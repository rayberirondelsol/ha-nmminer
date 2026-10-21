"""Fetch NMMiner data and normalise it to the firmware 1.x /swarm shape.

No Home Assistant imports, so it can be unit-tested standalone.
"""

from __future__ import annotations

from typing import Any

SWARM_ENDPOINT = "/swarm"  # firmware 1.x
SYSTEM_INFO_ENDPOINT = "/api/system/info"  # firmware 2.x


def _hashrate(ghs: float) -> tuple[str, str]:
    """GH/s -> ("2.45GH/s", "2.45G") like the 1.x strings ("1.0273MH/s", "1.0273M")."""
    hs = ghs * 1e9
    for factor, prefix in ((1e9, "G"), (1e6, "M"), (1e3, "k")):
        if hs >= factor:
            n = f"{hs / factor:.5g}"
            return f"{n}{prefix}H/s", f"{n}{prefix}"
    return f"{hs:.5g}H/s", f"{hs:.5g}"


def _clock(sec: int) -> str:
    """Seconds -> "000d 13:50:01"."""
    d, rem = divmod(int(sec), 86400)
    return f"{d:03d}d {rem // 3600:02d}:{rem % 3600 // 60:02d}:{rem % 60:02d}"


def _num(val: Any) -> float | None:
    """Number or None (bool/str/None are rejected, never raises)."""
    return float(val) if isinstance(val, (int, float)) and not isinstance(val, bool) else None


def v2_to_v1(info: dict[str, Any], host: str) -> dict[str, Any]:
    """Translate a firmware 2.x /api/system/info payload to the 1.x /swarm shape.

    Anything missing or malformed becomes None / "N/A" instead of raising.
    Share string keeps the 1.x layout "<first>/<total>/<pct>%" where, in the
    1.x sample (63/5464/98.9%), <first> is the rejected count.
    """
    def sect(name: str) -> dict[str, Any]:
        val = info.get(name) if isinstance(info, dict) else None
        return val if isinstance(val, dict) else {}

    ident, miner, stratum, temps = sect("identity"), sect("miner"), sect("stratum"), sect("temps")
    dev: dict[str, Any] = {"ip": host, "lastseen": "Just now"}
    summary: dict[str, Any] = {"totalWorkers": 1}

    dev["boardType"] = ident.get("hwModel")
    ver = ident.get("fwVersion")
    dev["version"] = f"v{ver}" if isinstance(ver, str) and ver[:1].isdigit() else ver
    rssi = _num(ident.get("rssi"))
    dev["rssi"] = None if rssi is None else str(int(rssi))

    ghs = _num(miner.get("hashRate"))
    if ghs is not None:
        dev["hashRate"], summary["totalHashRate"] = _hashrate(ghs)

    acc, rej = _num(miner.get("sAccepted")), _num(miner.get("sRejected"))
    if acc is not None and rej is not None:
        total = int(acc + rej)
        pct = f"{acc / total * 100:.1f}" if total else "100.0"
        dev["share"] = f"{int(rej)}/{total}/{pct}%"

    up, ever = _num(miner.get("uptimeSeconds")), _num(miner.get("uptimeEver"))
    if up is not None:
        dev["uptime"] = _clock(up) + ("" if ever is None else f"/{_clock(ever)}")

    dev["netDiff"] = miner.get("networkDiff")
    dev["poolDiff"] = miner.get("poolDiff")
    dev["lastDiff"] = miner.get("lastDiff")
    sess, alltime = miner.get("bestDiffSession"), miner.get("bestDiffEver")
    if sess is not None and alltime is not None:
        dev["bestDiff"] = f"{sess} /{alltime}"
    summary["bestDiff"] = sess
    hits = _num(miner.get("blkhits"))
    dev["valid"] = None if hits is None else str(int(hits))
    heap = _num(miner.get("freeHeap"))
    dev["freeHeap"] = None if heap is None else f"{heap / 1024:.1f}"

    dev["pool"] = stratum.get("url")
    temp = _num(temps.get("vcore"))
    if temp is None:
        temp = _num(temps.get("asic"))
    dev["temp"] = "N/A" if temp is None else str(temp)

    dev = {k: v for k, v in dev.items() if v is not None}
    return {"summary": summary, "devices": [dev]}


async def fetch(session: Any, host: str) -> dict[str, Any]:
    """Return 1.x-shaped data from a 2.x or 1.x miner.

    2.x first: 1.x answers /api/system/info with a clean 404, while a 2.x
    miner may no longer serve /swarm at all. Errors from the /swarm attempt
    propagate (ConnectionError etc.); invalid payloads raise ValueError.
    """
    # ponytail: one extra failed request per poll on 1.x; cache the working endpoint if that ever matters.
    try:
        async with session.get(f"http://{host}{SYSTEM_INFO_ENDPOINT}") as resp:
            if resp.status == 200:
                info = await resp.json(content_type=None)
                if isinstance(info, dict) and isinstance(info.get("miner"), dict):
                    return v2_to_v1(info, host)
    except Exception:  # noqa: BLE001 - any failure means "try 1.x"
        pass
    async with session.get(f"http://{host}{SWARM_ENDPOINT}") as resp:
        if resp.status != 200:
            raise ValueError(f"HTTP {resp.status} from {host}")
        data = await resp.json(content_type=None)
    if not isinstance(data, dict) or not data.get("devices"):
        raise ValueError("No devices found in NMMiner response")
    return data
