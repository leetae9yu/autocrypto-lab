# autocrypto-lab

`autocrypto-lab` is a local-first crypto quant research engineering harness. It is designed to show a reproducible Research Engineer / Quant Dev workflow rather than claim a production trading edge.

## V1 boundaries

- **No live order endpoints**: v1 exposes read-only account boundaries only and forbids order creation/cancel/position-changing paths.
- **Public/free data first**: data adapters start from public/free sources and deterministic fixtures.
- **Minimum cadence: 1h**: sub-hour scalping is out of scope.
- **Config-only autonomy**: autonomous research iterations mutate experiment configs and ledger decisions, not runtime code.
- **Research diagnostics only**: reports and dashboards are not investment advice or profit guarantees.

## Canonical research scope

- Assets: BTC, ETH, SOL, XRP.
- Factor families: momentum, reversal, volatility, flow/supply-demand, derivatives pressure.
- Core experiment: source-backed U.S. spot BTC ETF multi-window regime diagnostics.
- Evaluation: point-in-time validation, cost-aware long/short diagnostics, IC, quantiles, turnover, drawdown, and limitations.

## Quickstart

```bash
python3 -m pytest -q
PYTHONPATH=src python3 -m autocrypto_lab.cli run-sample --output-dir /tmp/autocrypto-smoke --run-id smoke
```

Expected smoke artifacts:

- `/tmp/autocrypto-smoke/report.md`
- `/tmp/autocrypto-smoke/regime_report.md`
- `/tmp/autocrypto-smoke/dashboard.html`
- `/tmp/autocrypto-smoke/manifest.json`

The next-phase public-futures fixture replay exercises the API-key-free model path:

```bash
PYTHONPATH=src python3 -m autocrypto_lab.cli run-public-fixture --output-dir /tmp/autocrypto-public-smoke --run-id public_smoke
```

Expected public fixture artifacts:

- `/tmp/autocrypto-public-smoke/report.md`
- `/tmp/autocrypto-public-smoke/regime_report.md`
- `/tmp/autocrypto-public-smoke/dashboard.html`
- `/tmp/autocrypto-public-smoke/manifest.json`
- `/tmp/autocrypto-public-smoke/models/public_smoke_weighted_score.model.json`
- `/tmp/autocrypto-public-smoke/models/public_smoke_weighted_score_signals.json`

The sample path uses deterministic fixtures under `tests/fixtures/` so CI does not need network access or credentials.

To run the same model/backtest path on **real API-key-free Binance USDⓈ-M public futures data**:

```bash
PYTHONPATH=src python3 -m autocrypto_lab.cli run-public-binance \
  --output-dir /tmp/autocrypto-real-binance-smoke \
  --run-id real_binance_smoke \
  --symbols BTC,ETH \
  --interval 1h \
  --lookback-hours 72 \
  --train-periods 24 \
  --test-periods 6
```

This command downloads public klines, funding rates, open-interest statistics, and basis data, persists raw/normalized artifacts, builds a PIT feature table, fits rolling walk-forward weighted-score factor models, persists out-of-sample `model_id`/`signal_score` artifacts, and runs the cost-aware signal backtest. It does **not** use API keys and does **not** place or modify trades.

### CPU-friendly autonomous research loop

The autonomous loop is still **research-only** and **config-only**: it generates bounded candidate configs, runs each candidate through the same public Binance walk-forward pipeline, ranks the diagnostics, and writes an auditable ledger. It does not edit runtime code, use API keys, or place sandbox/live orders.

```bash
PYTHONPATH=src python3 -m autocrypto_lab.cli run-agent-loop \
  --output-dir /tmp/autocrypto-agent-loop-smoke \
  --run-id agent_loop_smoke \
  --symbols BTC,ETH \
  --interval 1h \
  --lookback-hours 72 \
  --train-periods 24 \
  --test-periods 6 \
  --max-candidates 3 \
  --iterations 3
```

Expected autonomous artifacts:

- `/tmp/autocrypto-agent-loop-smoke/agent_loop_summary.json`
- `/tmp/autocrypto-agent-loop-smoke/agent_ledger.jsonl`
- one `iteration_###/candidate_evaluations.json` per feedback iteration
- one isolated candidate directory per generated config inside each iteration, each with `manifest.json`, `metrics.json`, `report.md`, `dashboard.html`, model artifact, signal artifact, and feature table

With `--iterations N`, the loop is a real feedback loop:

1. generate bounded config candidates
2. walk-forward each candidate
3. rank diagnostics and ledger decisions
4. promote the selected config by `--promotion-policy`
5. use that promoted config as the next iteration's base config

Promotion policies:

- `pareto_best` — always promote the top Pareto-ranked candidate, even if the decision is `continue`
- `adopt_only` — promote only candidates that pass the stricter `adopt` decision

Supported model families are CPU-friendly score models only:

- `walk_forward_weighted_score`
- `walk_forward_equal_weight_score`
- `walk_forward_sign_weight_score`
- `walk_forward_random_forest`

`walk_forward_random_forest` uses scikit-learn's CPU `RandomForestRegressor` and keeps hyperparameters in config, e.g. `n_estimators`, `max_depth`, `min_samples_leaf`, `random_state`, and `n_jobs`.

GPU/deep-learning families such as LSTM/Transformer models are intentionally rejected by config validation for this phase.

## Planning artifacts

- Deep-interview spec: `.omx/specs/deep-interview-crypto-quant-research-pipeline.md`
- PRD: `.omx/plans/prd-crypto-quant-research-pipeline.md`
- Test spec: `.omx/plans/test-spec-crypto-quant-research-pipeline.md`
- Durable ultragoal ledger: `.omx/ultragoal/`

## Reference dates

The ETF event registry records source URLs for the January 10, 2024 SEC approval statement and January 11, 2024 first-trading/listing evidence from exchange sources. The regime module uses multiple windows rather than a single before/after split to reduce overconfident interpretation.
