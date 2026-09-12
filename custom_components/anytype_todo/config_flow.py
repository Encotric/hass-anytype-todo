# Copyright (c) 2026 Sebastian Wilke
"""Adds the config flow for Anytype ToDo."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import (
    AnytypeApiClient,
    AnytypeApiClientAuthenticationError,
    AnytypeApiClientCommunicationError,
    AnytypeApiClientError,
    parse_object_url,
)
from .const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_OBJECT_URL,
    DEFAULT_HOST,
    DOMAIN,
    LOGGER,
)


class AnytypeFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Anytype ToDo."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a user-initialized config flow."""
        _errors = {}
        if user_input is not None:
            try:
                await self._test_credentials(
                    api_key=user_input[CONF_API_KEY],
                    host=user_input.get(CONF_HOST, DEFAULT_HOST),
                    object_url=user_input[CONF_OBJECT_URL],
                )
            except AnytypeApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except AnytypeApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except AnytypeApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                # Use a hash of the API key as unique_id
                unique_id = user_input[CONF_API_KEY][:16]
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Anytype ToDo", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_API_KEY,
                        default=(user_input or {}).get(CONF_API_KEY, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                    vol.Optional(
                        CONF_HOST,
                        default=(user_input or {}).get(CONF_HOST, DEFAULT_HOST),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.URL,
                        ),
                    ),
                    vol.Required(
                        CONF_OBJECT_URL,
                        default=(user_input or {}).get(CONF_OBJECT_URL, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.URL,
                        ),
                    ),
                },
            ),
            errors=_errors,
        )

    async def _test_credentials(self, api_key: str, host: str, object_url: str) -> None:
        """Validate Anytype ToDo credentials."""
        client = AnytypeApiClient(
            api_key=api_key,
            host=host,
            session=async_create_clientsession(self.hass),
        )
        space_id, object_id = parse_object_url(object_url=object_url)
        at_object = await client.async_get_object(
            space_id=space_id, object_id=object_id
        )

        if (
            not ("object" in at_object and "id" in at_object["object"])
            or at_object["object"]["id"] != object_id
        ):
            msg = "Invalid object url"
            raise AnytypeApiClientError(msg)
