"""Tests for the controller logic."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from unittest.mock import MagicMock, patch

from custom_components.schwoerer_wgt_controller.controller import (
    ActionType,
    AuxiliaryHeatingRule,
    ControllerState,
    FanLevelRule,
    HeatingLockRule,
    HeatingReleaseRule,
    NightModeRule,
    RoomState,
    RoomTemperatureRule,
    RuleResult,
    VacationModeRule,
    _parse_time,
)


class TestParseTime:
    """Test time parsing."""

    def test_parse_time_morning(self):
        """Test parsing morning time."""
        result = _parse_time("05:00")
        assert result == time(5, 0)

    def test_parse_time_evening(self):
        """Test parsing evening time."""
        result = _parse_time("20:00")
        assert result == time(20, 0)

    def test_parse_time_with_minutes(self):
        """Test parsing time with minutes."""
        result = _parse_time("14:30")
        assert result == time(14, 30)


class TestControllerState:
    """Test ControllerState dataclass."""

    def test_default_values(self):
        """Test default values."""
        state = ControllerState()
        assert state.rooms == {}
        assert state.heat_pump_heating_enabled is False
        assert state.is_night is False
        assert state.is_vacation is False
        assert state.fan_level == 2


class TestRuleResult:
    """Test RuleResult dataclass."""

    def test_create_result(self):
        """Test creating a rule result."""
        result = RuleResult(
            action=ActionType.SET_ROOM_TEMPERATURE,
            target="climate.room_1",
            value=20.0,
            reason="Normal temperature",
            priority=10,
        )

        assert result.action == ActionType.SET_ROOM_TEMPERATURE
        assert result.target == "climate.room_1"
        assert result.value == 20.0
        assert result.reason == "Normal temperature"
        assert result.priority == 10


class TestHeatingLockRule:
    """Test HeatingLockRule."""

    def test_heating_locked(self):
        """Test when heating is locked."""
        coordinator = MagicMock()
        # Mock internal heating lock switch
        lock_switch = MagicMock()
        lock_switch.is_on = True
        coordinator.heating_lock_switch = lock_switch

        rule = HeatingLockRule(coordinator)
        state = ControllerState()

        results = rule.evaluate(state)

        assert state.is_heating_locked is True
        assert len(results) == 1
        assert results[0].action == ActionType.SET_HEAT_PUMP_HEATING
        assert results[0].value is False

    def test_heating_not_locked(self):
        """Test when heating is not locked."""
        coordinator = MagicMock()
        # Mock internal heating lock switch as off
        lock_switch = MagicMock()
        lock_switch.is_on = False
        coordinator.heating_lock_switch = lock_switch

        rule = HeatingLockRule(coordinator)
        state = ControllerState()

        results = rule.evaluate(state)

        assert state.is_heating_locked is False
        assert len(results) == 0


class TestHeatingReleaseRule:
    """Test HeatingReleaseRule."""

    def test_heating_needed(self):
        """Test when heating is needed (cold outside)."""
        coordinator = MagicMock()
        coordinator.config = {"outdoor_temp_heating_threshold": 16.0}

        rule = HeatingReleaseRule(coordinator)
        state = ControllerState(outdoor_temperature=10.0)

        results = rule.evaluate(state)

        assert state.heat_pump_heating_enabled is True
        assert len(results) == 1
        assert results[0].value is True
        assert "10.0°C < 16.0°C" in results[0].reason

    def test_heating_not_needed(self):
        """Test when heating is not needed (warm outside)."""
        coordinator = MagicMock()
        coordinator.config = {"outdoor_temp_heating_threshold": 16.0}

        rule = HeatingReleaseRule(coordinator)
        state = ControllerState(outdoor_temperature=20.0)

        results = rule.evaluate(state)

        assert state.heat_pump_heating_enabled is False
        assert len(results) == 1
        assert results[0].value is False


class TestNightModeRule:
    """Test NightModeRule."""

    def test_is_night(self):
        """Test when it's night time."""
        coordinator = MagicMock()
        coordinator.config = {"night_start": "20:00", "night_end": "05:00"}

        rule = NightModeRule(coordinator)
        state = ControllerState()

        # Mock time to 22:00
        with patch(
            "custom_components.schwoerer_wgt_controller.controller.datetime"
        ) as mock_dt:
            mock_dt.now.return_value.time.return_value = time(22, 0)
            rule.evaluate(state)

        assert state.is_night is True

    def test_is_not_night(self):
        """Test when it's not night time."""
        coordinator = MagicMock()
        coordinator.config = {"night_start": "20:00", "night_end": "05:00"}

        rule = NightModeRule(coordinator)
        state = ControllerState()

        # Mock time to 12:00
        with patch(
            "custom_components.schwoerer_wgt_controller.controller.datetime"
        ) as mock_dt:
            mock_dt.now.return_value.time.return_value = time(12, 0)
            rule.evaluate(state)

        assert state.is_night is False


