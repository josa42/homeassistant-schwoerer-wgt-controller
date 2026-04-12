"""Binary sensor entities for Schwörer WGT Controller."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WGTControllerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities."""
    coordinator: WGTControllerCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = [
        HeatingReleaseSensor(coordinator),
        CoolingReleaseSensor(coordinator),
        NightModeSensor(coordinator),
        VacationModeSensor(coordinator),
    ]

    async_add_entities(entities)


class HeatingReleaseSensor(CoordinatorEntity[WGTControllerCoordinator], BinarySensorEntity):
    """Binary sensor indicating if heat pump heating is released."""

    _attr_has_entity_name = True
    _attr_translation_key = "heating_release"
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:radiator"

    def __init__(self, coordinator: WGTControllerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_heating_release"

    @property
    def is_on(self) -> bool | None:
        """Return true if heating is released."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.heat_pump_heating_enabled

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        return {
            "outdoor_temperature": self.coordinator.data.outdoor_temperature,
            "is_locked": self.coordinator.data.is_heating_locked,
        }


class CoolingReleaseSensor(CoordinatorEntity[WGTControllerCoordinator], BinarySensorEntity):
    """Binary sensor indicating if heat pump cooling is released."""

    _attr_has_entity_name = True
    _attr_translation_key = "cooling_release"
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:snowflake"

    def __init__(self, coordinator: WGTControllerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_cooling_release"

    @property
    def is_on(self) -> bool | None:
        """Return true if cooling is released."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.heat_pump_cooling_enabled


class NightModeSensor(CoordinatorEntity[WGTControllerCoordinator], BinarySensorEntity):
    """Binary sensor indicating if night mode is active."""

    _attr_has_entity_name = True
    _attr_translation_key = "night_mode"
    _attr_icon = "mdi:weather-night"

    def __init__(self, coordinator: WGTControllerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_night_mode"

    @property
    def is_on(self) -> bool | None:
        """Return true if night mode is active."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.is_night


class VacationModeSensor(CoordinatorEntity[WGTControllerCoordinator], BinarySensorEntity):
    """Binary sensor indicating if vacation mode is active."""

    _attr_has_entity_name = True
    _attr_translation_key = "vacation_mode"
    _attr_icon = "mdi:palm-tree"

    def __init__(self, coordinator: WGTControllerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_vacation_mode"

    @property
    def is_on(self) -> bool | None:
        """Return true if vacation mode is active."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.is_vacation
