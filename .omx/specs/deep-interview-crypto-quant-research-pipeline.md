# Deep Interview Spec — Crypto Quant Research Pipeline

## Metadata

- Profile: Standard, user-tightened ambiguity target to **<3%**
- Context type: Greenfield repository
- Rounds: 11
- Final ambiguity: **1.95%**
- Threshold: **3.00%**
- Context snapshot: `.omx/context/crypto-quant-research-pipeline-20260601T041514Z.md`
- External reference inspected: `https://github.com/leetae9yu/autoquant-lab` cloned read-only to `/tmp/autoquant-lab-inspect`

## Clarity Breakdown

| Dimension | Score |
|---|---:|
| Intent | 0.99 |
| Outcome | 0.98 |
| Scope | 0.98 |
| Constraints | 0.97 |
| Success criteria | 0.97 |

Readiness gates: Non-goals explicit; decision boundaries explicit; pressure pass complete.

## Intent

Build a portfolio-grade crypto quant research engineering project, not a simplistic “profitable strategy” claim. The project should demonstrate Research Engineer / Quant Dev skill through a reproducible pipeline from data ingestion to factor research, autonomous experiment iteration, cost-aware backtesting, regime analysis, and report/dashboard output.

## Desired Outcome

A **near-production demo before live trading** with a full-stack portfolio shape:

1. Python package + CLI for reproducible end-to-end runs.
2. Config-driven data, factor, model, backtest, and report pipeline.
3. Notebooks or generated reports for analysis narrative.
4. Minimal Streamlit-style dashboard for exploration, not a polished commercial web product.
5. AI Agent autonomous research loop that proposes hypotheses, edits configs, runs backtests, evaluates results, and records every decision/rationale in a ledger.
6. Safety boundary that supports read-only account context but prohibits order endpoints in v1.

## In Scope

- Public/free-data-first data collection for Binance-style crypto market data:
  - OHLCV, funding rates, open interest, spot/futures basis, volume, and selected macro/ETF/regime data.
- Universe: **BTC, ETH, SOL, XRP** as v1 canonical assets.
- Cadence: minimum **1h**; interval/timeframe is itself a configurable factor/model axis, not a fixed constant. Second/minute scalping is explicitly out of scope.
- Factor families:
  - momentum, reversal, volatility, flow/supply-demand, derivatives-market factors.
- Config-only autonomous research loop:
  - Agent may modify experiment configs/DSL parameters, not runtime code, while achieving research-code-level expressiveness through registries and declarative config.
- ETF regime experiment:
  - Multiple event windows around US spot BTC ETF events; planning/execution should verify exact dates/windows from reliable sources.
- Backtesting:
  - Point-in-time alignment, future-leakage tests, cost-aware evaluation, IC, quantile returns, long/short, volatility, drawdown, turnover, and regime comparisons.
- Reporting:
  - Honest limitation disclosure: short ETF-flow sample, overlapping market regimes, research diagnostics only.

## Out of Scope / Non-goals

- No polished/commercial web product in v1.
- No second/minute scalping; minimum 1h trading/rebalancing cadence.
- No investment advice, trading recommendation, or profit guarantee language.
- No v1 order execution endpoints: no Binance order create/cancel/position-changing calls.
- No production claim; outputs are research diagnostics and portfolio evidence.
- Paid data/vendor APIs are not the default; public/free data first. Paid/private data requires separate approval.

## Decision Boundaries

OMX/AI Agent may decide without re-asking:

- Python stack, package/CLI/test layout, directory structure.
- Local storage format and schema details, e.g. Parquet, SQLite, DuckDB.
- Priority/order of free/public data adapters.
- Factor DSL and registry design.
- Initial factor/model/hyperparameter defaults.
- ETF event windows after checking reliable sources.
- Minimal dashboard UX and chart priorities.
- CI smoke sample sizes, runtime thresholds, and fixture strategy.

Must not decide without explicit approval:

- Enabling live trading or order endpoints.
- Using trading-permission API keys.
- Switching to paid/private/vendor data as a core dependency.
- Cloud production deployment or always-on operation if it materially changes scope/cost.
- Making investment recommendation claims.

