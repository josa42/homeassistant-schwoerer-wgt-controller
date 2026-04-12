"""Controller logic with rule engine."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from .const import (
    CONF_FAN_LEVEL_HIGH_HUMIDITY,
    CONF_FAN_LEVEL_NIGHT,
    CONF_FAN_LEVEL_NORMAL,
    CONF_FAN_LEVEL_VACATION,
    CONF_HUMIDITY_THRESHOLD,
    CONF_NIGHT_END,
    CONF_NIGHT_START,
    CONF_OUTDOOR_TEMP_HEATING_THRESHOLD,
    CONF_ROOMS,
    CONF_TEMPERATURE_NIGHT,
    CONF_TEMPERATURE_NORMAL,
    CONF_TEMPERATURE_VACATION,
    CONF_TEMPERATURE_WINDOW_OPEN,
    DEFAULT_FAN_LEVEL_HIGH_HUMIDITY,
    DEFAULT_FAN_LEVEL_NIGHT,
    DEFAULT_FAN_LEVEL_NORMAL,
    DEFAULT_FAN_LEVEL_VACATION,
    DEFAULT_HUMIDITY_THRESHOLD,
    DEFAULT_NIGHT_END,
    DEFAULT_NIGHT_START,
    DEFAULT_OUTDOOR_TEMP_HEATING_THRESHOLD,
    DEFAULT_TEMPERATURE_NIGHT,
    DEFAULT_TEMPERATURE_NORMAL,
    DEFAULT_TEMPERATURE_VACATION,
    DEFAULT_TEMPERATURE_WINDOW_OPEN,
    DEFAULT_WINDOW_OPEN_DELAY_MINUTES,
    MODE_NIGHT,
    MODE_NORMAL,
    MODE_VACATION,
    MODE_WINDOW_OPEN,
)

if TYPE_CHECKING:
    from .coordinator import WGTControllerCoordinator

_LOGGER = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions the controller can perform."""

    SET_ROOM_TEMPERATURE = "set_room_temperature"
    SET_HEAT_PUMP_HEATING = "set_heat_pump_heating"
    SET_HEAT_PUMP_COOLING = "set_heat_pump_cooling"
    SET_AUXILIARY_HEATING = "set_auxiliary_heating"
    SET_FAN_LEVEL = "set_fan_level"


@dataclass
class RuleResult:
    """Result of a rule evaluation."""

    action: ActionType
    target: str  # Entity ID or room identifier
    value: Any  # Value to set
    reason: str  # Human-readable explanation
    priority: int = 0  # Higher priority wins


@dataclass
class RoomState:
    """Current state for a room."""

    room_id: str
    room_name: str
    climate_entity_id: str
    target_temperature: float | None = None
    mode: str = MODE_NORMAL
    reasons: list[str] = field(default_factory=list)
    auxiliary_heating_enabled: bool = False


@dataclass
class ControllerState:
    """Overall controller state."""

    rooms: dict[str, RoomState] = field(default_factory=dict)
    heat_pump_heating_enabled: bool = False
    heat_pump_cooling_enabled: bool = False
    fan_level: int = 2
    global_reasons: list[str] = field(default_factory=list)
    is_night: bool = False
    is_vacation: bool = False
    is_heating_locked: bool = False
    outdoor_temperature: float | None = None


class Rule(ABC):
    """Base class for controller rules."""

    def __init__(self, coordinator: WGTControllerCoordinator) -> None:
        self.coordinator = coordinator
        self.hass = coordinator.hass

    @property
    def config(self) -> dict[str, Any]:
        """Get current configuration."""
        return self.coordinator.config

    @abstractmethod
    def evaluate(self, state: ControllerState) -> list[RuleResult]:
        """Evaluate the rule and return any actions to take."""


class HeatingLockRule(Rule):
    """Check if heating is manually locked."""

    def evaluate(self, state: ControllerState) -> list[RuleResult]:
        results: list[RuleResult] = []

        # Use internal heating lock entity via coordinator reference
        lock_switch = self.coordinator.heating_lock_switch
        is_locked = lock_switch.is_on if lock_switch else False

        if is_locked:
            state.is_heating_locked = True
            state.global_reasons.append("Heizsperre aktiv")
            results.append(
                RuleResult(
                    action=ActionType.SET_HEAT_PUMP_HEATING,
                    target="heat_pump",
                    value=False,
                    reason="Heizsperre aktiv",
                    priority=100,
                )
            )

        return results


