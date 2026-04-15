"""Config flow for Schwörer WGT Controller."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_FAN_LEVEL_HIGH_HUMIDITY,
    CONF_FAN_LEVEL_NIGHT,
    CONF_FAN_LEVEL_NORMAL,
    CONF_FAN_LEVEL_VACATION,
    CONF_HUMIDITY_THRESHOLD,
    CONF_NIGHT_END,
    CONF_NIGHT_START,
    CONF_OUTDOOR_TEMP_AUXILIARY_HEATING_THRESHOLD,
    CONF_OUTDOOR_TEMP_HEATING_THRESHOLD,
    CONF_ROOMS,
    CONF_TEMPERATURE_NIGHT,
    CONF_TEMPERATURE_NORMAL,
    CONF_TEMPERATURE_VACATION,
    CONF_TEMPERATURE_WINDOW_OPEN,
    CONF_TEST_MODE,
    DEFAULT_FAN_LEVEL_HIGH_HUMIDITY,
    DEFAULT_FAN_LEVEL_NIGHT,
    DEFAULT_FAN_LEVEL_NORMAL,
    DEFAULT_FAN_LEVEL_VACATION,
    DEFAULT_HUMIDITY_THRESHOLD,
    DEFAULT_NIGHT_END,
    DEFAULT_NIGHT_START,
    DEFAULT_OUTDOOR_TEMP_AUXILIARY_HEATING_THRESHOLD,
    DEFAULT_OUTDOOR_TEMP_HEATING_THRESHOLD,
    DEFAULT_TEMPERATURE_NIGHT,
    DEFAULT_TEMPERATURE_NORMAL,
    DEFAULT_TEMPERATURE_VACATION,
    DEFAULT_TEMPERATURE_WINDOW_OPEN,
    DOMAIN,
)
from .discovery import discover_entities, validate_discovery

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Schwörer WGT Controller."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_rooms: list[dict[str, Any]] = []
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        # Discover entities from schwoerer_lueftung
        discovered = await discover_entities(self.hass)
        validation_errors = await validate_discovery(discovered)

        # Store discovered rooms for display
        room_list = ", ".join([r.name for r in discovered.rooms]) if discovered.rooms else "Keine"

        if validation_errors:
            for error in validation_errors:
                errors["base"] = error
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({}),
                errors=errors,
                description_placeholders={
                    "discovered_rooms": room_list,
                    "error_details": ", ".join(validation_errors)
                },
            )

        # Store discovered rooms for later
        self._discovered_rooms = [
            {"number": r.number, "name": r.name, "climate_entity_id": r.climate_entity_id}
            for r in discovered.rooms
        ]

        if user_input is not None:
            rooms_config = {}
            for room in self._discovered_rooms:
                room_id = f"room_{room['number']}"
                rooms_config[room_id] = {
                    "name": room["name"],
                    "climate_entity_id": room["climate_entity_id"],
                }

            self._data = {
                CONF_TEST_MODE: user_input.get(CONF_TEST_MODE, False),
                CONF_ROOMS: rooms_config,
            }

            return await self.async_step_rooms()

        room_list = ", ".join([r["name"] for r in self._discovered_rooms])

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_TEST_MODE, default=True): bool,
                }
            ),
            description_placeholders={"discovered_rooms": room_list},
        )

    async def async_step_rooms(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the room configuration step."""
        if user_input is not None:
            rooms_config = self._data.get(CONF_ROOMS, {})

            for key, value in user_input.items():
                if key.startswith("room_") and "_" in key[5:]:
                    parts = key.split("_", 2)
                    room_id = f"room_{parts[1]}"
                    setting = "_".join(parts[2:])
                    if room_id not in rooms_config:
                        rooms_config[room_id] = {}
                    rooms_config[room_id][setting] = value

            self._data[CONF_ROOMS] = rooms_config

            return self.async_create_entry(
                title="Schwörer WGT Controller",
                data=self._data,
            )

        schema_dict: dict[Any, Any] = {}
        for room in self._discovered_rooms:
            room_id = f"room_{room['number']}"
            room_name = room["name"]

            schema_dict[vol.Optional(f"{room_id}_window_sensors")] = selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="binary_sensor",
                    device_class=["window", "door", "opening"],
                    multiple=True,
                )
            )
            schema_dict[vol.Optional(f"{room_id}_humidity_sensor")] = selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="humidity",
                )
            )
            schema_dict[vol.Optional(f"{room_id}_is_bedroom", default=False)] = (
                selector.BooleanSelector()
            )

        return self.async_show_form(
            step_id="rooms",
            data_schema=vol.Schema(schema_dict),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlowWithConfigEntry):
    """Handle options flow for Schwörer WGT Controller."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options - main menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["temperatures", "timing", "fan_levels", "thresholds", "rooms"],
        )

    async def async_step_general(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure general settings."""
        if user_input is not None:
            options = {**self.config_entry.options, **user_input}
            return self.async_create_entry(title="", data=options)

        return self.async_show_menu(
            step_id="general",
            menu_options=["temperatures", "timing", "fan_levels", "thresholds", "rooms"],
        )

    async def async_step_temperatures(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure global temperatures."""
        if user_input is not None:
            options = {**self.config_entry.options, **user_input}
            return self.async_create_entry(title="", data=options)

        current = self.config_entry.options

        return self.async_show_form(
            step_id="temperatures",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_TEMPERATURE_NORMAL,
                        default=current.get(
                            CONF_TEMPERATURE_NORMAL, DEFAULT_TEMPERATURE_NORMAL
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=10, max=30, step=0.5, unit_of_measurement="°C"
                        )
                    ),
                    vol.Optional(
                        CONF_TEMPERATURE_NIGHT,
                        default=current.get(
                            CONF_TEMPERATURE_NIGHT, DEFAULT_TEMPERATURE_NIGHT
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=10, max=30, step=0.5, unit_of_measurement="°C"
                        )
                    ),
                    vol.Optional(
                        CONF_TEMPERATURE_VACATION,
                        default=current.get(
                            CONF_TEMPERATURE_VACATION, DEFAULT_TEMPERATURE_VACATION
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=10, max=30, step=0.5, unit_of_measurement="°C"
                        )
                    ),
                    vol.Optional(
                        CONF_TEMPERATURE_WINDOW_OPEN,
                        default=current.get(
                            CONF_TEMPERATURE_WINDOW_OPEN, DEFAULT_TEMPERATURE_WINDOW_OPEN
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=5, max=20, step=0.5, unit_of_measurement="°C"
                        )
                    ),
                }
            ),
        )

    async def async_step_timing(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure timing settings."""
        if user_input is not None:
            options = {**self.config_entry.options, **user_input}
            return self.async_create_entry(title="", data=options)

        current = self.config_entry.options

        return self.async_show_form(
            step_id="timing",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_NIGHT_START,
                        default=current.get(CONF_NIGHT_START, DEFAULT_NIGHT_START),
                    ): selector.TimeSelector(),
                    vol.Optional(
                        CONF_NIGHT_END,
                        default=current.get(CONF_NIGHT_END, DEFAULT_NIGHT_END),
                    ): selector.TimeSelector(),
                }
            ),
        )

    async def async_step_fan_levels(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure fan level settings."""
        if user_input is not None:
            options = {**self.config_entry.options, **user_input}
            return self.async_create_entry(title="", data=options)

        current = self.config_entry.options

        return self.async_show_form(
            step_id="fan_levels",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_FAN_LEVEL_NORMAL,
                        default=current.get(
                            CONF_FAN_LEVEL_NORMAL, DEFAULT_FAN_LEVEL_NORMAL
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=0, max=4, step=1)
                    ),
                    vol.Optional(
                        CONF_FAN_LEVEL_NIGHT,
                        default=current.get(
                            CONF_FAN_LEVEL_NIGHT, DEFAULT_FAN_LEVEL_NIGHT
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=0, max=4, step=1)
                    ),
                    vol.Optional(
                        CONF_FAN_LEVEL_VACATION,
                        default=current.get(
                            CONF_FAN_LEVEL_VACATION, DEFAULT_FAN_LEVEL_VACATION
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=0, max=4, step=1)
                    ),
                    vol.Optional(
                        CONF_FAN_LEVEL_HIGH_HUMIDITY,
                        default=current.get(
                            CONF_FAN_LEVEL_HIGH_HUMIDITY, DEFAULT_FAN_LEVEL_HIGH_HUMIDITY
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=0, max=4, step=1)
                    ),
                }
            ),
        )

    async def async_step_thresholds(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure threshold settings."""
        if user_input is not None:
            options = {**self.config_entry.options, **user_input}
            return self.async_create_entry(title="", data=options)

        current = self.config_entry.options

        return self.async_show_form(
            step_id="thresholds",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_OUTDOOR_TEMP_HEATING_THRESHOLD,
                        default=current.get(
                            CONF_OUTDOOR_TEMP_HEATING_THRESHOLD,
                            DEFAULT_OUTDOOR_TEMP_HEATING_THRESHOLD,
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=25, step=0.5, unit_of_measurement="°C"
                        )
                    ),
                    vol.Optional(
                        CONF_OUTDOOR_TEMP_AUXILIARY_HEATING_THRESHOLD,
                        default=current.get(
                            CONF_OUTDOOR_TEMP_AUXILIARY_HEATING_THRESHOLD,
                            DEFAULT_OUTDOOR_TEMP_AUXILIARY_HEATING_THRESHOLD,
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=-10, max=20, step=0.5, unit_of_measurement="°C"
                        )
                    ),
                    vol.Optional(
                        CONF_HUMIDITY_THRESHOLD,
                        default=current.get(
                            CONF_HUMIDITY_THRESHOLD, DEFAULT_HUMIDITY_THRESHOLD
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=50, max=90, step=1, unit_of_measurement="%"
                        )
                    ),
                }
            ),
        )

    async def async_step_rooms(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure room settings."""
        if user_input is not None:
            # Parse room configurations from user input
            rooms_config = self.config_entry.data.get(CONF_ROOMS, {})

            for key, value in user_input.items():
                if key.startswith("room_") and "_" in key[5:]:
                    parts = key.split("_", 2)
                    room_id = f"room_{parts[1]}"
                    setting = "_".join(parts[2:])

                    if room_id not in rooms_config:
                        rooms_config[room_id] = {}
                    rooms_config[room_id][setting] = value

            options = {**self.config_entry.options, CONF_ROOMS: rooms_config}
            return self.async_create_entry(title="", data=options)

        # Build schema for each room
        schema_dict: dict[Any, Any] = {}
        rooms_config = {
            **self.config_entry.data.get(CONF_ROOMS, {}),
            **self.config_entry.options.get(CONF_ROOMS, {}),
        }

        for room_id, room_data in rooms_config.items():
            room_name = room_data.get("name", room_id)

            # Add room header comment for better UX
            # Window sensors (multiple)
            key_window = vol.Optional(
                f"{room_id}_window_sensors",
                description={
                    "suggested_value": room_data.get("window_sensors", []),
                    "name": f"{room_name} - Fenstersensoren",
                },
            )
            schema_dict[key_window] = selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="binary_sensor",
                    device_class=["window", "door", "opening"],
                    multiple=True,
                )
            )

            # Humidity sensor
            key_humidity = vol.Optional(
                f"{room_id}_humidity_sensor",
                description={
                    "suggested_value": room_data.get("humidity_sensor"),
                    "name": f"{room_name} - Luftfeuchtigkeitssensor",
                },
            )
            schema_dict[key_humidity] = selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="humidity",
                )
            )

            # Is bedroom
            key_bedroom = vol.Optional(
                f"{room_id}_is_bedroom",
                description={"name": f"{room_name} - Ist Schlafraum"},
                default=room_data.get("is_bedroom", False),
            )
            schema_dict[key_bedroom] = selector.BooleanSelector()

        return self.async_show_form(
            step_id="rooms",
            data_schema=vol.Schema(schema_dict),
        )
