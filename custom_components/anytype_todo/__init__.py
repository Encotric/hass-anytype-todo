# Copyright (c) 2026 Sebastian Wilke
"""Anytype Todo integration."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import AnytypeApiClient, parse_object_url
from .const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_OBJECT_URL,
    DEFAULT_HOST,
    DOMAIN,
    LOGGER,
)
from .coordinator import AnytypeDataUpdateCoordinator
from .data import AnytypeData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import AnytypeConfigEntry

PLATFORMS: list[Platform] = [
    Platform.TODO,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: AnytypeConfigEntry,
) -> bool:
    """Set up Anytype ToDo using the UI."""
    coordinator = AnytypeDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=timedelta(seconds=1),
    )
    space_id, object_id = parse_object_url(entry.data[CONF_OBJECT_URL])
    entry.runtime_data = AnytypeData(
        client=AnytypeApiClient(
            api_key=entry.data[CONF_API_KEY],
            host=entry.data.get(CONF_HOST, DEFAULT_HOST),
            session=async_get_clientsession(hass),
        ),
        space_id=space_id,
        object_id=object_id,
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: AnytypeConfigEntry,
) -> bool:
    """Handle removal of an Anytype ToDo entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: AnytypeConfigEntry,
) -> None:
    """Reload an Anytype ToDo config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
