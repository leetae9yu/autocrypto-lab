# Test Spec: Autocrypto Lab — Crypto Quant Research Pipeline

Status: Approved by RALPLAN consensus  
PRD: `.omx/plans/prd-crypto-quant-research-pipeline.md`  
Source spec: `.omx/specs/deep-interview-crypto-quant-research-pipeline.md`

## 1. Test Strategy

Use a layered but vertical-first test strategy:

1. Unit tests for schemas, registries, factors, metrics, ledger, and safety boundaries.
2. Fixture-based integration tests for CLI walking skeleton.
3. Point-in-time/leakage adversarial tests.
4. No-trade safety static/runtime tests.
5. Final e2e smoke on deterministic sample data.

All stories must finish with green evidence and a commit.

## 2. Required Test Surfaces

### Config and Registry Tests

- Valid canonical experiment config loads.
- Sub-hour cadence config is rejected.
- Unknown assets/factors/models are rejected with helpful errors.
- Factor/model/backtest/report registries expose stable names.
- Config-only mutation constraints are enforceable.

### Safety Tests

- No order create/cancel/position-changing methods are exposed by v1 adapters.
- Trading-permission config is rejected.
- Read-only account adapter cannot call unsafe endpoints.
- Static scan fails if forbidden endpoint names are introduced outside explicit denylist tests/docs.

Forbidden runtime concepts for v1 implementation code:

- `create_order`
- `cancel_order`
- `place_order`
- `market_order`
- `limit_order`
- `change_position`
- `reduce_only` as an executable order path

### Data Tests

- Fixture OHLCV ingestion normalizes canonical symbols.
- Duplicate timestamps are rejected or deterministically resolved.
- Missing timestamp policy is explicit.
- Snapshot manifest captures source, symbol, interval, created_at, row count, and config hash.

### PIT / Leakage Tests

- Features never use future rows relative to label timestamp.
- Labels are shifted correctly for configured horizon.
- Joins respect known-at timestamps.
- ETF regime windows do not leak post-event data into pre-event feature generation.
- Synthetic future-leak fixture must fail.

### Factor Tests

- Momentum, reversal, volatility, flow/supply-demand, and derivatives factor families compute on fixtures.
- Factor DSL composition is declarative and validates parameters.
- Timeframe/cadence is part of config and bounded at `>=1h`.

### Backtest and Metrics Tests

- Cost-aware backtest applies fees, slippage, and funding/holding-cost proxy fields.
- IC, quantile returns, long/short return, volatility, MDD, turnover, and drawdown metrics are deterministic on fixtures.
- Pareto diagnostics compare return/risk/turnover/cost/robustness without selecting only highest return.

### ETF Regime Tests

- ETF event registry contains sourced metadata for approval/trading/window definitions.
- Multiple windows are represented explicitly.
- Generated regime report includes required metrics and limitations.
- Source URLs are preserved in artifact metadata.

### Autonomous Loop Tests

- Dry-run agent loop proposes a hypothesis.
- It mutates config only, not Python runtime code.
- It runs or simulates a fixture backtest.
- It writes ledger entries containing hypothesis, config diff/hash, rationale, metrics, diagnostics, and decision.
- It can choose continue/adopt/defer/stop using Pareto + diagnostics policy.

### Report Tests

- Markdown report contains metrics, charts/artifact references, limitations, run metadata, and no investment-advice language.
- Report generation is deterministic for fixture runs.

### Dashboard Smoke Tests

- Dashboard module imports without optional service credentials.
- It can render/load sample report and ledger artifacts.
- It does not require public network access for smoke mode.

### E2E CLI Smoke

- One command runs fixture data -> features -> PIT validation -> backtest -> report.
- Expected artifact tree is produced.
- Runtime remains within the CI threshold chosen during implementation.

## 3. Per-Story Green Evidence

| Story | Minimum verification command/evidence |
|---|---|
| G001 | `pytest` import/CLI help tests pass. |
| G002 | safety/no-trade tests pass. |
| G003 | config/registry/ledger schema tests pass. |
| G004 | fixture e2e CLI produces report and manifest. |
| G005 | data adapter contract tests pass. |
| G006 | factor DSL/family tests pass. |
| G007 | PIT adversarial tests pass. |
| G008 | backtest metric tests pass. |
| G009 | ETF event registry tests pass with source URLs. |
| G010 | regime report fixture test passes. |
| G011 | autonomous loop dry-run/ledger tests pass. |
| G012 | dashboard smoke test passes. |
| G013 | full test suite + final e2e smoke + no-trade scan pass. |

## 4. Final Quality Gate

Before final ultragoal completion:

1. Run full targeted verification, expected default: `pytest` plus fixture CLI smoke.
2. Run no-trade safety scan/tests.
3. Run ai-slop-cleaner on changed files or record no-op cleaner evidence.
4. Run code-review and require APPROVE/CLEAR.
5. Only then mark the aggregate ultragoal complete and push.
