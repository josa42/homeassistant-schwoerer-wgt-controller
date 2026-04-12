"""Constants for the Schwörer WGT Controller integration."""

from __future__ import annotations

DOMAIN = "schwoerer_wgt_controller"

# Integration we depend on
SCHWOERER_LUEFTUNG_DOMAIN = "schwoerer_lueftung"

# Configuration keys
CONF_TEST_MODE = "test_mode"
CONF_VACATION_MODE_ENTITY = "vacation_mode_entity"
CONF_HEATING_LOCK_ENTITY = "heating_lock_entity"
CONF_HUMIDITY_SENSOR_ENTITY = "humidity_sensor_entity"
CONF_FAN_LEVEL_OVERRIDE_ENTITY = "fan_level_override_entity"
CONF_ROOMS = "rooms"

# Room configuration keys
CONF_ROOM_NAME = "name"
CONF_ROOM_CLIMATE_ENTITY = "climate_entity"
CONF_ROOM_WINDOW_SENSOR = "window_sensor"
CONF_ROOM_FLOOR = "floor"  # "eg" or "og"
CONF_ROOM_TEMPERATURE_NORMAL = "temperature_normal"
CONF_ROOM_TEMPERATURE_NIGHT = "temperature_night"
CONF_ROOM_TEMPERATURE_VACATION = "temperature_vacation"
CONF_ROOM_TEMPERATURE_WINDOW_OPEN = "temperature_window_open"

# Global temperature settings
CONF_TEMPERATURE_NORMAL = "temperature_normal"
CONF_TEMPERATURE_NIGHT = "temperature_night"
CONF_TEMPERATURE_VACATION = "temperature_vacation"
CONF_TEMPERATURE_WINDOW_OPEN = "temperature_window_open"

# Time settings
CONF_NIGHT_START = "night_start"
CONF_NIGHT_END = "night_end"

# Fan level settings
CONF_FAN_LEVEL_NORMAL = "fan_level_normal"
CONF_FAN_LEVEL_NIGHT = "fan_level_night"
CONF_FAN_LEVEL_VACATION = "fan_level_vacation"
CONF_FAN_LEVEL_HIGH_HUMIDITY = "fan_level_high_humidity"

# Threshold settings
CONF_OUTDOOR_TEMP_HEATING_THRESHOLD = "outdoor_temp_heating_threshold"
CONF_HUMIDITY_THRESHOLD = "humidity_threshold"
CONF_WINDOW_OPEN_DELAY_MINUTES = "window_open_delay_minutes"
CONF_HEAT_PUMP_CHANGE_LOCKOUT_MINUTES = "heat_pump_change_lockout_minutes"

# Default values
DEFAULT_TEMPERATURE_NORMAL = 20.0
DEFAULT_TEMPERATURE_NIGHT = 19.0
DEFAULT_TEMPERATURE_VACATION = 18.0
DEFAULT_TEMPERATURE_WINDOW_OPEN = 12.0

DEFAULT_NIGHT_START = "20:00"
DEFAULT_NIGHT_END = "05:00"

DEFAULT_FAN_LEVEL_NORMAL = 2
DEFAULT_FAN_LEVEL_NIGHT = 1
DEFAULT_FAN_LEVEL_VACATION = 1
DEFAULT_FAN_LEVEL_HIGH_HUMIDITY = 3

DEFAULT_OUTDOOR_TEMP_HEATING_THRESHOLD = 16.0
DEFAULT_HUMIDITY_THRESHOLD = 70.0
DEFAULT_WINDOW_OPEN_DELAY_MINUTES = 1
DEFAULT_HEAT_PUMP_CHANGE_LOCKOUT_MINUTES = 30

# Update interval in seconds
DEFAULT_UPDATE_INTERVAL = 900  # 15 minutes

# Floor constants
FLOOR_EG = "eg"
FLOOR_OG = "og"

# Entity type attributes from schwoerer_lueftung
ENTITY_TYPE_CLIMATE_ROOM = "climate_room"
ENTITY_TYPE_HEAT_PUMP_HEATING = "heat_pump_heating_enabled"
ENTITY_TYPE_HEAT_PUMP_COOLING = "heat_pump_cooling_enabled"
ENTITY_TYPE_FAN_SPEED = "fan_speed"
ENTITY_TYPE_OUTDOOR_TEMP = "temperature_t10_outdoor"
ENTITY_TYPE_AUXILIARY_HEATING = "auxiliary_heating_enabled_room"

# Modes
MODE_NORMAL = "normal"
MODE_NIGHT = "night"
MODE_VACATION = "vacation"
MODE_WINDOW_OPEN = "window_open"
