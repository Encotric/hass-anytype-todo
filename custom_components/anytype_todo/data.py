# Copyright (c) 2026 Sebastian Wilke
"""Custom types for anytype."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import AnytypeApiClient
    from .coordinator import AnytypeDataUpdateCoordinator


type AnytypeConfigEntry = ConfigEntry[AnytypeData]


@dataclass
class AnytypeData:
    """Data for the Anytype integration."""

    client: AnytypeApiClient
    space_id: str
    object_id: str
    integration: Integration
    coordinator: AnytypeDataUpdateCoordinator