class TestVacationModeRule:
    """Test VacationModeRule."""

    def test_vacation_on(self):
        """Test when vacation mode is on."""
        coordinator = MagicMock()
        # Mock internal vacation mode switch
        vacation_switch = MagicMock()
        vacation_switch.is_on = True
        coordinator.vacation_mode_switch = vacation_switch

        rule = VacationModeRule(coordinator)
        state = ControllerState()

        rule.evaluate(state)

        assert state.is_vacation is True

    def test_vacation_off(self):
        """Test when vacation mode is off."""
        coordinator = MagicMock()
        # Mock internal vacation mode switch as off
        vacation_switch = MagicMock()
        vacation_switch.is_on = False
        coordinator.vacation_mode_switch = vacation_switch

        rule = VacationModeRule(coordinator)
        state = ControllerState()

        rule.evaluate(state)

        assert state.is_vacation is False


class TestRoomTemperatureRule:
    """Test RoomTemperatureRule."""

    def test_normal_temperature(self):
        """Test normal temperature setting."""
        coordinator = MagicMock()
        coordinator.config = {
            "temperature_normal": 20.0,
            "temperature_night": 19.0,
            "rooms": {},
        }

        rule = RoomTemperatureRule(coordinator)
        state = ControllerState(
            rooms={
                "room_1": RoomState(
                    room_id="room_1",
                    room_name="Wohnzimmer",
                    climate_entity_id="climate.room_1",
                )
            }
        )

        results = rule.evaluate(state)

        assert len(results) == 1
        assert results[0].value == 20.0
        assert state.rooms["room_1"].target_temperature == 20.0
        assert state.rooms["room_1"].mode == "normal"

    def test_night_temperature(self):
        """Test night temperature setting."""
        coordinator = MagicMock()
        coordinator.config = {
            "temperature_normal": 20.0,
            "temperature_night": 19.0,
            "rooms": {},
        }

        rule = RoomTemperatureRule(coordinator)
        state = ControllerState(
            is_night=True,
            rooms={
                "room_1": RoomState(
                    room_id="room_1",
                    room_name="Wohnzimmer",
                    climate_entity_id="climate.room_1",
                )
            },
        )

        results = rule.evaluate(state)

        assert len(results) == 1
        assert results[0].value == 19.0
        assert state.rooms["room_1"].mode == "night"

    def test_global_temperature_used(self):
        """Test that global temperature is used for all rooms."""
        coordinator = MagicMock()
        coordinator.config = {
            "temperature_normal": 20.0,
            "temperature_night": 19.0,
            "rooms": {
                "room_1": {}
            },
        }

        rule = RoomTemperatureRule(coordinator)
        state = ControllerState(
            rooms={
                "room_1": RoomState(
                    room_id="room_1",
                    room_name="Wohnzimmer",
                    climate_entity_id="climate.room_1",
                )
            }
        )

        results = rule.evaluate(state)

        assert results[0].value == 20.0


