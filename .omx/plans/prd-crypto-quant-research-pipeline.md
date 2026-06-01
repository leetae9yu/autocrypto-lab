# PRD: Autocrypto Lab — Crypto Quant Research Pipeline

Status: Approved by RALPLAN consensus  
Source of truth: `.omx/specs/deep-interview-crypto-quant-research-pipeline.md`  
Planning mode: RALPLAN-DR, standard, consensus approved  
Target execution: `$ultragoal` sequential durable delivery with commit-per-step discipline

## 1. Product Goal

Build a near-production, local-first crypto quant research engineering portfolio project. The system must demonstrate reproducible data collection, point-in-time factor research, cost-aware backtesting, ETF-regime diagnostics, report/dashboard generation, and an autonomous config-only research loop.

This is **not** a live trading system, investment-advice product, or profit-guarantee claim.

## 2. Audience

- Primary: reviewers evaluating Research Engineer / Quant Dev capability.
- Secondary: the maintainer running local research and autonomous config experiments.

## 3. RALPLAN-DR Summary

### Principles

1. Research credibility over profit claims.
2. Local-first reproducibility through CLI, typed configs, deterministic artifacts, and CI smoke tests.
3. Config-only autonomy through declarative DSL/registries, not runtime code mutation.
4. Point-in-time correctness and cost-aware diagnostics are first-class.
5. No-trade safety boundary comes before any exchange/account integration.
6. Ledger provenance records every autonomous hypothesis, config change, rationale, result, and decision.

### Decision Drivers

1. Portfolio-grade evidence for quant research engineering skill.
2. Safety and auditability before any future live-trading extension.
3. Experiment velocity without weakening reproducibility or safety.

### Alternatives Considered

| Option | Decision | Rationale |
|---|---|---|
| Modular Python package + CLI + config DSL + local storage | Chosen | Best fit for reproducibility, CI, config-only autonomy, and portfolio evidence. |
| Notebook-first research repo | Rejected | Fast exploration but weak provenance, CI, no-trade safety, and autonomous ledger discipline. |
| Production trading platform | Rejected | Violates v1 no-order endpoint boundary and expands beyond research diagnostics. |
| Heavy orchestration framework in v1 | Deferred | Adds scope before a simple vertical CLI pipeline proves insufficient. |

## 4. Core Workflows

1. `collect/update data -> build features -> run backtest -> generate report` through a single CLI path.
2. Autonomous research loop: propose hypothesis -> mutate config only -> execute run -> evaluate Pareto/research diagnostics -> ledger continue/adopt/defer/stop decision.
3. Dashboard demo: inspect run artifacts, report outputs, and ledger state.

## 5. Data Scope

- Canonical v1 assets: `BTC`, `ETH`, `SOL`, `XRP`.
- Minimum cadence: `1h`; sub-hour scalping is out of scope.
- Timeframe/cadence is a configurable research axis bounded at `>=1h`.
- Public/free data first:
  - OHLCV
  - funding rates
  - open interest
  - spot/futures basis
  - volume
  - selected macro / ETF / regime metadata
- Paid/vendor data requires separate approval.

## 6. Research Scope

- Factor families:
  - momentum
  - reversal
  - volatility
  - flow / supply-demand
  - derivatives-market factors
- ETF regime analysis:
  - multiple event windows around U.S. spot BTC ETF approval/trading/initial-flow stabilization.
  - event metadata must be source-backed.
  - SEC approval date anchor: January 10, 2024 per SEC statement.
  - first trading date anchor: January 11, 2024 per exchange/listing notices such as Nasdaq IBIT debut and Cboe/NYSE listings.
- Results must disclose short ETF-flow sample, overlapping market regimes, and research-diagnostic limitations.

Reference URLs for planning/execution sourcing:

- SEC statement: https://www.sec.gov/newsroom/speeches-statements/gensler-statement-spot-bitcoin-011023
- Nasdaq IBIT debut: https://www.nasdaq.com/press-release/blackrocks-ibit-debuts-on-nasdaq-2024-01-11
- Cboe new listing example: https://www.cboe.com/us/equities/notices/new_listings/details/?etf=true&firm_name=ARK+21+Shares&first_trade_dt=2024-01-11&ipo=true&symbols=ARKB
- NYSE rule bulletin example: https://www.nyse.com/publicdocs/nyse/markets/nyse/rule-interpretations/2024/NYSE_RB-24-010.pdf

