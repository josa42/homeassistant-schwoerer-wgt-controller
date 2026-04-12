"""Discovery module for finding schwoerer_lueftung entities."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    ENTITY_TYPE_AUXILIARY_HEATING,
    ENTITY_TYPE_FAN_SPEED,
    ENTITY_TYPE_HEAT_PUMP_COOLING,
    ENTITY_TYPE_HEAT_PUMP_HEATING,
    ENTITY_TYPE_OUTDOOR_TEMP,
    SCHWOERER_LUEFTUNG_DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class DiscoveredRoom:
    """Represents a discovered room from schwoerer_lueftung."""

    number: int
    name: str
    climate_entity_id: str
    auxiliary_heating_entity_id: str | None = None


@dataclass
class DiscoveredEntities:
    """Container for all discovered entities."""

    rooms: list[DiscoveredRoom]
    heat_pump_heating_entity: str | None = None
    heat_pump_cooling_entity: str | None = None
    fan_speed_entity: str | None = None
    outdoor_temp_entity: str | None = None


async def discover_entities(hass: HomeAssistant) -> DiscoveredEntities:
    """Discover entities from schwoerer_lueftung integration."""
    entity_reg = er.async_get(hass)

    rooms: dict[int, DiscoveredRoom] = {}
    result = DiscoveredEntities(rooms=[])

    _LOGGER.debug("Starting entity discovery")

    # First pass: find all schwoerer_lueftung entities by platform
    schwoerer_entities: list[tuple[str, Any, str | None]] = []
    
    for entry in entity_reg.entities.values():
        if entry.platform == SCHWOERER_LUEFTUNG_DOMAIN:
            state = hass.states.get(entry.entity_id)
            entity_type = state.attributes.get("entity_type") if state else None
            schwoerer_entities.append((entry.entity_id, state, entity_type))
            _LOGGER.debug(
                "Found schwoerer_lueftung entity: %s (entity_type=%s)",
                entry.entity_id, entity_type
            )

    _LOGGER.debug("Found %d schwoerer_lueftung entities", len(schwoerer_entities))

    # Process entities
    for entity_id, state, entity_type in schwoerer_entities:
        if state is None:
            continue

        attrs = state.attributes

        # Handle climate entities (rooms) - they might not have entity_type attribute
        if entity_id.startswith("climate."):
            room_number = _extract_room_number(entity_id, attrs)
            if room_number:
                room_name = _get_room_name(state, room_number)
                _LOGGER.debug("Found room %d: %s (%s)", room_number, room_name, entity_id)
                if room_number not in rooms:
                    rooms[room_number] = DiscoveredRoom(
                        number=room_number,
                        name=room_name,
                        climate_entity_id=entity_id,
                    )
                else:
                    rooms[room_number].climate_entity_id = entity_id
            continue

        # For other entities, use entity_type attribute
        if not entity_type:
            continue

        # Handle auxiliary heating entities
        if entity_type.startswith(ENTITY_TYPE_AUXILIARY_HEATING):
            room_number = _extract_room_number_from_entity_type(entity_type)
            if room_number and room_number in rooms:
                rooms[room_number].auxiliary_heating_entity_id = entity_id

        # Handle global entities
        elif entity_type == ENTITY_TYPE_HEAT_PUMP_HEATING:
            result.heat_pump_heating_entity = entity_id
            _LOGGER.debug("Found heat pump heating: %s", entity_id)
        elif entity_type == ENTITY_TYPE_HEAT_PUMP_COOLING:
            result.heat_pump_cooling_entity = entity_id
            _LOGGER.debug("Found heat pump cooling: %s", entity_id)
        elif entity_type == ENTITY_TYPE_FAN_SPEED:
            result.fan_speed_entity = entity_id
            _LOGGER.debug("Found fan speed: %s", entity_id)
        elif entity_type == ENTITY_TYPE_OUTDOOR_TEMP:
            result.outdoor_temp_entity = entity_id
            _LOGGER.debug("Found outdoor temp: %s", entity_id)

    result.rooms = sorted(rooms.values(), key=lambda r: r.number)
    _LOGGER.info(
        "Discovery complete: %d rooms, outdoor_temp=%s, heat_pump=%s",
        len(result.rooms),
        result.outdoor_temp_entity is not None,
        result.heat_pump_heating_entity is not None,
    )
    return result


def _extract_room_number(entity_id: str, attrs: dict[str, Any]) -> int | None:
    """Extract room number from entity attributes or ID."""
    # Try to get from unique_id pattern like "xxx_room_1_climate"
    match = re.search(r"room[_\s]?(\d+)", entity_id.lower())
    if match:
        return int(match.group(1))
    return None


def _extract_room_number_from_entity_type(entity_type: str) -> int | None:
    """Extract room number from entity_type like 'auxiliary_heating_enabled_room_1'."""
    match = re.search(r"room[_\s]?(\d+)", entity_type.lower())
    if match:
        return int(match.group(1))
    return None


def _get_room_name(state: Any, room_number: int) -> str:
    """Get friendly name for a room."""
    if state and state.attributes.get("friendly_name"):
        name = state.attributes["friendly_name"]
        # Clean up common prefixes
        for prefix in ["WGT - ", "WRT - "]:
            if name.startswith(prefix):
                name = name[len(prefix):]
        return name

    return f"Raum {room_number}"


async def validate_discovery(discovered: DiscoveredEntities) -> list[str]:
    """Validate that required entities were discovered."""
    errors: list[str] = []

    if not discovered.rooms:
        errors.append("no_rooms_found")

    if not discovered.outdoor_temp_entity:
        errors.append("no_outdoor_temp_sensor")

    return errors
