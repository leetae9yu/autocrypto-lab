from pathlib import Path

from autocrypto_lab.data import load_ohlcv_csv
from autocrypto_lab.factors import add_forward_returns, add_momentum
from autocrypto_lab.backtest import quantile_returns, research_diagnostics, run_long_short


def fixture_rows():
    return add_forward_returns(add_momentum(load_ohlcv_csv(Path("tests/fixtures/ohlcv_1h.csv"))))


def test_quantile_returns_are_generated():
    qs = quantile_returns(fixture_rows(), "momentum", buckets=3)
    assert qs
    assert set(qs).issubset({"q1", "q2", "q3"})


def test_research_diagnostics_include_cost_and_robustness_fields():
    diag = research_diagnostics(fixture_rows(), "momentum", funding_cost=0.0001)
    for key in ["ic", "quantile_returns", "net_return_after_funding", "max_drawdown", "turnover", "robustness_flags"]:
        assert key in diag
    assert isinstance(diag["robustness_flags"]["cost_survives"], bool)


def test_long_short_rebalances_by_timestamp_and_excludes_terminal_labels():
    metrics = run_long_short(fixture_rows(), "momentum")
    assert metrics["periods"] == 3
    assert metrics["turnover"] == 6.0
    assert len(metrics["long_symbol"].split(",")) == 3
    assert len(metrics["short_symbol"].split(",")) == 3
