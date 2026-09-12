# Copyright (c) 2026 Sebastian Wilke
"""Constants for anytype."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "anytype_todo"
ATTRIBUTION = "Data provided by Anytype API"

# Configuration constants
CONF_API_KEY = "api_key"
CONF_HOST = "host"
CONF_OBJECT_URL = "object_url"
DEFAULT_HOST = "http://localhost:31009"
API_VERSION = "2025-11-08"
