from pathlib import Path

import pytest

from autocrypto_lab.config import CPU_FRIENDLY_MODELS, ConfigError, load_config
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


def test_accepts_cpu_friendly_model_registry_with_params():
    cfg = load_config(
        {
            "run_id": "cpu",
            "model": "walk_forward_random_forest",
            "model_params": {"n_estimators": 25, "max_depth": 3, "min_samples_leaf": 2, "random_state": 42},
        }
    )
    assert cfg.model in CPU_FRIENDLY_MODELS
    assert cfg.model_spec() == {
        "name": "walk_forward_random_forest",
        "params": {"n_estimators": 25, "max_depth": 3, "min_samples_leaf": 2, "random_state": 42},
    }


@pytest.mark.parametrize("model", ["lstm_alpha", "transformer_ranker", "gpu_boosted", "cuda_tree"])
def test_rejects_gpu_or_deep_learning_model_names(model: str):
    with pytest.raises(ConfigError, match="GPU/deep-learning"):
        load_config({"run_id": "bad", "model": model})


def test_rejects_private_or_non_mapping_model_params():
    with pytest.raises(Exception, match="private"):
        load_config({"run_id": "bad", "model_params": {"api_key": "nope"}})
    with pytest.raises(ConfigError, match="model_params must be a mapping"):
        load_config({"run_id": "bad", "model_params": ["not", "a", "mapping"]})


def test_public_only_config_rejects_private_reads_and_credentials():
    cfg = load_config({"run_id": "public", "public_only": True, "allow_private_read": False})
    assert cfg.public_only is True
    with pytest.raises(Exception, match="public-only"):
        load_config({"run_id": "bad", "public_only": True})
    with pytest.raises(Exception, match="private"):
        load_config({"run_id": "bad", "metadata": {"api_key": "nope"}})
    with pytest.raises(Exception, match="private"):
        load_config({"run_id": "bad", "public_only": True, "allow_private_read": False, "api_key": "nope"})
    with pytest.raises(ConfigError, match="unknown config keys"):
        load_config({"run_id": "bad", "public_only": True, "allow_private_read": False, "surprise": "nope"})


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


def test_ledger_requires_artifact_provenance(tmp_path: Path):
    path = tmp_path / "ledger.jsonl"
    entry = LedgerEntry(
        run_id="r1",
        hypothesis="missing provenance should fail",
        config_hash=stable_hash({"run_id": "r1"}),
        config_diff={"run_id": {"before": "base", "after": "r1"}},
        config_snapshot={"run_id": "r1"},
        rationale="fixture smoke",
        metrics={"net_return": 0.01},
        decision="continue",
        evidence="pytest fixture",
    )
    with pytest.raises(ValueError, match="raw_data_snapshot_ids"):
        append_ledger(path, entry)