class HeatingReleaseRule(Rule):
    """Control heat pump heating based on outdoor temperature."""

    def evaluate(self, state: ControllerState) -> list[RuleResult]:
        results: list[RuleResult] = []

        if state.is_heating_locked:
            return results

        threshold = self.config.get(
            CONF_OUTDOOR_TEMP_HEATING_THRESHOLD, DEFAULT_OUTDOOR_TEMP_HEATING_THRESHOLD
        )

        outdoor_temp = state.outdoor_temperature
        if outdoor_temp is None:
            return results

        should_heat = outdoor_temp < threshold

        if should_heat:
            reason = f"Außentemperatur {outdoor_temp}°C < {threshold}°C"
            state.global_reasons.append(f"Heizfreigabe: {reason}")
        else:
            reason = f"Außentemperatur {outdoor_temp}°C >= {threshold}°C"

        state.heat_pump_heating_enabled = should_heat
        results.append(
            RuleResult(
                action=ActionType.SET_HEAT_PUMP_HEATING,
                target="heat_pump",
                value=should_heat,
                reason=reason,
                priority=50,
            )
        )

        return results


class NightModeRule(Rule):
    """Check if it's night time."""

    def evaluate(self, state: ControllerState) -> list[RuleResult]:
        night_start_str = self.config.get(CONF_NIGHT_START, DEFAULT_NIGHT_START)
        night_end_str = self.config.get(CONF_NIGHT_END, DEFAULT_NIGHT_END)

        night_start = _parse_time(night_start_str)
        night_end = _parse_time(night_end_str)
        now = datetime.now().time()

        # Handle overnight periods (e.g., 20:00 to 05:00)
        if night_start > night_end:
            is_night = now >= night_start or now < night_end
        else:
            is_night = night_start <= now < night_end

        state.is_night = is_night
        if is_night:
            state.global_reasons.append(
                f"Nachtmodus ({night_start_str}-{night_end_str})"
            )

        return []


class VacationModeRule(Rule):
    """Check if vacation mode is active."""

    def evaluate(self, state: ControllerState) -> list[RuleResult]:
        # Use internal vacation mode entity via coordinator reference
        vacation_switch = self.coordinator.vacation_mode_switch
        is_vacation = vacation_switch.is_on if vacation_switch else False

        if is_vacation:
            state.is_vacation = True
            state.global_reasons.append("Urlaubsmodus aktiv")

        return []


class RoomTemperatureRule(Rule):
    """Calculate target temperature for each room."""

    def evaluate(self, state: ControllerState) -> list[RuleResult]:
        results: list[RuleResult] = []
        rooms_config = self.config.get("rooms", {})

        # Global defaults
        temp_normal = self.config.get(CONF_TEMPERATURE_NORMAL, DEFAULT_TEMPERATURE_NORMAL)
        temp_night = self.config.get(CONF_TEMPERATURE_NIGHT, DEFAULT_TEMPERATURE_NIGHT)
        temp_vacation = self.config.get(
            CONF_TEMPERATURE_VACATION, DEFAULT_TEMPERATURE_VACATION
        )
        temp_window = self.config.get(
            CONF_TEMPERATURE_WINDOW_OPEN, DEFAULT_TEMPERATURE_WINDOW_OPEN
        )
        window_delay = DEFAULT_WINDOW_OPEN_DELAY_MINUTES

        for room_id, room_state in state.rooms.items():
            room_config = rooms_config.get(room_id, {})

            target_temp = temp_normal
            mode = MODE_NORMAL
            reasons: list[str] = []

            # Priority 1: Window open (highest)
            window_sensors = room_config.get("window_sensors", [])
            if window_sensors and self._is_any_window_open(window_sensors, window_delay):
                target_temp = temp_window
                mode = MODE_WINDOW_OPEN
                reasons.append(f"Fenster offen > {window_delay} Min → {target_temp}°C")

            # Priority 2: Vacation mode
            elif state.is_vacation:
                target_temp = temp_vacation
                mode = MODE_VACATION
                reasons.append(f"Urlaubsmodus → {target_temp}°C")

            # Priority 3: Night mode
            elif state.is_night:
                target_temp = temp_night
                mode = MODE_NIGHT
                reasons.append(f"Nachtmodus → {target_temp}°C")

            # Default: Normal mode
            else:
                reasons.append(f"Normalbetrieb → {target_temp}°C")

            room_state.target_temperature = target_temp
            room_state.mode = mode
            room_state.reasons = reasons

            results.append(
                RuleResult(
                    action=ActionType.SET_ROOM_TEMPERATURE,
                    target=room_state.climate_entity_id,
                    value=target_temp,
                    reason=" | ".join(reasons),
                    priority=10,
                )
            )

        return results

    def _is_any_window_open(self, sensor_entities: list[str], delay_minutes: int) -> bool:
        """Check if any window sensor has been open for the required delay."""
        for sensor_entity in sensor_entities:
            if self._is_window_open(sensor_entity, delay_minutes):
                return True
        return False

    def _is_window_open(self, sensor_entity: str, delay_minutes: int) -> bool:
        """Check if window sensor has been open for the required delay."""
        sensor_state = self.hass.states.get(sensor_entity)
        if not sensor_state or sensor_state.state != "on":
            return False

        # Check how long the window has been open
        last_changed = sensor_state.last_changed
        if last_changed:
            from datetime import timezone

            now = datetime.now(timezone.utc)
            open_duration = (now - last_changed).total_seconds() / 60
            return open_duration >= delay_minutes

        return False


