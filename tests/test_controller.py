"""Tests for the controller logic."""

from __future__ import annotations

from datetime import time
from unittest.mock import MagicMock, patch

from custom_components.schwoerer_wgt_controller.controller import (
    ActionType,
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
        coordinator.config = {"heating_lock_entity": "input_boolean.heating_lock"}
        coordinator.hass.states.get.return_value = MagicMock(state="on")

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
        coordinator.config = {"heating_lock_entity": "input_boolean.heating_lock"}
        coordinator.hass.states.get.return_value = MagicMock(state="off")

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
        coordinator.config = {"vacation_mode_entity": "input_boolean.vacation"}
        coordinator.hass.states.get.return_value = MagicMock(state="on")

        rule = VacationModeRule(coordinator)
        state = ControllerState()

        rule.evaluate(state)

        assert state.is_vacation is True

    def test_vacation_off(self):
        """Test when vacation mode is off."""
        coordinator = MagicMock()
        coordinator.config = {"vacation_mode_entity": "input_boolean.vacation"}
        coordinator.hass.states.get.return_value = MagicMock(state="off")

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

    def test_room_specific_override(self):
        """Test room-specific temperature override."""
        coordinator = MagicMock()
        coordinator.config = {
            "temperature_normal": 20.0,
            "temperature_night": 19.0,
            "rooms": {
                "room_1": {
                    "temperature_normal": 22.0,
                }
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

        assert results[0].value == 22.0


class TestFanLevelRule:
    """Test FanLevelRule."""

    def test_normal_fan_level(self):
        """Test normal fan level."""
        coordinator = MagicMock()
        coordinator.config = {
            "fan_level_normal": 2,
            "fan_level_night": 1,
        }
        coordinator.hass.states.get.return_value = None

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
        }
        coordinator.hass.states.get.return_value = None

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
            "humidity_sensor_entity": "sensor.humidity",
        }

        # Mock humidity sensor
        def get_state(entity_id):
            if entity_id == "sensor.humidity":
                return MagicMock(state="75")
            return None

        coordinator.hass.states.get.side_effect = get_state

        rule = FanLevelRule(coordinator)
        state = ControllerState()

        rule.evaluate(state)

        assert state.fan_level == 3