class TestFanLevelRule:
    """Test FanLevelRule."""

    def test_normal_fan_level(self):
        """Test normal fan level."""
        coordinator = MagicMock()
        coordinator.config = {
            "fan_level_normal": 2,
            "fan_level_night": 1,
            "rooms": {},
        }
        # No manual override
        coordinator.fan_level_override_select = None

        rule = FanLevelRule(coordinator)
        state = ControllerState()

        rule.evaluate(state)

        assert state.fan_level == 2

    def test_night_fan_level(self):
        """Test night fan level."""
        coordinator = MagicMock()
        coordinator.config = {
            "fan_level_normal": 2,
            "fan_level_night": 1,
            "rooms": {},
        }
        # No manual override
        coordinator.fan_level_override_select = None

        rule = FanLevelRule(coordinator)
        state = ControllerState(is_night=True)

        rule.evaluate(state)

        assert state.fan_level == 1

    def test_high_humidity_fan_level(self):
        """Test high humidity fan level."""
        coordinator = MagicMock()
        coordinator.config = {
            "fan_level_normal": 2,
            "fan_level_high_humidity": 3,
            "humidity_threshold": 70,
            "rooms": {
                "room_1": {
                    "humidity_sensor": "sensor.room_1_humidity",
                }
            },
        }

        # No manual override
        coordinator.fan_level_override_select = None

        # Mock humidity sensor
        def get_state(entity_id):
            if entity_id == "sensor.room_1_humidity":
                return MagicMock(state="75")
            return None

        coordinator.hass.states.get.side_effect = get_state

        rule = FanLevelRule(coordinator)
        state = ControllerState()

        rule.evaluate(state)

        assert state.fan_level == 3

    def test_vacation_fan_level(self):
        """Test fan level during vacation mode."""
        coordinator = MagicMock()
        coordinator.config = {
            "fan_level_normal": 2,
            "fan_level_vacation": 1,
            "rooms": {},
        }
        coordinator.fan_level_override_select = None

        rule = FanLevelRule(coordinator)
        state = ControllerState(is_vacation=True)

        rule.evaluate(state)

        assert state.fan_level == 1

    def test_manual_override_takes_priority(self):
        """Test that manual fan level override wins over automation."""
        coordinator = MagicMock()
        coordinator.config = {
            "fan_level_normal": 2,
            "fan_level_night": 1,
            "rooms": {},
        }
        override = MagicMock()
        override.current_option = "3"
        coordinator.fan_level_override_select = override

        rule = FanLevelRule(coordinator)
        state = ControllerState(is_night=True)

        results = rule.evaluate(state)

        assert state.fan_level == 3
        assert results[0].priority == 100

    def test_manual_override_auto_falls_through(self):
        """Test that 'Auto' override is ignored and automation applies."""
        coordinator = MagicMock()
        coordinator.config = {
            "fan_level_normal": 2,
            "fan_level_night": 1,
            "rooms": {},
        }
        override = MagicMock()
        override.current_option = "Auto"
        coordinator.fan_level_override_select = override

        rule = FanLevelRule(coordinator)
        state = ControllerState(is_night=True)

        rule.evaluate(state)

        assert state.fan_level == 1

    def test_humidity_ignored_when_window_open(self):
        """Test that high humidity is ignored when a window is open."""
        sensor = "sensor.room_1_humidity"
        window = "binary_sensor.window_1"
        now = datetime.now(UTC)

        humidity_state = MagicMock(state="80")
        window_state = MagicMock()
        window_state.state = "on"
        window_state.last_changed = now - timedelta(minutes=5)

        coordinator = MagicMock()
        coordinator.config = {
            "fan_level_normal": 2,
            "fan_level_high_humidity": 3,
            "humidity_threshold": 70.0,
            "rooms": {
                "room_1": {
                    "humidity_sensor": sensor,
                    "window_sensors": [window],
                }
            },
        }
        coordinator.fan_level_override_select = None

        def get_state(entity_id):
            if entity_id == sensor:
                return humidity_state
            if entity_id == window:
                return window_state
            return None

        coordinator.hass.states.get.side_effect = get_state

        rule = FanLevelRule(coordinator)
        state = ControllerState()

        rule.evaluate(state)

        assert state.fan_level == 2

    def test_high_co2_elevates_fan(self):
        """Test that sustained high CO2 elevates the fan level."""
        sensor = "sensor.room_1_co2"
        coordinator = MagicMock()
        coordinator.config = {
            "fan_level_normal": 2,
            "fan_level_high_co2": 3,
            "co2_threshold": 1000,
            "co2_high_delay_minutes": 5,
            "rooms": {"room_1": {"co2_sensor": sensor}},
        }
        coordinator.fan_level_override_select = None
        coordinator.hass.states.get.return_value = MagicMock(state="1200")

        rule = FanLevelRule(coordinator)
        # Seed the onset time so the delay has already elapsed
        rule._co2_high_since[sensor] = datetime.now(UTC) - timedelta(minutes=10)

        state = ControllerState()
        rule.evaluate(state)

        assert state.fan_level == 3

    def test_co2_below_threshold_no_elevation(self):
        """Test that CO2 below threshold does not elevate fan."""
        sensor = "sensor.room_1_co2"
        coordinator = MagicMock()
        coordinator.config = {
            "fan_level_normal": 2,
            "fan_level_high_co2": 3,
            "co2_threshold": 1000,
            "co2_high_delay_minutes": 5,
            "rooms": {"room_1": {"co2_sensor": sensor}},
        }
        coordinator.fan_level_override_select = None
        coordinator.hass.states.get.return_value = MagicMock(state="800")

        rule = FanLevelRule(coordinator)
        state = ControllerState()
        rule.evaluate(state)

        assert state.fan_level == 2

    def test_co2_not_elevated_before_delay(self):
        """Test that CO2 above threshold but within delay period does not elevate fan."""
        sensor = "sensor.room_1_co2"
        coordinator = MagicMock()
        coordinator.config = {
            "fan_level_normal": 2,
            "fan_level_high_co2": 3,
            "co2_threshold": 1000,
            "co2_high_delay_minutes": 5,
            "rooms": {"room_1": {"co2_sensor": sensor}},
        }
        coordinator.fan_level_override_select = None
        coordinator.hass.states.get.return_value = MagicMock(state="1200")

        rule = FanLevelRule(coordinator)
        # Set onset to only 1 minute ago — delay of 5 min not elapsed
        rule._co2_high_since[sensor] = datetime.now(UTC) - timedelta(minutes=1)

        state = ControllerState()
        rule.evaluate(state)

        assert state.fan_level == 2

    def test_co2_ignored_when_window_open(self):
        """Test that high CO2 is ignored when a window is open."""
        co2_sensor = "sensor.room_1_co2"
        window = "binary_sensor.window_1"
        now = datetime.now(UTC)
        window_state = MagicMock()
        window_state.state = "on"
        window_state.last_changed = now - timedelta(minutes=5)

        coordinator = MagicMock()
        coordinator.config = {
            "fan_level_normal": 2,
            "fan_level_high_co2": 3,
            "co2_threshold": 1000,
            "co2_high_delay_minutes": 5,
            "rooms": {"room_1": {"co2_sensor": co2_sensor, "window_sensors": [window]}},
        }
        coordinator.fan_level_override_select = None

        def get_state(entity_id):
            if entity_id == co2_sensor:
                return MagicMock(state="1500")
            if entity_id == window:
                return window_state
            return None

        coordinator.hass.states.get.side_effect = get_state

        rule = FanLevelRule(coordinator)
        rule._co2_high_since[co2_sensor] = now - timedelta(minutes=10)

        state = ControllerState()
        rule.evaluate(state)

        assert state.fan_level == 2

    def test_co2_takes_priority_over_vacation(self):
        """Test that high CO2 overrides vacation fan level."""
        sensor = "sensor.room_1_co2"
        coordinator = MagicMock()
        coordinator.config = {
            "fan_level_normal": 2,
            "fan_level_vacation": 1,
            "fan_level_high_co2": 3,
            "co2_threshold": 1000,
            "co2_high_delay_minutes": 5,
            "rooms": {"room_1": {"co2_sensor": sensor}},
        }
        coordinator.fan_level_override_select = None
        coordinator.hass.states.get.return_value = MagicMock(state="1200")

        rule = FanLevelRule(coordinator)
        rule._co2_high_since[sensor] = datetime.now(UTC) - timedelta(minutes=10)

        state = ControllerState(is_vacation=True)
        rule.evaluate(state)

        assert state.fan_level == 3

    def test_co2_resets_when_drops_below_threshold(self):
        """Test that the onset timer clears when CO2 drops below threshold."""
        sensor = "sensor.room_1_co2"
        coordinator = MagicMock()
        coordinator.config = {
            "fan_level_normal": 2,
            "fan_level_high_co2": 3,
            "co2_threshold": 1000,
            "co2_high_delay_minutes": 5,
            "rooms": {"room_1": {"co2_sensor": sensor}},
        }
        coordinator.fan_level_override_select = None
        coordinator.hass.states.get.return_value = MagicMock(state="800")

        rule = FanLevelRule(coordinator)
        rule._co2_high_since[sensor] = datetime.now(UTC) - timedelta(minutes=10)

        state = ControllerState()
        rule.evaluate(state)

        assert rule._co2_high_since[sensor] is None
        assert state.fan_level == 2