class AuxiliaryHeatingRule(Rule):
    """Control auxiliary heating based on room type (bedroom vs normal room)."""

    def evaluate(self, state: ControllerState) -> list[RuleResult]:
        results: list[RuleResult] = []
        rooms_config = self.config.get("rooms", {})

        for room_id, room_state in state.rooms.items():
            room_config = rooms_config.get(room_id, {})
            is_bedroom = room_config.get("is_bedroom", False)

            aux_entity = room_config.get("auxiliary_heating_entity")
            if not aux_entity:
                continue

            # Auxiliary heating only when heat pump heating is enabled
            should_enable = state.heat_pump_heating_enabled

            # Disable bedroom auxiliary heating at night
            if is_bedroom and state.is_night:
                should_enable = False
                reason = "Schlafraum: Zusatzheizer nachts deaktiviert"
            elif should_enable:
                reason = "Zusatzheizer aktiv (Heizfreigabe)"
            else:
                reason = "Zusatzheizer aus (keine Heizfreigabe)"

            room_state.auxiliary_heating_enabled = should_enable

            results.append(
                RuleResult(
                    action=ActionType.SET_AUXILIARY_HEATING,
                    target=aux_entity,
                    value=should_enable,
                    reason=reason,
                    priority=20,
                )
            )

        return results


class FanLevelRule(Rule):
    """Control fan level based on conditions."""

    def evaluate(self, state: ControllerState) -> list[RuleResult]:
        results: list[RuleResult] = []

        # Get configuration
        fan_normal = self.config.get(CONF_FAN_LEVEL_NORMAL, DEFAULT_FAN_LEVEL_NORMAL)
        fan_night = self.config.get(CONF_FAN_LEVEL_NIGHT, DEFAULT_FAN_LEVEL_NIGHT)
        fan_vacation = self.config.get(CONF_FAN_LEVEL_VACATION, DEFAULT_FAN_LEVEL_VACATION)
        fan_humidity = self.config.get(
            CONF_FAN_LEVEL_HIGH_HUMIDITY, DEFAULT_FAN_LEVEL_HIGH_HUMIDITY
        )
        humidity_threshold = self.config.get(
            CONF_HUMIDITY_THRESHOLD, DEFAULT_HUMIDITY_THRESHOLD
        )

        fan_level = fan_normal
        reason = f"Normalbetrieb → Stufe {fan_level}"

        # Check manual override using internal entity via coordinator reference
        override_select = self.coordinator.fan_level_override_select
        if override_select:
            option = override_select.current_option
            if option not in ("Auto", "unknown", "unavailable"):
                try:
                    fan_level = int(option)
                    reason = f"Manuell gesetzt → Stufe {fan_level}"
                    state.fan_level = fan_level
                    state.global_reasons.append(reason)
                    results.append(
                        RuleResult(
                            action=ActionType.SET_FAN_LEVEL,
                            target="fan",
                            value=fan_level,
                            reason=reason,
                            priority=100,
                        )
                    )
                    return results
                except ValueError:
                    pass

        # Priority: Vacation → High humidity → Night → Normal
        if state.is_vacation:
            fan_level = fan_vacation
            reason = f"Urlaubsmodus → Stufe {fan_level}"
        elif self._is_humidity_high(humidity_threshold):
            fan_level = fan_humidity
            reason = f"Hohe Luftfeuchtigkeit > {humidity_threshold}% → Stufe {fan_level}"
        elif state.is_night:
            fan_level = fan_night
            reason = f"Nachtmodus → Stufe {fan_level}"

        state.fan_level = fan_level
        state.global_reasons.append(f"Lüfterstufe: {reason}")

        results.append(
            RuleResult(
                action=ActionType.SET_FAN_LEVEL,
                target="fan",
                value=fan_level,
                reason=reason,
                priority=30,
            )
        )

        return results

    def _is_humidity_high(self, threshold: float) -> bool:
        """Check if any room has humidity above threshold (ignoring rooms with open windows)."""
        rooms_config = self.config.get("rooms", {})
        window_delay = DEFAULT_WINDOW_OPEN_DELAY_MINUTES
        
        for room_config in rooms_config.values():
            # Skip rooms with open windows
            window_sensors = room_config.get("window_sensors", [])
            if window_sensors and self._is_any_window_open(window_sensors, window_delay):
                continue
            
            # Check humidity
            humidity_sensor = room_config.get("humidity_sensor")
            if not humidity_sensor:
                continue
            
            humidity_state = self.hass.states.get(humidity_sensor)
            if not humidity_state:
                continue
            
            try:
                humidity = float(humidity_state.state)
                if humidity > threshold:
                    return True
            except ValueError:
                continue
        
        return False


