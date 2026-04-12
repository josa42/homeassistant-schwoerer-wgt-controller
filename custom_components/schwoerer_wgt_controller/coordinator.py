"""Coordinator for Schwörer WGT Controller."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_TEST_MODE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .controller import Controller, ControllerState, RuleResult
from .discovery import DiscoveredEntities, discover_entities

_LOGGER = logging.getLogger(__name__)


class WGTControllerCoordinator(DataUpdateCoordinator[ControllerState]):
    """Coordinator for managing WGT controller state and updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )

        self.entry = entry
        self.discovered: DiscoveredEntities | None = None
        self.controller: Controller | None = None
        self.last_results: list[RuleResult] = []
        self._unsub_listeners: list[Any] = []

        # Internal entity references (set by entity setup)
        self.vacation_mode_switch: Any = None
        self.heating_lock_switch: Any = None
        self.fan_level_override_select: Any = None

    @property
    def config(self) -> dict[str, Any]:
        """Get current configuration (data + options merged)."""
        return {**self.entry.data, **self.entry.options}

    @property
    def test_mode(self) -> bool:
        """Check if test mode is enabled."""
        return self.config.get(CONF_TEST_MODE, True)  # Default to True for safety

    async def async_config_entry_first_refresh(self) -> None:
        """Perform first refresh and setup."""
        # Discover entities from schwoerer_lueftung
        self.discovered = await discover_entities(self.hass)
        _LOGGER.info(
            "Discovered %d rooms from schwoerer_lueftung", len(self.discovered.rooms)
        )

        # Initialize controller
        self.controller = Controller(self)

        # Setup event listeners
        await self._setup_listeners()

        # Perform initial refresh
        await super().async_config_entry_first_refresh()

    async def _setup_listeners(self) -> None:
        """Setup event listeners for state changes."""
        entities_to_watch: list[str] = []

        # Watch room sensors (window, humidity)
        rooms_config = self.config.get("rooms", {})
        for room_config in rooms_config.values():
            # Watch all window sensors
            window_sensors = room_config.get("window_sensors") or []
            for window_sensor in window_sensors:
                if window_sensor:
                    entities_to_watch.append(window_sensor)

            humidity_sensor = room_config.get("humidity_sensor")
            if humidity_sensor:
                entities_to_watch.append(humidity_sensor)

        # Register state change listener
        if entities_to_watch:
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self.hass, entities_to_watch, self._handle_state_change
                )
            )
            _LOGGER.debug("Watching entities: %s", entities_to_watch)

        # Register periodic update
        self._unsub_listeners.append(
            async_track_time_interval(
                self.hass,
                self._handle_periodic_update,
                timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
            )
        )

    @callback
    def _handle_state_change(self, event: Any) -> None:
        """Handle state change events."""
        entity_id = event.data.get("entity_id")
        _LOGGER.debug("State change detected for %s", entity_id)

        # Schedule a refresh
        self.hass.async_create_task(self.async_request_refresh())

    async def _handle_periodic_update(self, now: Any) -> None:
        """Handle periodic updates."""
        await self.async_request_refresh()

    async def _async_update_data(self) -> ControllerState:
        """Update data by evaluating controller rules."""
        if not self.controller:
            return ControllerState()

        # Evaluate rules
        state, results = await self.controller.evaluate()
        self.last_results = results

        # Execute actions
        await self.controller.execute(results, test_mode=self.test_mode)

        return state

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and cleanup listeners."""
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

    async def async_force_update(self) -> None:
        """Force an immediate update."""
        await self.async_request_refresh()

    def get_room_explanation(self, room_id: str) -> str:
        """Get explanation for a specific room's current state."""
        if not self.data:
            return "Keine Daten verfügbar"

        room_state = self.data.rooms.get(room_id)
        if not room_state:
            return "Raum nicht gefunden"

        if room_state.reasons:
            return " | ".join(room_state.reasons)

        return "Keine Begründung verfügbar"

    def get_global_explanation(self) -> str:
        """Get global explanation for controller state."""
        if not self.data:
            return "Keine Daten verfügbar"

        if self.data.global_reasons:
            return " | ".join(self.data.global_reasons)

        return "Normalbetrieb"
