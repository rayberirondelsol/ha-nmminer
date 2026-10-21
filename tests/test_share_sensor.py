"""Share sensors: the device string is "rejected/total/acceptance%"."""

import ast
from pathlib import Path

SRC = Path(__file__).parents[1] / "custom_components/nmminer/sensor.py"
WANTED = {"_get_device", "_share_counts", "_parse_share_accepted", "_parse_share_total"}


def _load():
    # sensor.py imports homeassistant; load only the pure parser functions.
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in WANTED]
    ns: dict = {}
    exec(compile(ast.Module(funcs, []), str(SRC), "exec"), ns)
    return ns


def _data(share):
    return {"devices": [{"share": share}]}


def test_real_device_string():
    ns = _load()
    d = _data("62/5367/98.9%")  # from a v1.8.28 device: 98.9 % == (5367-62)/5367
    assert ns["_parse_share_total"](d) == 5367
    assert ns["_parse_share_accepted"](d) == 5305


def test_no_rejects():
    ns = _load()
    d = _data("0/31/100.0%")
    assert ns["_parse_share_accepted"](d) == 31
    assert ns["_parse_share_total"](d) == 31


def test_missing_or_bad_share_gives_none():
    ns = _load()
    for bad in ({"devices": [{}]}, _data(""), _data("N/A"), _data("x/y/z")):
        assert ns["_parse_share_accepted"](bad) is None
        assert ns["_parse_share_total"](bad) is None