class Controller:
    """Main controller that evaluates all rules."""

    def __init__(self, coordinator: WGTControllerCoordinator) -> None:
        self.coordinator = coordinator
        self.hass = coordinator.hass

        # Initialize rules in evaluation order
        self.rules: list[Rule] = [
            HeatingLockRule(coordinator),
            VacationModeRule(coordinator),
            NightModeRule(coordinator),
            HeatingReleaseRule(coordinator),
            RoomTemperatureRule(coordinator),
            AuxiliaryHeatingRule(coordinator),
            FanLevelRule(coordinator),
        ]

    async def evaluate(self) -> tuple[ControllerState, list[RuleResult]]:
        """Evaluate all rules and return state and actions."""
        state = self._build_initial_state()
        all_results: list[RuleResult] = []

        for rule in self.rules:
            try:
                results = rule.evaluate(state)
                all_results.extend(results)
            except Exception as err:
                _LOGGER.error("Error evaluating rule %s: %s", rule.__class__.__name__, err)

        return state, all_results

    async def execute(self, results: list[RuleResult], test_mode: bool = False) -> None:
        """Execute the rule results."""
        for result in results:
            if test_mode:
                _LOGGER.info(
                    "[TEST MODE] Would execute: %s on %s = %s (Reason: %s)",
                    result.action.value,
                    result.target,
                    result.value,
                    result.reason,
                )
                continue

            try:
                await self._execute_action(result)
            except Exception as err:
                _LOGGER.error("Error executing action %s: %s", result, err)

    async def _execute_action(self, result: RuleResult) -> None:
        """Execute a single action."""
        if result.action == ActionType.SET_ROOM_TEMPERATURE:
            await self.hass.services.async_call(
                "climate",
                "set_temperature",
                {"entity_id": result.target, "temperature": result.value},
            )

        elif result.action == ActionType.SET_HEAT_PUMP_HEATING:
            entity_id = self.coordinator.discovered.heat_pump_heating_entity
            if entity_id:
                service = "turn_on" if result.value else "turn_off"
                await self.hass.services.async_call(
                    "switch", service, {"entity_id": entity_id}
                )

        elif result.action == ActionType.SET_HEAT_PUMP_COOLING:
            entity_id = self.coordinator.discovered.heat_pump_cooling_entity
            if entity_id:
                service = "turn_on" if result.value else "turn_off"
                await self.hass.services.async_call(
                    "switch", service, {"entity_id": entity_id}
                )

        elif result.action == ActionType.SET_AUXILIARY_HEATING:
            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {
                    "entity_id": result.target,
                    "hvac_mode": "heat" if result.value else "fan_only",
                },
            )

        elif result.action == ActionType.SET_FAN_LEVEL:
            fan_entity = self.coordinator.discovered.fan_speed_entity
            if fan_entity:
                await self.hass.services.async_call(
                    "select",
                    "select_option",
                    {"entity_id": fan_entity, "option": str(result.value)},
                )

    def _build_initial_state(self) -> ControllerState:
        """Build initial controller state from discovered entities."""
        state = ControllerState()

        # Get outdoor temperature
        if self.coordinator.discovered.outdoor_temp_entity:
            temp_state = self.hass.states.get(
                self.coordinator.discovered.outdoor_temp_entity
            )
            if temp_state:
                try:
                    state.outdoor_temperature = float(temp_state.state)
                except ValueError:
                    pass

        # Initialize room states
        rooms_config = self.coordinator.config.get("rooms", {})
        for room in self.coordinator.discovered.rooms:
            room_id = f"room_{room.number}"
            room_config = rooms_config.get(room_id, {})

            state.rooms[room_id] = RoomState(
                room_id=room_id,
                room_name=room_config.get("name", room.name),
                climate_entity_id=room.climate_entity_id,
            )

        return state


def _parse_time(time_str: str) -> time:
    """Parse time string in HH:MM format."""
    parts = time_str.split(":")
    return time(int(parts[0]), int(parts[1]))
