"""DataUpdateCoordinator for NMMiner."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, SWARM_ENDPOINT

_LOGGER = logging.getLogger(__name__)


class NMMinerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch data from NMMiner device."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        """Initialize the coordinator."""
        self.host = host
        self._url = f"http://{host}{SWARM_ENDPOINT}"
        super().__init__(
            hass,
            _LOGGER,
            name=f"NMMiner ({host})",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the NMMiner /swarm endpoint."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self._url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"HTTP {resp.status} from {self._url}")
                    data = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with NMMiner at {self.host}: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

        if "devices" not in data or not data["devices"]:
            raise UpdateFailed("No devices found in NMMiner response")

        return data