class TestAuxiliaryHeatingRule:
    """Test AuxiliaryHeatingRule."""

    def _make_coordinator(self, room_config=None):
        coordinator = MagicMock()
        coordinator.config = {
            "outdoor_temp_auxiliary_heating_threshold": 10.0,
            "rooms": {
                "room_1": {"auxiliary_heating_entity": "climate.aux_room1"} if room_config is None else room_config,
            },
        }
        coordinator.hass.states.get.return_value = None
        return coordinator

    def test_enabled_when_cold_and_heating_active(self):
        """Test aux heating turns on when it's cold and heat pump is heating."""
        rule = AuxiliaryHeatingRule(self._make_coordinator())
        state = ControllerState(
            outdoor_temperature=5.0,
            heat_pump_heating_enabled=True,
            rooms={"room_1": RoomState("room_1", "Room 1", "climate.room1")},
        )

        results = rule.evaluate(state)

        assert len(results) == 1
        assert results[0].action == ActionType.SET_AUXILIARY_HEATING
        assert results[0].target == "climate.aux_room1"
        assert results[0].value is True
        assert state.rooms["room_1"].auxiliary_heating_enabled is True

    def test_disabled_when_outdoor_temp_above_threshold(self):
        """Test aux heating stays off when outdoor temp is above threshold."""
        rule = AuxiliaryHeatingRule(self._make_coordinator())
        state = ControllerState(
            outdoor_temperature=15.0,
            heat_pump_heating_enabled=True,
            rooms={"room_1": RoomState("room_1", "Room 1", "climate.room1")},
        )

        results = rule.evaluate(state)

        assert results[0].value is False
        assert "≥" in results[0].reason

    def test_disabled_when_heat_pump_not_heating(self):
        """Test aux heating stays off when heat pump is not heating."""
        rule = AuxiliaryHeatingRule(self._make_coordinator())
        state = ControllerState(
            outdoor_temperature=5.0,
            heat_pump_heating_enabled=False,
            rooms={"room_1": RoomState("room_1", "Room 1", "climate.room1")},
        )

        results = rule.evaluate(state)

        assert results[0].value is False

    def test_disabled_in_bedroom_at_night(self):
        """Test aux heating is disabled in bedrooms at night."""
        coordinator = self._make_coordinator(
            room_config={
                "auxiliary_heating_entity": "climate.aux_room1",
                "is_bedroom": True,
            }
        )
        rule = AuxiliaryHeatingRule(coordinator)
        state = ControllerState(
            outdoor_temperature=5.0,
            heat_pump_heating_enabled=True,
            is_night=True,
            rooms={"room_1": RoomState("room_1", "Room 1", "climate.room1")},
        )

        results = rule.evaluate(state)

        assert results[0].value is False
        assert "nachts" in results[0].reason

    def test_enabled_in_bedroom_during_day(self):
        """Test aux heating works normally in bedrooms during daytime."""
        coordinator = self._make_coordinator(
            room_config={
                "auxiliary_heating_entity": "climate.aux_room1",
                "is_bedroom": True,
            }
        )
        rule = AuxiliaryHeatingRule(coordinator)
        state = ControllerState(
            outdoor_temperature=5.0,
            heat_pump_heating_enabled=True,
            is_night=False,
            rooms={"room_1": RoomState("room_1", "Room 1", "climate.room1")},
        )

        results = rule.evaluate(state)

        assert results[0].value is True

    def test_no_aux_entity_skips_room(self):
        """Test that rooms without an aux entity are skipped."""
        coordinator = self._make_coordinator(room_config={})  # no auxiliary_heating_entity
        rule = AuxiliaryHeatingRule(coordinator)
        state = ControllerState(
            outdoor_temperature=5.0,
            heat_pump_heating_enabled=True,
            rooms={"room_1": RoomState("room_1", "Room 1", "climate.room1")},
        )

        results = rule.evaluate(state)

        assert results == []

    def test_unknown_outdoor_temp_disables(self):
        """Test that aux heating is disabled when outdoor temp is unknown."""
        rule = AuxiliaryHeatingRule(self._make_coordinator())
        state = ControllerState(
            outdoor_temperature=None,
            heat_pump_heating_enabled=True,
            rooms={"room_1": RoomState("room_1", "Room 1", "climate.room1")},
        )

        results = rule.evaluate(state)

        assert results[0].value is False
        assert "unbekannt" in results[0].reason

    def test_at_threshold_not_enabled(self):
        """Test that aux heating is not enabled exactly at the threshold."""
        rule = AuxiliaryHeatingRule(self._make_coordinator())
        state = ControllerState(
            outdoor_temperature=10.0,  # exactly at threshold
            heat_pump_heating_enabled=True,
            rooms={"room_1": RoomState("room_1", "Room 1", "climate.room1")},
        )

        results = rule.evaluate(state)

        assert results[0].value is False


