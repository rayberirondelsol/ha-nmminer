"""Sensor platform for NMMiner integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, SIGNAL_STRENGTH_DECIBELS_MILLIWATT, UnitOfInformation, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NMMinerCoordinator


def _get_device(data: dict) -> dict:
    """Get first device from data."""
    return data.get("devices", [{}])[0]


def _parse_hash_rate(data: dict) -> str | None:
    """Extract hash rate string from device."""
    return _get_device(data).get("hashRate")


def _parse_total_hash_rate(data: dict) -> str | None:
    """Extract total hash rate from summary."""
    return data.get("summary", {}).get("totalHashRate")


def _parse_total_workers(data: dict) -> int | None:
    """Extract total workers from summary."""
    val = data.get("summary", {}).get("totalWorkers")
    if val is not None:
        return int(val)
    return None


def _parse_best_diff_summary(data: dict) -> str | None:
    """Extract best difficulty from summary."""
    return data.get("summary", {}).get("bestDiff")


def _parse_shares(data: dict) -> str | None:
    """Extract share string."""
    return _get_device(data).get("share")


def _share_counts(data: dict) -> tuple[int, int] | None:
    """Return (rejected, total) from the "rejected/total/acceptance%" share string."""
    try:
        rejected, total = _get_device(data).get("share", "").split("/")[:2]
        return int(rejected), int(total)
    except ValueError:
        return None


def _parse_share_accepted(data: dict) -> int | None:
    """Accepted shares = total - rejected."""
    counts = _share_counts(data)
    return counts[1] - counts[0] if counts else None


def _parse_share_total(data: dict) -> int | None:
    """Total shares submitted."""
    counts = _share_counts(data)
    return counts[1] if counts else None


def _parse_share_acceptance(data: dict) -> float | None:
    """Extract acceptance percentage from share string."""
    share = _get_device(data).get("share", "")
    parts = share.split("/")
    if len(parts) >= 3:
        try:
            return float(parts[2].replace("%", ""))
        except (ValueError, IndexError):
            pass
    return None


def _parse_pool(data: dict) -> str | None:
    """Extract pool address."""
    return _get_device(data).get("pool")


def _parse_net_diff(data: dict) -> str | None:
    """Extract network difficulty."""
    return _get_device(data).get("netDiff")


def _parse_pool_diff(data: dict) -> str | None:
    """Extract pool difficulty."""
    val = _get_device(data).get("poolDiff", "")
    return val.strip() if val else None


def _parse_last_diff(data: dict) -> str | None:
    """Extract last difficulty."""
    return _get_device(data).get("lastDiff")


def _parse_best_diff_session(data: dict) -> str | None:
    """Extract session best difficulty."""
    best = _get_device(data).get("bestDiff", "")
    parts = best.split("/")
    if parts:
        return parts[0].strip()
    return None


def _parse_best_diff_alltime(data: dict) -> str | None:
    """Extract all-time best difficulty."""
    best = _get_device(data).get("bestDiff", "")
    parts = best.split("/")
    if len(parts) >= 2:
        return parts[1].strip()
    return None


def _parse_valid(data: dict) -> int | None:
    """Extract valid/hits count."""
    val = _get_device(data).get("valid")
    if val is not None:
        try:
            return int(val)
        except ValueError:
            pass
    return None


def _parse_temp(data: dict) -> float | None:
    """Extract temperature."""
    val = _get_device(data).get("temp", "")
    if val and val != "N/A":
        try:
            return float(val)
        except ValueError:
            pass
    return None


def _parse_rssi(data: dict) -> int | None:
    """Extract RSSI."""
    val = _get_device(data).get("rssi")
    if val is not None:
        try:
            return int(val)
        except ValueError:
            pass
    return None


def _parse_free_heap(data: dict) -> float | None:
    """Extract free heap memory in KB."""
    val = _get_device(data).get("freeHeap")
    if val is not None:
        try:
            return float(val)
        except ValueError:
            pass
    return None


def _parse_uptime_session(data: dict) -> str | None:
    """Extract session uptime."""
    uptime = _get_device(data).get("uptime", "")
    parts = uptime.split("/")
    if parts:
        return parts[0].strip()
    return None


def _parse_uptime_total(data: dict) -> str | None:
    """Extract total uptime."""
    uptime = _get_device(data).get("uptime", "")
    parts = uptime.split("/")
    if len(parts) >= 2:
        return parts[1].strip()
    return None


def _parse_version(data: dict) -> str | None:
    """Extract firmware version."""
    return _get_device(data).get("version")


def _parse_board(data: dict) -> str | None:
    """Extract board type."""
    return _get_device(data).get("boardType")


def _parse_ip(data: dict) -> str | None:
    """Extract device IP."""
    return _get_device(data).get("ip")


def _parse_last_seen(data: dict) -> str | None:
    """Extract last seen status."""
    return _get_device(data).get("lastseen")


@dataclass(frozen=True, kw_only=True)
class NMMinerSensorEntityDescription(SensorEntityDescription):
    """Describe an NMMiner sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSOR_DESCRIPTIONS: tuple[NMMinerSensorEntityDescription, ...] = (
    NMMinerSensorEntityDescription(
        key="hash_rate",
        translation_key="hash_rate",
        name="HashRate",
        icon="mdi:lightning-bolt",
        value_fn=_parse_hash_rate,
    ),
    NMMinerSensorEntityDescription(
        key="total_hash_rate",
        translation_key="total_hash_rate",
        name="Total HashRate",
        icon="mdi:lightning-bolt-outline",
        value_fn=_parse_total_hash_rate,
    ),
    NMMinerSensorEntityDescription(
        key="active_workers",
        translation_key="active_workers",
        name="Active Workers",
        icon="mdi:account-hard-hat",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_total_workers,
    ),
    NMMinerSensorEntityDescription(
        key="best_difficulty",
        translation_key="best_difficulty",
        name="Best Difficulty",
        icon="mdi:trophy",
        value_fn=_parse_best_diff_summary,
    ),
    NMMinerSensorEntityDescription(
        key="shares",
        translation_key="shares",
        name="Shares",
        icon="mdi:share-variant",
        value_fn=_parse_shares,
    ),
    NMMinerSensorEntityDescription(
        key="shares_accepted",
        translation_key="shares_accepted",
        name="Shares Accepted",
        icon="mdi:check-circle",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_parse_share_accepted,
    ),
    NMMinerSensorEntityDescription(
        key="shares_total",
        translation_key="shares_total",
        name="Shares Total",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_parse_share_total,
    ),
    NMMinerSensorEntityDescription(
        key="share_acceptance",
        translation_key="share_acceptance",
        name="Share Acceptance",
        icon="mdi:check-decagram",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_share_acceptance,
    ),
    NMMinerSensorEntityDescription(
        key="pool",
        translation_key="pool",
        name="Pool",
        icon="mdi:server-network",
        value_fn=_parse_pool,
    ),
    NMMinerSensorEntityDescription(
        key="net_difficulty",
        translation_key="net_difficulty",
        name="Net Difficulty",
        icon="mdi:target",
        value_fn=_parse_net_diff,
    ),
    NMMinerSensorEntityDescription(
        key="pool_difficulty",
        translation_key="pool_difficulty",
        name="Pool Difficulty",
        icon="mdi:target-variant",
        value_fn=_parse_pool_diff,
    ),
    NMMinerSensorEntityDescription(
        key="last_difficulty",
        translation_key="last_difficulty",
        name="Last Difficulty",
        icon="mdi:target-account",
        value_fn=_parse_last_diff,
    ),
    NMMinerSensorEntityDescription(
        key="best_diff_session",
        translation_key="best_diff_session",
        name="Best Diff Session",
        icon="mdi:trophy-outline",
        value_fn=_parse_best_diff_session,
    ),
    NMMinerSensorEntityDescription(
        key="best_diff_alltime",
        translation_key="best_diff_alltime",
        name="Best Diff All-Time",
        icon="mdi:trophy",
        value_fn=_parse_best_diff_alltime,
    ),
    NMMinerSensorEntityDescription(
        key="hits",
        translation_key="hits",
        name="Hits",
        icon="mdi:star-circle",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_parse_valid,
    ),
    NMMinerSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        name="Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_temp,
    ),
    NMMinerSensorEntityDescription(
        key="rssi",
        translation_key="rssi",
        name="WiFi Signal",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_rssi,
    ),
    NMMinerSensorEntityDescription(
        key="free_memory",
        translation_key="free_memory",
        name="Free Memory",
        icon="mdi:memory",
        native_unit_of_measurement="KB",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_parse_free_heap,
    ),
    NMMinerSensorEntityDescription(
        key="uptime_session",
        translation_key="uptime_session",
        name="Uptime Session",
        icon="mdi:clock-outline",
        value_fn=_parse_uptime_session,
    ),
    NMMinerSensorEntityDescription(
        key="uptime_total",
        translation_key="uptime_total",
        name="Uptime Total",
        icon="mdi:clock-check-outline",
        value_fn=_parse_uptime_total,
    ),
    NMMinerSensorEntityDescription(
        key="version",
        translation_key="version",
        name="Firmware",
        icon="mdi:information-outline",
        value_fn=_parse_version,
    ),
    NMMinerSensorEntityDescription(
        key="board",
        translation_key="board",
        name="Board",
        icon="mdi:circuit-board",
        value_fn=_parse_board,
    ),
    NMMinerSensorEntityDescription(
        key="ip",
        translation_key="ip",
        name="IP Address",
        icon="mdi:ip-network",
        value_fn=_parse_ip,
    ),
    NMMinerSensorEntityDescription(
        key="last_seen",
        translation_key="last_seen",
        name="Last Seen",
        icon="mdi:eye-check",
        value_fn=_parse_last_seen,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NMMiner sensors from a config entry."""
    coordinator: NMMinerCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create sensors for each device
    entities: list[NMMinerSensor] = []
    data = coordinator.data
    devices = data.get("devices", [])

    for device_index in range(len(devices)):
        for description in SENSOR_DESCRIPTIONS:
            entities.append(
                NMMinerSensor(
                    coordinator=coordinator,
                    description=description,
                    entry=entry,
                    device_index=device_index,
                )
            )

    async_add_entities(entities)


class NMMinerSensor(CoordinatorEntity[NMMinerCoordinator], SensorEntity):
    """Representation of an NMMiner sensor."""

    entity_description: NMMinerSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NMMinerCoordinator,
        description: NMMinerSensorEntityDescription,
        entry: ConfigEntry,
        device_index: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device_index = device_index
        self._attr_unique_id = f"{entry.entry_id}_{device_index}_{description.key}"

        # Device info groups all sensors under one device
        device = coordinator.data.get("devices", [{}])[device_index]
        board = device.get("boardType", "NMMiner")
        ip = device.get("ip", coordinator.host)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}_{device_index}")},
            "name": f"NMMiner {board}",
            "manufacturer": "NMMiner",
            "model": board,
            "sw_version": device.get("version"),
            "configuration_url": f"http://{ip}/static",
        }

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes for the hashrate sensor (used by Garmin widget)."""
        if self.entity_description.key != "hash_rate":
            return None
        if self.coordinator.data is None:
            return None
        data = self.coordinator.data
        return {
            "best_diff": _parse_best_diff_summary(data),
            "best_diff_session": _parse_best_diff_session(data),
            "best_diff_alltime": _parse_best_diff_alltime(data),
            "shares_accepted": _parse_share_accepted(data),
            "shares_total": _parse_share_rejected(data),
            "share_acceptance": _parse_share_acceptance(data),
            "hits": _parse_valid(data),
            "rssi": _parse_rssi(data),
            "temperature": _parse_temp(data),
            "uptime_session": _parse_uptime_session(data),
            "active_workers": _parse_total_workers(data),
            "total_hash_rate": _parse_total_hash_rate(data),
        }
