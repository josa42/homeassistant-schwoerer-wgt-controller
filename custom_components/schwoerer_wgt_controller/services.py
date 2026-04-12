"""Services for Schwörer WGT Controller."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import WGTControllerCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_FORCE_UPDATE = "force_update"
SERVICE_SET_ROOM_TEMPERATURE = "set_room_temperature"

SERVICE_FORCE_UPDATE_SCHEMA = vol.Schema({})

SERVICE_SET_ROOM_TEMPERATURE_SCHEMA = vol.Schema(
    {
        vol.Required("room_id"): cv.string,
        vol.Required("temperature"): vol.Coerce(float),
        vol.Optional("duration_minutes", default=60): vol.Coerce(int),
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for the integration."""

    async def handle_force_update(call: ServiceCall) -> None:
        """Handle force update service call."""
        _LOGGER.info("Force update requested")
        for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
            if isinstance(coordinator, WGTControllerCoordinator):
                await coordinator.async_force_update()

    async def handle_set_room_temperature(call: ServiceCall) -> None:
        """Handle set room temperature service call."""
        room_id = call.data["room_id"]
        temperature = call.data["temperature"]
        duration = call.data.get("duration_minutes", 60)

        _LOGGER.info(
            "Setting temporary temperature for %s to %s°C for %s minutes",
            room_id,
            temperature,
            duration,
        )

        # TODO: Implement temporary temperature override
        # This would require storing the override in the coordinator
        # and having the controller respect it

    hass.services.async_register(
        DOMAIN,
        SERVICE_FORCE_UPDATE,
        handle_force_update,
        schema=SERVICE_FORCE_UPDATE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ROOM_TEMPERATURE,
        handle_set_room_temperature,
        schema=SERVICE_SET_ROOM_TEMPERATURE_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services."""
    hass.services.async_remove(DOMAIN, SERVICE_FORCE_UPDATE)
    hass.services.async_remove(DOMAIN, SERVICE_SET_ROOM_TEMPERATURE)
