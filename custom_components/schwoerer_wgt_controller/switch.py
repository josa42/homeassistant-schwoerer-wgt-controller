"""Switch entities for Schwörer WGT Controller."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_TEST_MODE, DOMAIN
from .coordinator import WGTControllerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities."""
    coordinator: WGTControllerCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SwitchEntity] = [
        ControllerEnabledSwitch(coordinator),
        TestModeSwitch(coordinator),
        VacationModeSwitch(coordinator),
        HeatingLockSwitch(coordinator),
    ]

    async_add_entities(entities)


class ControllerEnabledSwitch(CoordinatorEntity[WGTControllerCoordinator], SwitchEntity):
    """Switch to enable/disable the controller."""

    _attr_has_entity_name = True
    _attr_translation_key = "controller_enabled"
    _attr_icon = "mdi:power"

    def __init__(self, coordinator: WGTControllerCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_controller_enabled"
        self._is_on = True  # Controller is enabled by default

        # Attach to schwoerer_lueftung device
        if coordinator.discovered and coordinator.discovered.device_identifier:
            self._attr_device_info = DeviceInfo(
                identifiers={coordinator.discovered.device_identifier},
            )

    @property
    def is_on(self) -> bool:
        """Return true if the controller is enabled."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the controller."""
        self._is_on = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the controller."""
        self._is_on = False
        self.async_write_ha_state()


class TestModeSwitch(CoordinatorEntity[WGTControllerCoordinator], SwitchEntity):
    """Switch to enable/disable test mode."""

    _attr_has_entity_name = True
    _attr_translation_key = "test_mode"
    _attr_icon = "mdi:test-tube"

    def __init__(self, coordinator: WGTControllerCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_test_mode"

        # Attach to schwoerer_lueftung device
        if coordinator.discovered and coordinator.discovered.device_identifier:
            self._attr_device_info = DeviceInfo(
                identifiers={coordinator.discovered.device_identifier},
            )

    @property
    def is_on(self) -> bool:
        """Return true if test mode is enabled."""
        return self.coordinator.test_mode

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable test mode."""
        await self._set_test_mode(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable test mode."""
        await self._set_test_mode(False)

    async def _set_test_mode(self, enabled: bool) -> None:
        """Set test mode in options."""
        new_options = {**self.coordinator.entry.options, CONF_TEST_MODE: enabled}
        self.hass.config_entries.async_update_entry(
            self.coordinator.entry, options=new_options
        )
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        return {
            "description": "Im Testmodus werden Aktionen nur geloggt, nicht ausgeführt."
        }


class VacationModeSwitch(RestoreEntity, SwitchEntity):
    """Switch for vacation mode."""

    _attr_has_entity_name = True
    _attr_translation_key = "vacation_mode_switch"
    _attr_icon = "mdi:palm-tree"

    def __init__(self, coordinator: WGTControllerCoordinator) -> None:
        """Initialize the switch."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_vacation_mode"
        self._is_on = False
        # Register with coordinator
        coordinator.vacation_mode_switch = self

        # Attach to schwoerer_lueftung device
        if coordinator.discovered and coordinator.discovered.device_identifier:
            self._attr_device_info = DeviceInfo(
                identifiers={coordinator.discovered.device_identifier},
            )

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._is_on = last_state.state == "on"

    @property
    def is_on(self) -> bool:
        """Return true if vacation mode is enabled."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable vacation mode."""
        self._is_on = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable vacation mode."""
        self._is_on = False
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()


class HeatingLockSwitch(RestoreEntity, SwitchEntity):
    """Switch for heating lock."""

    _attr_has_entity_name = True
    _attr_translation_key = "heating_lock_switch"
    _attr_icon = "mdi:radiator-off"

    def __init__(self, coordinator: WGTControllerCoordinator) -> None:
        """Initialize the switch."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_heating_lock"
        self._is_on = False
        # Register with coordinator
        coordinator.heating_lock_switch = self

        # Attach to schwoerer_lueftung device
        if coordinator.discovered and coordinator.discovered.device_identifier:
            self._attr_device_info = DeviceInfo(
                identifiers={coordinator.discovered.device_identifier},
            )

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._is_on = last_state.state == "on"

    @property
    def is_on(self) -> bool:
        """Return true if heating is locked."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Lock heating."""
        self._is_on = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Unlock heating."""
        self._is_on = False
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
