"""Config flow for NMMiner integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST

from .const import DOMAIN, SWARM_ENDPOINT

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
    }
)


class NMMinerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NMMiner."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip().rstrip("/")
            # Remove http:// prefix if user entered full URL
            if host.startswith("http://"):
                host = host[7:]
            if host.startswith("https://"):
                host = host[8:]
            # Remove /static or /swarm suffix if user entered full path
            for suffix in ("/static", "/swarm", "/"):
                if host.endswith(suffix):
                    host = host[: -len(suffix)]

            # Set unique ID to prevent duplicate entries
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            # Test connection
            url = f"http://{host}{SWARM_ENDPOINT}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status != 200:
                            errors["base"] = "cannot_connect"
                        else:
                            data = await resp.json(content_type=None)
                            if "devices" not in data:
                                errors["base"] = "invalid_response"
                            else:
                                # Determine a nice title
                                device = data["devices"][0]
                                board = device.get("boardType", "NMMiner")
                                title = f"NMMiner ({board})"
                                return self.async_create_entry(
                                    title=title,
                                    data={CONF_HOST: host},
                                )
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
