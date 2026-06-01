from pathlib import Path

import pytest

from autocrypto_lab.config import ConfigError, load_config
from autocrypto_lab.ledger import LedgerEntry, append_ledger, read_ledger
from autocrypto_lab.manifest import stable_hash
from autocrypto_lab.registry import Registry, RegistryError


def test_load_valid_config():
    cfg = load_config({"run_id": "smoke", "symbols": ["BTC", "ETH"], "interval": "1h"})
    assert cfg.run_id == "smoke"
    assert cfg.cadence_minutes == 60


def test_rejects_sub_hour_config():
    with pytest.raises(ConfigError, match=">= 1h"):
        load_config({"run_id": "bad", "interval": "15m"})


def test_rejects_unknown_symbol():
    with pytest.raises(ConfigError, match="unknown symbols"):
        load_config({"run_id": "bad", "symbols": ["DOGE"]})


def test_registry_rejects_duplicate_and_unknown():
    reg = Registry("demo")
    reg.register("x", object())
    with pytest.raises(RegistryError):
        reg.register("x", object())
    with pytest.raises(RegistryError):
        reg.get("missing")


def test_ledger_roundtrip(tmp_path: Path):
    path = tmp_path / "ledger.jsonl"
    entry = LedgerEntry(
        run_id="r1",
        hypothesis="momentum survives costs",
        config_hash=stable_hash({"run_id": "r1"}),
        rationale="fixture smoke",
        metrics={"net_return": 0.01},
        decision="continue",
        evidence="pytest fixture",
    )
    append_ledger(path, entry)
    rows = read_ledger(path)
    assert rows[0]["hypothesis"] == "momentum survives costs"
    assert rows[0]["decision"] == "continue"
