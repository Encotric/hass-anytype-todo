"""Base entity class for Anytype ToDo."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION
from .coordinator import AnytypeDataUpdateCoordinator


class AnytypeEntity(CoordinatorEntity[AnytypeDataUpdateCoordinator]):
    """Base entity for Anytype ToDo entities."""

    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: AnytypeDataUpdateCoordinator) -> None:
        """Initialize the shared entity state."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.config_entry.entry_id
