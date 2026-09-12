# Copyright (c) 2026 Sebastian Wilke
"""DataUpdateCoordinator for Anytype ToDo."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .anytype import AnytypeMarkdownToDoPage
from .api import (
    AnytypeApiClientAuthenticationError,
    AnytypeApiClientError,
)

if TYPE_CHECKING:
    from .data import AnytypeConfigEntry


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class AnytypeDataUpdateCoordinator(DataUpdateCoordinator):
    """Manage fetching Anytype ToDo data from the API."""

    config_entry: AnytypeConfigEntry

    async def _async_update_data(self) -> Any:
        """Fetch the latest markdown page and convert it to Todo lists."""
        try:
            at_object = await self.config_entry.runtime_data.client.async_get_object(
                space_id=self.config_entry.runtime_data.space_id,
                object_id=self.config_entry.runtime_data.object_id,
            )

            if "object" in at_object and "markdown" in at_object["object"]:
                markdown = at_object["object"]["markdown"]
                page = AnytypeMarkdownToDoPage(markdown)
                return {"page": page}

            message = "Anytype API responded with invalid body."
            raise UpdateFailed(message)

        except AnytypeApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except AnytypeApiClientError as exception:
            raise UpdateFailed(exception) from exception
