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


def test_rejects_unknown_factor_and_model():
    with pytest.raises(ConfigError, match="unknown factors"):
        load_config({"run_id": "bad", "factors": ["arbitrary_python"]})
    with pytest.raises(ConfigError, match="unknown model"):
        load_config({"run_id": "bad", "model": "opaque_ai_model"})


def test_public_only_config_rejects_private_reads_and_credentials():
    cfg = load_config({"run_id": "public", "public_only": True, "allow_private_read": False})
    assert cfg.public_only is True
    with pytest.raises(Exception, match="public-only"):
        load_config({"run_id": "bad", "public_only": True})
    with pytest.raises(Exception, match="private"):
        load_config({"run_id": "bad", "metadata": {"api_key": "nope"}})


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
        config_diff={"run_id": {"before": "base", "after": "r1"}},
        config_snapshot={"run_id": "r1"},
        rationale="fixture smoke",
        metrics={"net_return": 0.01},
        decision="continue",
        evidence="pytest fixture",
        raw_data_snapshot_ids=["raw1"],
        normalized_data_snapshot_ids=["norm1"],
        feature_table_id="features1",
        model_artifact_id="model1",
        signal_artifact_id="signals1",
    )
    append_ledger(path, entry)
    rows = read_ledger(path)
    assert rows[0]["hypothesis"] == "momentum survives costs"
    assert rows[0]["decision"] == "continue"
