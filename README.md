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

The sample path uses deterministic fixtures under `tests/fixtures/` so CI does not need network access or credentials.

## Planning artifacts

- Deep-interview spec: `.omx/specs/deep-interview-crypto-quant-research-pipeline.md`
- PRD: `.omx/plans/prd-crypto-quant-research-pipeline.md`
- Test spec: `.omx/plans/test-spec-crypto-quant-research-pipeline.md`
- Durable ultragoal ledger: `.omx/ultragoal/`

## Reference dates

The ETF event registry records source URLs for the January 10, 2024 SEC approval statement and January 11, 2024 first-trading/listing evidence from exchange sources. The regime module uses multiple windows rather than a single before/after split to reduce overconfident interpretation.