## Constraints

- Greenfield repository; no existing source/package structure.
- v1 should be local-first and reproducible.
- Config-only autonomy is a hard architectural constraint: registries/DSL must expose enough expressiveness for factor/model experimentation without code mutation by the agent loop.
- Every AI Agent action must be ledgered with change, rationale, evidence, result, and continue/adopt/stop decision.
- Read-only account/private API access is allowed only for non-trading information; order endpoints are prohibited.

## Testable Acceptance Criteria

v1 is complete only when all are true:

1. **End-to-end CLI**: one command can run data collection/update → feature generation → backtest → report.
2. **Point-in-time tests**: future leakage and timestamp alignment checks are automated.
3. **Regime report**: ETF multiple-window regime report compares factor IC, quantile returns, long/short performance, volatility, drawdown, and limitations.
4. **Cost-aware backtest**: fees, slippage, funding/holding costs or defensible proxies are included.
5. **Autonomous loop ledger**: every AI hypothesis, config change, rationale, run result, and adopt/defer/stop decision is persisted.
6. **Dashboard demo**: minimal exploratory dashboard displays key runs, charts, and current research state.
7. **CI smoke tests**: mock or sample-data smoke/e2e tests pass quickly in CI.
8. **No-trade safety tests**: tests prove order endpoints cannot be called in v1 and read-only boundaries are enforced.

## Autonomous Loop Policy

Use **Pareto frontier + research diagnostics**:

- Do not adopt a branch based on highest return alone.
- Compare net/cost-aware performance, max drawdown, turnover, robustness, IC stability, regime consistency, and interpretability.
- Require diagnostics: no data leakage, cost survival, regime-specific behavior, stress/drawdown explanation, limitations, and next hypothesis.
- If no Pareto improvement or diagnostics fail, defer/stop and ledger the reason.

## Assumptions Exposed + Resolutions

- Initial idea looked like a research pipeline; pressure pass revealed a bigger goal: near-production autonomous research loop before live trading.
- “Full stack portfolio” risked scope creep; non-goals and safety boundaries now constrain it.
- Autonomy could have meant code mutation; resolved as config-only autonomy with DSL/registry expressiveness.
- ETF analysis could have been a single split; resolved as multiple event windows with sourced date/window definitions.

## Brownfield / Reference Evidence Notes

Repository is greenfield: local listing showed only `.omx` files and no package/source files. `autoquant-lab` was inspected as a reference pattern. Relevant reference facts:

- It uses an offline research harness with configs, scripts, tests, reports, manifests/ledgers, and generated/private artifacts excluded from git.
- Its autonomous loop emphasizes guardrails, local artifacts, scorecards, and research diagnostics rather than production trading advice.
- Its skill/runbook pattern supports config-only autonomy, frozen harness boundaries, ledger state, and multi-metric promotion.

## Condensed Transcript

### Round 1 — outcome+scope

- Label: [from-user]
- Question: v1 primary deliverable shape
- Answer: `{"kind": "option", "value": "full-stack-portfolio", "selected_labels": ["Full Stack Portfolio"]}`
- Impact: Outcome clarified as full-stack portfolio: package/CLI, notebooks, report, and simple dashboard.

### Round 2 — non-goals/scope

- Label: [from-user]
- Question: Select v1 non-goals
- Answer: `{"kind": "multi", "selected_values": ["no-polished-web-product"], "other_text": "ambiguity goal <3%"}`
- Impact: Non-goal confirmed: dashboard should not be polished/commercial-grade. User also tightened ambiguity threshold to <3%.

### Round 3 — scope pressure / non-goals

- Label: [from-user]
- Question: Contrarian check on maximum v1 scope
- Answer: `{"kind": "other", "value": "Near-production demo; later real Binance trading, now right before real trading. Wants an AI Agent autonomous research loop inspired by github.com/leetae9yu/autoquant-lab: inspect outputs, propose hypotheses, run backtests, modify factor model and hyperparameters iteratively."}`
- Impact: Scope expanded to near-production demo and autonomous AI research/backtest optimization loop; external reference requested for factual grounding.