## 7. Safety Boundaries

- No order create/cancel/position-changing endpoint exposure in v1.
- Trading-permission API keys are not supported.
- Read-only account context may be supported behind restricted interfaces.
- Reports and dashboards must avoid investment advice or profit guarantee language.
- Local-first execution; cloud production deployment requires separate approval.

## 8. Architecture Decision

Use a modular Python package with:

- `src/autocrypto_lab/` package.
- `autocrypto` CLI entrypoint.
- typed config schema and strict validation.
- registry-backed factor/model/backtest/report components.
- local artifact storage via lightweight file formats selected during implementation, e.g. Parquet/SQLite/DuckDB/JSON/CSV as appropriate.
- markdown report generation and minimal dashboard over local artifacts.
- tests and fixtures that run without external services.

## 9. Story Plan for Ultragoal

Each story must end with a focused commit and green evidence.

| Story | Objective | Green Evidence |
|---|---|---|
| G001 | Repo/package/CLI skeleton + sample fixtures + CI smoke | CLI help/import test passes; sample fixture committed. |
| G002 | Safety boundary first: no order endpoints/read-only adapter/no-trade tests | tests prove unsafe endpoints/config are rejected. |
| G003 | Config schema + registries + artifact manifest + ledger foundation | config validation and ledger schema tests pass. |
| G004 | Minimal walking skeleton: fixture OHLCV -> one factor -> PIT check -> cost-aware backtest -> report | sample e2e CLI produces report/manifest. |
| G005 | Public/free data adapter contracts + local storage snapshots for canonical symbols/cadence | adapter contract tests and cadence validation pass. |
| G006 | Full factor DSL/families and configurable timeframe axis | factor DSL tests cover all core families and `>=1h` rule. |
| G007 | PIT/leakage validation hardening | PIT/leakage tests fail on synthetic future leak and pass valid fixtures. |
| G008 | Backtest diagnostics: IC, quantiles, long/short, vol, MDD, turnover, costs | metric tests and fixture report pass. |
| G009 | Sourced ETF event/window registry | registry artifact includes source URLs and tests for required windows. |
| G010 | ETF multi-window regime report | report compares windows and includes limitations. |
| G011 | Autonomous config-only loop with Pareto diagnostics and mandatory ledger rationale | loop dry-run mutates configs only and ledger records rationale/result/decision. |
| G012 | Minimal dashboard over reports/runs/ledger | dashboard smoke/import test passes. |
| G013 | E2E polish, README, portfolio narrative, final CI smoke | documented one-command run and final verification pass. |

## 10. Acceptance Criteria

v1 is complete only when all are true:

1. One command can run data/fixture collection -> features -> backtest -> report.
2. Point-in-time and future-leakage tests are automated.
3. ETF multi-window regime report includes IC, quantile returns, long/short performance, volatility, drawdown, and limitations.
4. Cost-aware backtest includes fees, slippage, funding/holding-cost proxies or documented defensible approximations.
5. Autonomous loop ledger records every AI hypothesis, config change, rationale, run result, and adopt/defer/stop decision.
6. Minimal dashboard displays key runs, charts, reports, and ledger state.
7. CI smoke tests pass on sample/mock data quickly.
8. No-trade safety tests prove order endpoints cannot be called in v1 and read-only boundaries are enforced.

## 11. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Scope creep | Vertical story sequence; no heavy orchestration until needed. |
| Data quality gaps | fixtures, source metadata, adapter contracts, snapshot manifests. |
| Future leakage | PIT utilities and adversarial leakage tests. |
| Overfitting by autonomous loop | Pareto frontier + research diagnostics, not single return ranking. |
| ETF sample limitations | mandatory limitations section and multi-window robustness framing. |
| Safety regression | safety story early plus final no-trade scan/tests. |
| CI runtime | small deterministic fixtures for smoke/e2e. |

## 12. Handoff

Proceed with `$ultragoal` using this PRD and `.omx/plans/test-spec-crypto-quant-research-pipeline.md`. Use `$team` only if parallel execution is explicitly launched under the ultragoal ledger. Use `$ralph` only as fallback.
