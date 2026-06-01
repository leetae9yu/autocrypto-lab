from pathlib import Path

import pytest

from autocrypto_lab.data import load_ohlcv_csv
from autocrypto_lab.factors import add_forward_returns, add_momentum
from autocrypto_lab.backtest import quantile_returns, research_diagnostics, run_long_short, run_signal_backtest
from autocrypto_lab.models import fit_weighted_score_model, score_model


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


def test_signal_backtest_requires_model_signal_scores():
    rows = fixture_rows()
    model = fit_weighted_score_model(rows, features=["momentum"], model_id="backtest_model")
    scored = score_model(rows, model)
    metrics = run_signal_backtest(scored, funding_cost=0.0001)

    assert metrics["model_id"] == "backtest_model"
    assert metrics["score_field"] == "signal_score"
    assert "ic" in metrics
    assert "quantile_returns" in metrics
    assert "stability" in metrics
    assert metrics["robustness_flags"]["model_signal_source"] is True


def test_signal_backtest_rejects_factor_shortcut_rows():
    try:
        run_signal_backtest(fixture_rows())
    except ValueError as exc:
        assert "signal_score" in str(exc)
    else:
        raise AssertionError("signal backtest accepted rows without model signal output")


def test_signal_backtest_rejects_partial_or_inconsistent_model_rows():
    rows = fixture_rows()
    model = fit_weighted_score_model(rows, features=["momentum"], model_id="backtest_model")
    scored = score_model(rows, model)
    missing_signal = [dict(row) for row in scored]
    missing_signal[0].pop("signal_score")
    with pytest.raises(ValueError, match="every row"):
        run_signal_backtest(missing_signal)

    inconsistent = [dict(row) for row in scored]
    inconsistent[0]["model_id"] = "other_model"
    with pytest.raises(ValueError, match="consistent"):
        run_signal_backtest(inconsistent)

    missing_terminal_model_id = [dict(row) for row in scored]
    missing_terminal_model_id[-1]["model_id"] = ""
    with pytest.raises(ValueError, match="consistent"):
        run_signal_backtest(missing_terminal_model_id)


def test_signal_backtest_can_reduce_turnover_with_rebalance_periods():
    rows = fixture_rows()
    model = fit_weighted_score_model(rows, features=["momentum"], model_id="rebalance_model")
    scored = score_model(rows, model)

    every_period = run_signal_backtest(scored)
    sparse = run_signal_backtest(scored, rebalance_periods=2)

    assert sparse["rebalance_periods"] == 2
    assert sparse["periods"] < every_period["periods"]
    assert sparse["turnover"] < every_period["turnover"]
    assert sparse["cost"] < every_period["cost"]


def test_signal_backtest_can_skip_weak_score_spreads():
    rows = fixture_rows()
    model = fit_weighted_score_model(rows, features=["momentum"], model_id="spread_model")
    scored = score_model(rows, model)

    metrics = run_signal_backtest(scored, min_score_spread=999.0)

    assert metrics["periods"] == 0
    assert metrics["skipped_spread_periods"] > 0

