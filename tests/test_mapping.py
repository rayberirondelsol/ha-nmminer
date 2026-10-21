import asyncio
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parent
spec = importlib.util.spec_from_file_location("mapping", ROOT.parent / "custom_components/nmminer/mapping.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

V1 = json.loads((ROOT / "fixtures/swarm_v1.json").read_text())
V2 = {  # example from the NMMiner firmware docs (api-reference.md)
    "identity": {"hwModel": "NMMiner", "hostName": "NMMiner-ABCD", "fwVersion": "2.1.0", "rssi": -62},
    "miner": {"hashRate": 2.45, "sAccepted": 42, "sRejected": 0, "uptimeSeconds": 5025, "uptimeEver": 86400,
              "networkDiff": "92.67T", "poolDiff": "8.00K", "lastDiff": "12.30K", "bestDiffSession": "45.20K",
              "bestDiffEver": "1.23M", "blkhits": 0, "freeHeap": 145408, "minFreeHeap": 131072},
    "stratum": {"url": "solobtc.nmminer.com:3333", "user": "wallet.worker"},
    "temps": {"vcore": 42.5, "asic": None},
    "storage": {"fsTotal": 393216, "fsUsed": 262144},
}


class FakeResp:
    def __init__(self, status, body):
        self.status, self.body = status, body
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    async def json(self, content_type=None):
        if isinstance(self.body, Exception):
            raise self.body
        return self.body


class FakeSession:
    def __init__(self, routes):
        self.routes = routes
    def get(self, url):
        return FakeResp(*self.routes.get("/" + url.split("/", 3)[3], (404, None)))


def fetch(routes):
    return asyncio.run(m.fetch(FakeSession(routes), "h"))


def test_v1_passthrough_unchanged():
    assert fetch({"/swarm": (200, V1)}) == V1


def test_v1_device_keys_covered_by_v2_mapping():
    # every key sensor.py can read from a 1.x device is also produced for the 2.x example
    out = m.v2_to_v1(V2, "10.0.0.5")["devices"][0]
    assert set(V1["devices"][0]) - set(out) == set()


def test_v2_example_mapped():
    out = m.v2_to_v1(V2, "10.0.0.5")
    d = out["devices"][0]
    assert d["hashRate"] == "2.45GH/s" and out["summary"]["totalHashRate"] == "2.45G"
    assert d["share"] == "0/42/100.0%"
    assert d["pool"] == "solobtc.nmminer.com:3333"
    assert d["rssi"] == "-62" and d["temp"] == "42.5" and d["valid"] == "0"
    assert d["uptime"] == "000d 01:23:45/001d 00:00:00"
    assert d["bestDiff"] == "45.20K /1.23M" and out["summary"]["bestDiff"] == "45.20K"
    assert d["freeHeap"] == "142.0" and d["version"] == "v2.1.0"
    assert d["ip"] == "10.0.0.5" and d["boardType"] == "NMMiner"


def test_v2_share_percent_with_rejects():
    v2 = {"miner": {"sAccepted": 95, "sRejected": 5}}
    assert m.v2_to_v1(v2, "h")["devices"][0]["share"] == "5/100/95.0%"


def test_hashrate_units():
    assert m._hashrate(0.0010273) == ("1.0273MH/s", "1.0273M")  # same string as the 1.x fixture
    assert m._hashrate(0.0005)[0] == "500kH/s" and m._hashrate(0.0000005)[0] == "500H/s"


def test_v2_empty_and_garbage_do_not_crash():
    for bad in ({}, {"miner": {}}, {"miner": None, "identity": "x"}, {"miner": {"hashRate": "fast", "sAccepted": True}}, None, []):
        out = m.v2_to_v1(bad, "h")
        assert len(out["devices"]) == 1
        assert out["devices"][0]["temp"] == "N/A"
        assert "hashRate" not in out["devices"][0]


def test_fetch_prefers_v2_and_falls_back():
    assert fetch({"/api/system/info": (200, V2)})["devices"][0]["hashRate"] == "2.45GH/s"
    # v1 miner: 404 on the 2.x endpoint, junk JSON also falls back
    assert fetch({"/swarm": (200, V1)}) == V1
    assert fetch({"/api/system/info": (200, ValueError("html")), "/swarm": (200, V1)}) == V1


def test_fetch_invalid_raises_valueerror():
    import pytest
    with pytest.raises(ValueError):
        fetch({"/swarm": (200, {"devices": []})})
    with pytest.raises(ValueError):
        fetch({})