### Round 4 — decision boundaries

- Label: [from-user]
- Question: What may the AI agent autonomously change in v1?
- Answer: `{"kind": "other", "value": "Config-only autonomy, but config should be expressive enough to approximate research-code autonomy: create/compose many factor models and adjust parameters/hyperparameters without editing code."}`
- Impact: Decision boundary clarified: autonomous agent edits configs/experiment specs only; code-level flexibility must be exposed through registries/DSL/config rather than runtime code mutation.

### Round 5 — safety non-goals + decision boundaries

- Label: [from-user]
- Question: Select v1 safety boundaries for near-production scope
- Answer: `{"kind": "multi", "selected_values": ["public-free-data-first", "no-investment-advice"], "other_text": "No second/minute scalping; minimum 1h trading/rebalancing cadence."}`
- Impact: Confirmed public/free-data-first, no investment advice/profit guarantee language, and minimum 1h cadence/no scalping. Did not yet settle live-order/paper-trading/read-only-key boundary.

### Round 6 — execution safety boundary

- Label: [from-user]
- Question: How far may Binance order/account functionality go in v1?
- Answer: `{"kind": "option", "value": "read-only-account-ok"}`
- Impact: v1 may use read-only private API for balances/positions; order endpoints and trade execution are forbidden.

### Round 7 — success criteria

- Label: [from-user]
- Question: Which acceptance criteria must v1 satisfy?
- Answer: `{"kind": "multi", "selected_values": ["e2e-cli", "pit-tests", "regime-report", "cost-aware", "agent-ledger", "dashboard-demo", "ci-smoke", "no-trade-safety"], "other_text": "AI Agent ledger is very important; every change and rationale must be recorded."}`
- Impact: Acceptance criteria expanded to all major deliverables; ledger/rationale traceability is a first-class requirement.

### Round 8 — data universe + cadence

- Label: [from-user]
- Question: What is the canonical v1 research universe/cadence?
- Answer: `{"kind": "other", "value": "BTC/ETH/SOL/XRP; time interval itself should be encoded as a factor/model axis, not fixed, with prior minimum 1h cadence boundary preserved."}`
- Impact: Universe narrowed to four liquid symbols; cadence becomes configurable research axis bounded at >=1h.

### Round 9 — ETF regime experiment design

- Label: [from-user]
- Question: How should the US spot BTC ETF before/after comparison be canonically analyzed?
- Answer: `{"kind": "option", "value": "multi-window"}`
- Impact: ETF regime analysis should compare multiple event windows rather than a single split. Exact event dates/windows to be sourced in planning/research.

### Round 10 — autonomous loop stop/adopt policy

- Label: [from-user]
- Question: What rule should drive continue/adopt/stop for the AI research loop?
- Answer: `{"kind": "other", "value": "Pareto frontier + Research diagnostics"}`
- Impact: Autonomous loop must avoid single-metric overfitting; decisions depend on Pareto improvement plus diagnostics including no leakage, cost survival, regime robustness, and explicit limitations.

### Round 11 — final decision boundaries

- Label: [from-user]
- Question: Which planning/implementation decisions may OMX/AI Agent make autonomously?
- Answer: `{"kind": "multi", "selected_values": ["python-stack-layout", "storage-format", "free-data-adapters", "factor-dsl-design", "default-factors-models", "etf-windows-sources", "dashboard-minimal-ux", "test-thresholds"]}`
- Impact: All proposed implementation/planning decision areas may be decided autonomously without re-asking, inside the clarified safety and scope boundaries.


## Recommended Handoff

Recommended: `$ralplan` / `$plan --consensus --direct .omx/specs/deep-interview-crypto-quant-research-pipeline.md` to turn this clarified spec into PRD + test-spec artifacts before implementation.

Then use `$ultragoal` or `$autopilot` for durable execution; use `$team` if implementation is split across data, backtest, autonomous loop, dashboard, and tests. Use `$ralph` only as explicit fallback for single-owner persistence.
