from pathlib import Path

from autocrypto_lab.data import load_ohlcv_csv
from autocrypto_lab.factors import add_forward_returns, add_momentum
from autocrypto_lab.regime import regime_metrics, write_regime_report


def rows():
    return add_forward_returns(add_momentum(load_ohlcv_csv(Path("tests/fixtures/ohlcv_1h.csv"))))


def test_regime_metrics_cover_multiple_windows():
    metrics = regime_metrics(rows())
    assert len(metrics) >= 3
    assert all("window" in item and "metrics" in item for item in metrics)


def test_regime_report_contains_sources_metrics_and_limitations(tmp_path: Path):
    path = tmp_path / "regime.md"
    write_regime_report(path, rows())
    text = path.read_text()
    assert "ETF Regime Diagnostics" in text
    assert "sec.gov" in text
    assert "Quantile returns" in text
    assert "not investment advice" in text.lower()
    assert "samples are short" in text
