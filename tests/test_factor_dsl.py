from pathlib import Path

import pytest

from autocrypto_lab.data import load_ohlcv_csv
from autocrypto_lab.factors import apply_factor_dsl


def test_factor_dsl_exposes_core_families():
    rows = load_ohlcv_csv(Path("tests/fixtures/ohlcv_1h.csv"))
    out = apply_factor_dsl(rows, [
        {"name": "momentum", "params": {"lookback": 1}},
        {"name": "reversal"},
        {"name": "volatility", "params": {"lookback": 2}},
        {"name": "flow"},
        {"name": "derivatives_pressure"},
    ])
    sample = out[-1]
    for key in ["momentum", "reversal", "volatility", "flow", "derivatives_pressure"]:
        assert key in sample


def test_factor_dsl_rejects_unknown_factor():
    rows = load_ohlcv_csv(Path("tests/fixtures/ohlcv_1h.csv"))
    with pytest.raises(ValueError, match="unknown factor"):
        apply_factor_dsl(rows, [{"name": "arbitrary_python"}])
