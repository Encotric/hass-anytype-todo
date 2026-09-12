# Copyright (c) 2026 Sebastian Wilke
"""Anytype API Client."""

from __future__ import annotations

import socket
from typing import Any
from urllib.parse import parse_qs, urlsplit

import aiohttp
import async_timeout

from .const import API_VERSION


class AnytypeApiClientError(Exception):
    """Exception to indicate a general API error."""


class AnytypeApiClientCommunicationError(
    AnytypeApiClientError,
):
    """Exception to indicate a communication error."""


class AnytypeApiClientAuthenticationError(
    AnytypeApiClientError,
):
    """Exception to indicate an authentication error."""


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Verify that the response is valid."""
    if response.status in (401, 403):
        msg = "Invalid credentials"
        raise AnytypeApiClientAuthenticationError(
            msg,
        )
    response.raise_for_status()


def parse_object_url(object_url: str) -> tuple[str, str]:
    """Validate object url using the API."""
    components = urlsplit(object_url)
    object_id = str(components.path)[1:]
    space_id = str(parse_qs(components.query)["spaceId"][0])
    return space_id, object_id


class AnytypeApiClient:
    """Anytype API Client."""

    def __init__(
        self,
        api_key: str,
        host: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the Anytype API Client."""
        self._api_key = api_key
        self._host = host.rstrip("/")
        self._session = session

    async def async_get_spaces(self) -> list[dict[str, Any]]:
        """Get all spaces from the API."""
        response = await self._api_wrapper(
            method="get",
            url=f"{self._host}/v1/spaces",
        )
        return response.get("spaces", [])

    async def async_get_space(self, space_id: str) -> dict[str, Any]:
        """Get a specific space by ID."""
        return await self._api_wrapper(
            method="get",
            url=f"{self._host}/v1/spaces/{space_id}",
        )

    async def async_get_objects(
        self,
        space_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get objects from the API."""
        url = f"{self._host}/v1/spaces/{space_id}/objects"
        params = {"limit": limit}

        response = await self._api_wrapper(
            method="get",
            url=url,
            params=params,
        )
        return response.get("objects", [])

    async def async_get_object(self, space_id: str, object_id: str) -> dict[str, Any]:
        """Get a specific object by ID."""
        return await self._api_wrapper(
            method="get",
            url=f"{self._host}/v1/spaces/{space_id}/objects/{object_id}",
        )

    async def async_update_object(
        self, space_id: str, object_id: str, body: str
    ) -> dict[str, Any]:
        """Get a specific object by ID."""
        return await self._api_wrapper(
            method="patch",
            url=f"{self._host}/v1/spaces/{space_id}/objects/{object_id}",
            data={"markdown": body},
        )

    async def async_search(
        self,
        query: str,
        space_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search for objects."""
        data = {
            "query": query,
            "limit": limit,
        }

        response = await self._api_wrapper(
            method="post",
            url=f"{self._host}/v1/spaces/{space_id}/search",
            data=data,
        )
        return response.get("results", [])

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        params: dict | None = None,
    ) -> Any:
        """Get information from the API."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Anytype-Version": API_VERSION,
            "Content-Type": "application/json",
        }

        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params,
                )
                _verify_response_or_raise(response)
                return await response.json()

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise AnytypeApiClientCommunicationError(
                msg,
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise AnytypeApiClientCommunicationError(
                msg,
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            raise AnytypeApiClientError(
                msg,
            ) from exception
