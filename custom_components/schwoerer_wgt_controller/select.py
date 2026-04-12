"""Select entities for Schwörer WGT Controller."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .coordinator import WGTControllerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities."""
    coordinator: WGTControllerCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SelectEntity] = [
        FanLevelOverrideSelect(coordinator),
    ]

    async_add_entities(entities)


class FanLevelOverrideSelect(RestoreEntity, SelectEntity):
    """Select entity for manual fan level override."""

    _attr_has_entity_name = True
    _attr_translation_key = "fan_level_override"
    _attr_icon = "mdi:fan"
    _attr_options = ["Auto", "0", "1", "2", "3", "4"]

    def __init__(self, coordinator: WGTControllerCoordinator) -> None:
        """Initialize the select."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_fan_level_override"
        self._current_option = "Auto"
        # Register with coordinator
        coordinator.fan_level_override_select = self

        # Attach to schwoerer_lueftung device
        if coordinator.discovered and coordinator.discovered.device_identifier:
            self._attr_device_info = DeviceInfo(
                identifiers={coordinator.discovered.device_identifier},
            )

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state in self._attr_options:
                self._current_option = last_state.state

    @property
    def current_option(self) -> str:
        """Return the current option."""
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self._current_option = option
        self.async_write_ha_state()
        # Trigger controller update
        await self.coordinator.async_request_refresh()
