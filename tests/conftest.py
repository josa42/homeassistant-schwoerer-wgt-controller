"""Pytest fixtures for tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    from unittest.mock import MagicMock

    hass = MagicMock()
    hass.states.async_all.return_value = []
    return hass


@pytest.fixture
def mock_coordinator(mock_hass):
    """Create a mock coordinator."""
    from unittest.mock import MagicMock

    coordinator = MagicMock()
    coordinator.hass = mock_hass
    coordinator.config = {}
    return coordinator