class TestHeatingReleaseRuleEdgeCases:
    """Additional edge cases for HeatingReleaseRule."""

    def test_skipped_when_heating_locked(self):
        """Test that the rule is a no-op when heating is locked."""
        coordinator = MagicMock()
        coordinator.config = {"outdoor_temp_heating_threshold": 16.0}

        rule = HeatingReleaseRule(coordinator)
        state = ControllerState(is_heating_locked=True, outdoor_temperature=5.0)

        results = rule.evaluate(state)

        assert results == []

    def test_at_threshold_does_not_heat(self):
        """Test that exactly at the threshold, heating is not enabled."""
        coordinator = MagicMock()
        coordinator.config = {"outdoor_temp_heating_threshold": 16.0}

        rule = HeatingReleaseRule(coordinator)
        state = ControllerState(outdoor_temperature=16.0)

        results = rule.evaluate(state)

        assert results[0].value is False


class TestRoomTemperatureRuleEdgeCases:
    """Additional edge cases for RoomTemperatureRule."""

    def test_window_open_overrides_night_mode(self):
        """Test that an open window takes priority over night mode."""
        sensor = "binary_sensor.window_1"
        now = datetime.now(UTC)
        window_state = MagicMock()
        window_state.state = "on"
        window_state.last_changed = now - timedelta(minutes=5)

        coordinator = MagicMock()
        coordinator.config = {
            "temperature_normal": 20.0,
            "temperature_night": 19.0,
            "temperature_window_open": 12.0,
            "rooms": {"room_1": {"window_sensors": [sensor]}},
        }
        coordinator.hass.states.get.return_value = window_state

        rule = RoomTemperatureRule(coordinator)
        state = ControllerState(
            is_night=True,
            rooms={"room_1": RoomState("room_1", "Room 1", "climate.room1")},
        )

        results = rule.evaluate(state)

        assert results[0].value == 12.0
        assert state.rooms["room_1"].mode == "window_open"

    def test_window_open_overrides_vacation_mode(self):
        """Test that an open window takes priority over vacation mode."""
        sensor = "binary_sensor.window_1"
        now = datetime.now(UTC)
        window_state = MagicMock()
        window_state.state = "on"
        window_state.last_changed = now - timedelta(minutes=5)

        coordinator = MagicMock()
        coordinator.config = {
            "temperature_normal": 20.0,
            "temperature_vacation": 16.0,
            "temperature_window_open": 12.0,
            "rooms": {"room_1": {"window_sensors": [sensor]}},
        }
        coordinator.hass.states.get.return_value = window_state

        rule = RoomTemperatureRule(coordinator)
        state = ControllerState(
            is_vacation=True,
            rooms={"room_1": RoomState("room_1", "Room 1", "climate.room1")},
        )

        results = rule.evaluate(state)

        assert results[0].value == 12.0
        assert state.rooms["room_1"].mode == "window_open"

    def test_window_not_open_long_enough(self):
        """Test that a recently opened window is not yet treated as open."""
        sensor = "binary_sensor.window_1"
        now = datetime.now(UTC)
        window_state = MagicMock()
        window_state.state = "on"
        window_state.last_changed = now - timedelta(seconds=30)  # less than 1 min delay

        coordinator = MagicMock()
        coordinator.config = {
            "temperature_normal": 20.0,
            "temperature_window_open": 12.0,
            "rooms": {"room_1": {"window_sensors": [sensor]}},
        }
        coordinator.hass.states.get.return_value = window_state

        rule = RoomTemperatureRule(coordinator)
        state = ControllerState(
            rooms={"room_1": RoomState("room_1", "Room 1", "climate.room1")},
        )

        results = rule.evaluate(state)

        assert state.rooms["room_1"].mode == "normal"
