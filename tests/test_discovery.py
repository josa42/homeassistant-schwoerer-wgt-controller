"""Tests for the discovery module."""

from __future__ import annotations

import pytest

from custom_components.schwoerer_wgt_controller.discovery import (
    DiscoveredEntities,
    DiscoveredRoom,
    _extract_room_number,
    _extract_room_number_from_entity_type,
    validate_discovery,
)


class TestExtractRoomNumber:
    """Test room number extraction."""

    def test_extract_from_entity_id(self):
        """Test extracting room number from entity ID."""
        result = _extract_room_number("climate.wgt_room_1", {})
        assert result == 1

    def test_extract_from_entity_id_room2(self):
        """Test extracting room number 2."""
        result = _extract_room_number("climate.wgt_room_2_climate", {})
        assert result == 2

    def test_no_room_number(self):
        """Test when no room number found."""
        result = _extract_room_number("climate.wgt_main", {})
        assert result is None


class TestExtractRoomNumberFromEntityType:
    """Test room number extraction from entity type."""

    def test_extract_auxiliary_heating(self):
        """Test extracting from auxiliary_heating_enabled_room_1."""
        result = _extract_room_number_from_entity_type("auxiliary_heating_enabled_room_1")
        assert result == 1

    def test_extract_room_5(self):
        """Test extracting room 5."""
        result = _extract_room_number_from_entity_type("some_feature_room_5")
        assert result == 5


class TestDiscoveredRoom:
    """Test DiscoveredRoom dataclass."""

    def test_create_room(self):
        """Test creating a discovered room."""
        room = DiscoveredRoom(
            number=1,
            name="Wohnzimmer",
            climate_entity_id="climate.wgt_room_1",
        )

        assert room.number == 1
        assert room.name == "Wohnzimmer"
        assert room.climate_entity_id == "climate.wgt_room_1"
        assert room.auxiliary_heating_entity_id is None


class TestValidateDiscovery:
    """Test discovery validation."""

    @pytest.mark.asyncio
    async def test_valid_discovery(self):
        """Test valid discovery."""
        discovered = DiscoveredEntities(
            rooms=[
                DiscoveredRoom(
                    number=1,
                    name="Wohnzimmer",
                    climate_entity_id="climate.wgt_room_1",
                )
            ],
            outdoor_temp_entity="sensor.wgt_outdoor_temp",
        )

        errors = await validate_discovery(discovered)
        assert errors == []

    @pytest.mark.asyncio
    async def test_no_rooms(self):
        """Test discovery with no rooms."""
        discovered = DiscoveredEntities(
            rooms=[],
            outdoor_temp_entity="sensor.wgt_outdoor_temp",
        )

        errors = await validate_discovery(discovered)
        assert "no_rooms_found" in errors

    @pytest.mark.asyncio
    async def test_no_outdoor_temp(self):
        """Test discovery with no outdoor temp sensor."""
        discovered = DiscoveredEntities(
            rooms=[
                DiscoveredRoom(
                    number=1,
                    name="Wohnzimmer",
                    climate_entity_id="climate.wgt_room_1",
                )
            ],
        )

        errors = await validate_discovery(discovered)
        assert "no_outdoor_temp_sensor" in errors
