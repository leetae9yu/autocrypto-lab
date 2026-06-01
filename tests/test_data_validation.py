from pathlib import Path

import pytest

from autocrypto_lab.data import DataValidationError, load_ohlcv_csv


HEADER = "timestamp,symbol,open,high,low,close,volume,funding_rate,open_interest,spot_future_basis\n"
ROW = "2024-01-10T00:00:00Z,BTC,45000,45200,44800,45100,1200,0.0001,100000,12\n"


def test_rejects_duplicate_symbol_timestamp(tmp_path: Path):
    path = tmp_path / "dupe.csv"
    path.write_text(HEADER + ROW + ROW, encoding="utf-8")

    with pytest.raises(DataValidationError, match="duplicate symbol/timestamp"):
        load_ohlcv_csv(path)


def test_rejects_missing_required_ohlcv_field(tmp_path: Path):
    path = tmp_path / "missing.csv"
    path.write_text(
        HEADER + "2024-01-10T00:00:00Z,BTC,45000,45200,44800,,1200,0.0001,100000,12\n",
        encoding="utf-8",
    )

    with pytest.raises(DataValidationError, match="missing required"):
        load_ohlcv_csv(path)
