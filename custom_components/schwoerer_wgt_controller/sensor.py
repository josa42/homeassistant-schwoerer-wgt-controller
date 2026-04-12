"""Sensor entities for Schwörer WGT Controller."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODE_NIGHT, MODE_NORMAL, MODE_VACATION, MODE_WINDOW_OPEN
from .coordinator import WGTControllerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: WGTControllerCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        GlobalStatusSensor(coordinator),
        GlobalExplanationSensor(coordinator),
    ]

    # Add per-room sensors
    if coordinator.discovered:
        for room in coordinator.discovered.rooms:
            room_id = f"room_{room.number}"
            entities.extend([
                RoomModeSensor(coordinator, room_id, room.name, room.device_identifier),
                RoomExplanationSensor(coordinator, room_id, room.name, room.device_identifier),
            ])

    async_add_entities(entities)


def _get_device_info(coordinator: WGTControllerCoordinator) -> DeviceInfo | None:
    """Get device info for attaching to schwoerer_lueftung device."""
    if coordinator.discovered and coordinator.discovered.device_identifier:
        return DeviceInfo(identifiers={coordinator.discovered.device_identifier})
    return None


class GlobalStatusSensor(CoordinatorEntity[WGTControllerCoordinator], SensorEntity):
    """Sensor showing the global controller status."""

    _attr_has_entity_name = True
    _attr_translation_key = "controller_status"
    _attr_icon = "mdi:home-thermometer"

    def __init__(self, coordinator: WGTControllerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_controller_status"
        self._attr_device_info = _get_device_info(coordinator)

    @property
    def native_value(self) -> str:
        """Return the current status."""
        if not self.coordinator.data:
            return "unknown"

        data = self.coordinator.data

        if self.coordinator.test_mode:
            return "test_mode"
        if data.is_heating_locked:
            return "locked"
        if data.is_vacation:
            return "vacation"
        if data.is_night:
            return "night"
        return "normal"

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}

        data = self.coordinator.data
        return {
            "test_mode": self.coordinator.test_mode,
            "is_night": data.is_night,
            "is_vacation": data.is_vacation,
            "is_heating_locked": data.is_heating_locked,
            "heat_pump_heating_enabled": data.heat_pump_heating_enabled,
            "outdoor_temperature": data.outdoor_temperature,
            "fan_level": data.fan_level,
        }


class GlobalExplanationSensor(CoordinatorEntity[WGTControllerCoordinator], SensorEntity):
    """Sensor providing a text explanation of the current controller state."""

    _attr_has_entity_name = True
    _attr_translation_key = "controller_explanation"
    _attr_icon = "mdi:text-box-outline"

    def __init__(self, coordinator: WGTControllerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_controller_explanation"
        self._attr_device_info = _get_device_info(coordinator)

    @property
    def native_value(self) -> str:
        """Return the explanation text."""
        return self.coordinator.get_global_explanation()

    @property
    def extra_state_attributes(self) -> dict:
        """Return the individual reasons as attributes."""
        if not self.coordinator.data:
            return {}

        return {
            "reasons": self.coordinator.data.global_reasons,
            "last_results_count": len(self.coordinator.last_results),
        }


class RoomModeSensor(CoordinatorEntity[WGTControllerCoordinator], SensorEntity):
    """Sensor showing the current mode for a room."""

    _attr_has_entity_name = True
    _attr_translation_key = "room_mode"
    _attr_icon = "mdi:home-thermometer-outline"

    def __init__(
        self,
        coordinator: WGTControllerCoordinator,
        room_id: str,
        room_name: str,
        room_device_identifier: tuple[str, str] | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._room_id = room_id
        self._room_name = room_name
        self._room_device_identifier = room_device_identifier
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{room_id}_mode"
        self._attr_has_entity_name = False  # Use full name, not device+entity
        self._attr_name = f"WGT Controller {self._room_name} Modus"
        if room_device_identifier:
            self._attr_device_info = DeviceInfo(identifiers={room_device_identifier})

    @property
    def native_value(self) -> str:
        """Return the current mode."""
        if not self.coordinator.data:
            return MODE_NORMAL

        room_state = self.coordinator.data.rooms.get(self._room_id)
        if room_state:
            return room_state.mode

        return MODE_NORMAL

    @property
    def extra_state_attributes(self) -> dict:
        """Return mode translations."""
        return {
            "mode_labels": {
                MODE_NORMAL: "Normal",
                MODE_NIGHT: "Nacht",
                MODE_VACATION: "Urlaub",
                MODE_WINDOW_OPEN: "Fenster offen",
            }
        }


class RoomExplanationSensor(CoordinatorEntity[WGTControllerCoordinator], SensorEntity):
    """Sensor providing a text explanation of why the room has its current settings."""

    _attr_has_entity_name = True
    _attr_translation_key = "room_explanation"
    _attr_icon = "mdi:text-box-outline"

    def __init__(
        self,
        coordinator: WGTControllerCoordinator,
        room_id: str,
        room_name: str,
        room_device_identifier: tuple[str, str] | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._room_id = room_id
        self._room_name = room_name
        self._room_device_identifier = room_device_identifier
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{room_id}_explanation"
        self._attr_has_entity_name = False  # Use full name, not device+entity
        self._attr_name = f"WGT Controller {self._room_name} Begründung"
        if room_device_identifier:
            self._attr_device_info = DeviceInfo(identifiers={room_device_identifier})

    @property
    def native_value(self) -> str:
        """Return the explanation text."""
        return self.coordinator.get_room_explanation(self._room_id)

    @property
    def extra_state_attributes(self) -> dict:
        """Return the individual reasons as attributes."""
        if not self.coordinator.data:
            return {}

        room_state = self.coordinator.data.rooms.get(self._room_id)
        if room_state:
            return {
                "reasons": room_state.reasons,
                "mode": room_state.mode,
                "target_temperature": room_state.target_temperature,
                "auxiliary_heating_enabled": room_state.auxiliary_heating_enabled,
            }

        return {}
