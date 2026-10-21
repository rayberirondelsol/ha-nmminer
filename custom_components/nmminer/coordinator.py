"""DataUpdateCoordinator for NMMiner."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL
from .mapping import fetch

_LOGGER = logging.getLogger(__name__)


class NMMinerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch data from NMMiner device."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        """Initialize the coordinator."""
        self.host = host
        super().__init__(
            hass,
            _LOGGER,
            name=f"NMMiner ({host})",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data (firmware 2.x /api/system/info or 1.x /swarm), 1.x-shaped."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                return await fetch(session, self.host)
        except (aiohttp.ClientError, ValueError) as err:
            raise UpdateFailed(f"Error communicating with NMMiner at {self.host}: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err
