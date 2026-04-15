"""Config flow for Schwörer WGT Controller."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CO2_HIGH_DELAY_MINUTES,
    CONF_CO2_THRESHOLD,
    CONF_FAN_LEVEL_HIGH_CO2,
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
    DEFAULT_CO2_HIGH_DELAY_MINUTES,
    DEFAULT_CO2_THRESHOLD,
    DEFAULT_FAN_LEVEL_HIGH_CO2,
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


def _get_device_name(hass, climate_entity_id: str | None) -> str | None:
    """Look up the HA device name for a climate entity."""
    if not climate_entity_id:
        return None
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    entity_entry = ent_reg.async_get(climate_entity_id)
    if entity_entry and entity_entry.device_id:
        device = dev_reg.async_get(entity_entry.device_id)
        if device:
            return device.name_by_user or device.name
    return None


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Schwörer WGT Controller."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_rooms: list[dict[str, Any]] = []
        self._data: dict[str, Any] = {}
        self._room_index: int = 0

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
        """Handle the room configuration step (one room at a time)."""
        room = self._discovered_rooms[self._room_index]
        room_id = f"room_{room['number']}"

        if user_input is not None:
            rooms_config = self._data.get(CONF_ROOMS, {})
            if room_id not in rooms_config:
                rooms_config[room_id] = {}
            rooms_config[room_id].update(
                {
                    "window_sensors": user_input.get("window_sensors") or [],
                    "humidity_sensor": user_input.get("humidity_sensor"),
                    "co2_sensor": user_input.get("co2_sensor"),
                    "is_bedroom": user_input.get("is_bedroom", False),
                }
            )
            self._data[CONF_ROOMS] = rooms_config
            self._room_index += 1

            if self._room_index >= len(self._discovered_rooms):
                return self.async_create_entry(
                    title="Schwörer WGT Controller",
                    data=self._data,
                )
            return await self.async_step_rooms()

        return self.async_show_form(
            step_id="rooms",
            data_schema=vol.Schema(
                {
                    vol.Optional("window_sensors"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="binary_sensor",
                            device_class=["window", "door", "opening"],
                            multiple=True,
                        )
                    ),
                    vol.Optional("humidity_sensor"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor",
                            device_class="humidity",
                        )
                    ),
                    vol.Optional("co2_sensor"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor",
                            device_class="carbon_dioxide",
                        )
                    ),
                    vol.Optional("is_bedroom", default=False): selector.BooleanSelector(),
                }
            ),
            description_placeholders={
                "room_name": room["name"],
                "room_number": str(self._room_index + 1),
                "total_rooms": str(len(self._discovered_rooms)),
            },
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

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow."""
        super().__init__(config_entry)
        self._room_index: int = 0

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
                    vol.Optional(
                        CONF_FAN_LEVEL_HIGH_CO2,
                        default=current.get(
                            CONF_FAN_LEVEL_HIGH_CO2, DEFAULT_FAN_LEVEL_HIGH_CO2
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
                    vol.Optional(
                        CONF_CO2_THRESHOLD,
                        default=current.get(CONF_CO2_THRESHOLD, DEFAULT_CO2_THRESHOLD),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=400, max=2000, step=50, unit_of_measurement="ppm"
                        )
                    ),
                    vol.Optional(
                        CONF_CO2_HIGH_DELAY_MINUTES,
                        default=current.get(
                            CONF_CO2_HIGH_DELAY_MINUTES, DEFAULT_CO2_HIGH_DELAY_MINUTES
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=60, step=1, unit_of_measurement="min"
                        )
                    ),
                }
            ),
        )

    async def async_step_rooms(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure room settings (one room at a time)."""
        rooms_config: dict[str, Any] = {
            **self.config_entry.data.get(CONF_ROOMS, {}),
            **self.config_entry.options.get(CONF_ROOMS, {}),
        }
        room_ids = list(rooms_config.keys())
        total = len(room_ids)

        if user_input is not None:
            room_id = room_ids[self._room_index]
            rooms_config[room_id] = {
                **rooms_config.get(room_id, {}),
                "window_sensors": user_input.get("window_sensors") or [],
                "humidity_sensor": user_input.get("humidity_sensor"),
                "co2_sensor": user_input.get("co2_sensor"),
                "is_bedroom": user_input.get("is_bedroom", False),
            }
            self._room_index += 1

            if self._room_index >= total:
                options = {**self.config_entry.options, CONF_ROOMS: rooms_config}
                return self.async_create_entry(title="", data=options)
            return await self.async_step_rooms()

        room_id = room_ids[self._room_index]
        room_data = rooms_config.get(room_id, {})
        room_name = _get_device_name(self.hass, room_data.get("climate_entity_id")) or room_data.get("name") or room_id

        return self.async_show_form(
            step_id="rooms",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "window_sensors",
                        description={"suggested_value": room_data.get("window_sensors") or []},
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="binary_sensor",
                            device_class=["window", "door", "opening"],
                            multiple=True,
                        )
                    ),
                    vol.Optional(
                        "humidity_sensor",
                        description={"suggested_value": room_data.get("humidity_sensor")},
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor",
                            device_class="humidity",
                        )
                    ),
                    vol.Optional(
                        "co2_sensor",
                        description={"suggested_value": room_data.get("co2_sensor")},
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor",
                            device_class="carbon_dioxide",
                        )
                    ),
                    vol.Optional(
                        "is_bedroom",
                        default=room_data.get("is_bedroom", False),
                    ): selector.BooleanSelector(),
                }
            ),
            description_placeholders={
                "room_name": room_name,
                "room_number": str(self._room_index + 1),
                "total_rooms": str(total),
            },
        )
