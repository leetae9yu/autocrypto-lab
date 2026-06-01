# RALPLAN-DR: Public Futures Factor Autonomy Phase

Status: Planning only; implementation intentionally not started  
Repo: `/home/opc/projects/autocrypto-lab`  
Date: 2026-06-01  
Mode: RALPLAN-DR short mode  
Target next phase: **API-key-free public futures backtest system with real factor model outputs and an autonomous config-only experiment loop**  
Explicit exclusion: **no live trading, order placement, sandbox order execution, or account-key integration in this phase**

## 1. Principles

1. **Public-data-first research credibility** — backtests must run from API-key-free Binance/USDⓈ-M public market data before any sandbox/live account work is considered.
2. **Point-in-time reproducibility** — every dataset, feature table, model artifact, strategy config, report, and ledger decision must be reproducible from saved config and local artifacts.
3. **Config-only autonomy** — the autonomous agent may create/choose factor models and strategies by writing validated configs/artifacts only; it must not mutate Python source at runtime.
4. **Research diagnostics over profit claims** — selection must use robust diagnostics such as IC, quantiles, risk, turnover, costs, funding, drawdown, and stability, not headline returns alone.
5. **Safety boundary remains hard** — no live trading/order implementation, no trading-permission keys, and no investment-advice language.

## 2. Decision Drivers

1. **Portfolio-grade quant research evidence:** demonstrate real public futures ingestion, historical storage, PIT features, model artifacts, strategy evaluation, and autonomous research provenance.
2. **Safe autonomous iteration:** let an agent explore factor/model/strategy space while preserving auditability and preventing source-code or live-trading side effects.
3. **Dependency-light execution velocity:** extend the current passing walking skeleton without prematurely adding heavy data/model infrastructure unless justified by tests and artifact needs.

## 3. Viable Options

### Option A — Incremental public-data research engine on current package, dependency-light baseline (recommended)

Build on the current `src/autocrypto_lab/` skeleton with exchange-neutral public-data adapters, local partitioned artifacts, PIT feature builders, simple but real multi-factor scoring/model artifacts, and a repeated config-only autonomous loop.

**Pros**
- Preserves current passing v1 foundation and test suite (`42 passed` reported).
- Keeps API-key-free public futures backtesting as the main milestone.
- Minimizes architectural churn and avoids a premature trading-platform rewrite.
- Allows fast vertical evidence: ingest -> store -> features -> model -> strategy/backtest -> report -> ledger.
- Fits existing touchpoints: `adapters.py`, `storage.py`, `data.py`, `config.py`, `factors.py`, `backtest.py`, `autonomous.py`, `ledger.py`, `pipeline.py`, `cli.py`.

**Cons**
- Dependency-light storage/model choices may need later migration if datasets grow.
- Simple first model family may look less sophisticated than ML-heavy approaches.
- Binance public endpoints have endpoint-specific retention/limit constraints that require careful chunking and artifact metadata.

### Option B — Data platform first with DuckDB/Parquet and richer model abstractions

Introduce a more formal local research warehouse and model registry before expanding autonomy.

**Pros**
- Better long-horizon scalability for larger historical datasets and cross-sectional features.
- Cleaner separation between raw data, features, labels, model runs, and reports.
- More natural path to advanced statistical/ML model experiments later.

**Cons**
- Adds dependency and schema complexity before a public-data vertical slice proves needs.
- Slower to deliver visible portfolio-grade end-to-end evidence.
- Higher migration/compatibility risk for the current skeleton.

### Option C — Autonomous strategy generator first, still fixture-backed

Prioritize model/strategy config generation and ledgering on fixtures, deferring real public futures ingestion.

**Pros**
- Fastest way to demonstrate agentic config-only research behavior.
- Keeps tests deterministic and avoids external rate-limit/data-window issues early.

**Cons**
- Fails the user's clarified priority: API-key-free Binance/futures public data should be used first.
- Risks another toy demo rather than a credible quant research system.
- Weakens model outputs because features remain fixture-limited.

### Recommended option

Choose **Option A**. It is the right next phase because it turns the current walking skeleton into a real API-key-free public futures research system while keeping the hard safety boundary and enabling autonomous config-only experimentation. Defer Option B-style heavier warehouse/model dependencies until Option A reveals concrete bottlenecks.

## 4. Requirements Summary

### In scope

- **Hard public-only phase mode:** this phase must reject API keys, secrets, signed routes, private/account reads, `allow_private_read=True`, order/cancel/position/leverage/margin endpoints, and any exchange HTTP `POST`/`DELETE` action. Existing v1 read-only-account tolerance is explicitly not part of this phase.
- Binance USDⓈ-M public futures ingestion without API keys:
  - `/fapi/v1/klines` with `symbol`, `interval`, `startTime`, `endTime`, `limit` up to 1500.
  - `/fapi/v1/fundingRate` with `startTime`, `endTime`, `limit` up to 1000.
  - `/futures/data/openInterestHist` with supported periods including `1h`; official docs note latest 1 month availability.
  - `/futures/data/basis` with `contractType=PERPETUAL`, supported periods including `1h`; official docs note latest 30 days availability.
  - Later optional public market-data families: long/short ratio and taker buy/sell volume endpoints.
- Local historical storage for **separate raw endpoint artifacts** and normalized public futures datasets. Klines, funding, open-interest, basis, long/short, and taker-flow must keep endpoint-specific schemas before any normalized PIT join.
- Point-in-time feature table builder joining endpoint-specific raw/normalized sources by explicit known-at timestamps; funding/OI/basis must not be prematurely forced into a single OHLCV row shape without source metadata.
- True multi-factor model artifacts: `model_id`, config, feature list, coefficients/weights/rules, train/evaluation window, metrics, input data hashes, generated `signal_score` output path, and model artifact hash.
- Strategy/backtest artifacts driven by persisted model outputs (`model_id` or `signal_score`) only, not the current first-factor/`primary_factor` shortcut.
- Autonomous repeated experiment loop that:
  - proposes or selects factor/model/strategy configs;
  - runs bounded backtests;
  - evaluates Pareto/research diagnostics;
  - writes ledger entries for hypothesis, config diff/hash, data snapshot, model artifact, metrics, decision, and rationale;
  - changes config/artifacts only, not source code.
- CLI/pipeline commands for ingestion, feature build, model run, backtest/report, and autonomous dry-run/loop.
- Tests that do not require public network access by default; use fake HTTP/fixtures for CI.

### Out of scope

- Live trading, order placement, position-changing endpoints, and sandbox/live key flows.
- Account/private data ingestion.
- Paid/vendor datasets.
- Profit guarantees or investment-advice output.
- Heavy orchestration frameworks unless later justified.

## 5. Acceptance Criteria

1. **API-key-free ingestion:** a user can ingest or replay Binance public futures klines/funding/open-interest/basis data without providing API keys; tests prove no credential is required and no auth/signature headers are emitted.
2. **Endpoint chunking correctness:** kline and funding history chunk requests respect documented max limits (`1500` klines, `1000` funding rows) and use `startTime`/`endTime` deterministically.
3. **Retention-aware metadata:** open-interest and basis artifacts record their documented latest-window limitations so reports do not misrepresent available history.
4. **Historical storage:** raw and normalized artifacts include source endpoint, symbol, interval/period, request window, row count, created timestamp, schema version, content/config hash, retention note, and optional public-archive checksum when data.binance.vision files are used.
5. **PIT feature table:** feature rows join all sources using known-at timestamps; synthetic future-leak fixtures fail validation.
6. **Multi-factor model artifacts:** at least one real multi-factor model family produces persisted `model_id`, model metadata, feature weights/rules, signal scores, train/eval windows, evaluation metrics, input data hashes, and reproducible artifact hashes.
7. **Strategy/backtest from model output:** final-phase backtests consume model-generated `signal_score`/`model_id` artifacts and produce cost-aware diagnostics including fees/slippage/funding proxy, IC, quantiles, long/short or exposure returns, turnover, volatility, MDD/drawdown, and stability indicators; tests reject a final path that directly calls single-factor `run_long_short(..., factor="momentum")` as the strategy source.
8. **Autonomous config loop:** a dry-run repeated loop proposes/selects configs, runs experiments, records decisions, and never edits Python code or live-trading settings.
9. **Ledger provenance:** every autonomous experiment records hypothesis, config diff/hash/snapshot, raw and normalized data snapshot ids, feature table id, model artifact id, signal artifact id, metrics, Pareto/diagnostic rationale, and adopt/defer/continue/stop decision as required schema fields.
10. **No-trade/no-signed-route boundary:** static/runtime tests fail if order-placement, cancellation, position-changing, leverage/margin, private/account, signed-route, API-key, auth-header, or exchange HTTP `POST`/`DELETE` paths are introduced in implementation modules.
11. **CI remains deterministic:** default tests pass without network access, credentials, or live Binance availability.
12. **User-facing docs/reporting:** README or generated report explains API-key-free scope, public-data limits, no-live-trading boundary, and research-diagnostic limitations.

## 6. Implementation Steps (handoff plan; no code in this plan)

### Step 1 — Lock phase boundaries and config schema extensions

**Touchpoints:** `src/autocrypto_lab/config.py`, `src/autocrypto_lab/safety.py`, `tests/test_config_registry_ledger.py`, `tests/test_safety.py`, docs/README.  
**Work:** define config sections for public futures ingestion, storage paths, feature table specs, model specs, strategy/backtest specs, and autonomous loop limits. Preserve `>=1h` cadence and add a stricter `public_only` phase mode that rejects credentials, signed/private/account reads, `allow_private_read=True`, and live-trading settings.  
**Output:** validated phase config examples and tests that reject credentials/private reads/live-trading settings for this phase.

### Step 2 — Add Binance public futures adapter contracts and fake-client tests

**Touchpoints:** `src/autocrypto_lab/adapters.py`, `src/autocrypto_lab/data.py`, `tests/test_adapters_storage.py`, new/extended fixtures.  
**Work:** define exchange-neutral public futures interfaces and a Binance implementation plan for klines, funding, open interest, basis, plus optional later endpoints and optional Binance public archive ZIP/CHECKSUM source for longer kline history. Use injectable HTTP/fake client in tests.  
**Output:** request planning/chunking tests for limits, parameters, retry/error behavior, archive checksum metadata, and credential-free execution with no auth/signature headers.

### Step 3 — Build raw/normalized local storage and manifests

**Touchpoints:** `src/autocrypto_lab/storage.py`, `src/autocrypto_lab/manifest.py`, `src/autocrypto_lab/data.py`, `tests/test_adapters_storage.py`, fixture directories.  
**Work:** specify artifact layout for endpoint-specific raw responses, normalized tables, schema versions, source metadata, hashes, retention notes, and optional archive checksums. Prefer existing lightweight file patterns first; introduce dependencies only if separately approved.  
**Output:** deterministic storage tests for row counts, hashes, duplicate timestamp behavior, missing timestamp policy, endpoint schema separation, and manifest contents.

### Step 4 — Implement PIT feature table builder for public futures data

**Touchpoints:** `src/autocrypto_lab/pit.py`, `src/autocrypto_lab/factors.py`, `src/autocrypto_lab/data.py`, `tests/test_pit.py`, `tests/test_factor_dsl.py`, `tests/test_data_validation.py`.  
**Work:** plan feature table generation from klines + funding + open interest + basis + existing factor DSL, with known-at joins and label shifting.  
**Output:** PIT tests covering aligned joins, horizon labels, missing source policies, and adversarial future leaks.

### Step 5 — Add multi-factor model artifact layer

**Touchpoints:** `src/autocrypto_lab/factors.py`, `src/autocrypto_lab/backtest.py`, `src/autocrypto_lab/registry.py`, `src/autocrypto_lab/storage.py`, `tests/test_factor_dsl.py`, `tests/test_backtest_diagnostics.py`.  
**Work:** define dependency-light baseline model families such as weighted score, rank aggregation, and simple train/evaluate split; persist `model_id`, model configs, feature list, weights/rules, train/eval windows, metrics, input hashes, signal output paths, and artifact hashes.  
**Output:** tests proving model artifacts are reproducible and final backtests use model outputs rather than directly reading one fixture factor or first configured factor.

### Step 6 — Upgrade strategy/backtest diagnostics around model signals

**Touchpoints:** `src/autocrypto_lab/backtest.py`, `src/autocrypto_lab/report.py`, `src/autocrypto_lab/pipeline.py`, `tests/test_backtest_diagnostics.py`, `tests/test_walking_skeleton.py`.  
**Work:** route model signal scores into strategy rules and cost-aware backtest diagnostics; include funding/holding-cost proxy and robustness metrics.  
**Output:** deterministic fixture tests for IC, quantiles, exposure/long-short returns, turnover, volatility, MDD/drawdown, costs, and artifact/report metadata.

### Step 7 — Expand autonomous config-only experiment loop

**Touchpoints:** `src/autocrypto_lab/autonomous.py`, `src/autocrypto_lab/ledger.py`, `src/autocrypto_lab/config.py`, `src/autocrypto_lab/pipeline.py`, `tests/test_autonomous_loop.py`, `tests/test_config_registry_ledger.py`.  
**Work:** plan repeated bounded experiments where the agent chooses factor/model/strategy config variants, runs the pipeline, ranks outcomes using Pareto/research diagnostics, and records decisions. Enforce config/artifact-only mutation.  
**Output:** dry-run tests for repeated experiments, config diffs/hashes, decision rationale, no source-code mutation, and stop/adopt/defer/continue behavior.

### Step 8 — Add CLI vertical slices and reports

**Touchpoints:** `src/autocrypto_lab/cli.py`, `src/autocrypto_lab/pipeline.py`, `src/autocrypto_lab/report.py`, `src/autocrypto_lab/dashboard.py`, `tests/test_cli.py`, `tests/test_dashboard.py`, `README.md`.  
**Work:** expose commands for public-data ingest/replay, feature build, model/backtest/report, and autonomous dry-run loop. Keep network operations optional and make fixture/replay mode the CI default.  
**Output:** one-command fixture e2e plus documented optional live public-data command requiring no API key.

### Step 9 — Final safety, docs, and portfolio polish

**Touchpoints:** `README.md`, `docs/final-quality-gate.md`, safety tests, full test suite.  
**Work:** document phase scope, Binance public endpoint limitations, reproducibility, no-live-trading boundary, and autonomous ledger examples.  
**Output:** full deterministic test suite, no-trade scan, fixture e2e, and final review evidence.

## 7. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Binance public endpoint limits and retention windows create partial datasets | Chunk klines/funding by documented limits; record retention/window limitations in manifests and reports; make tests fake-client based. |
| Network flakiness breaks CI | Default CI uses fixtures/fake HTTP only; live public-data smoke is optional/manual. |
| Feature leakage through cross-source joins | PIT builder must join on known-at timestamps and adversarial future-leak fixtures must fail. |
| Autonomous loop overfits to one metric | Use Pareto diagnostics across return, risk, turnover, costs, stability, and sample coverage; ledger rationale must state tradeoffs. |
| Scope creep into live trading | Keep no-trade safety tests and config validation early; sandbox/live keys are explicitly later-phase only. |
| Storage/model abstractions become too heavy | Start dependency-light and artifact-oriented; add DuckDB/Parquet/ML libraries only through a later dependency decision. |
| Public-data semantics are misrepresented | Preserve source endpoint metadata, row windows, retention notes, and limitations in reports. |
| Agent config mutations become opaque | Require config diffs, hashes, model artifact ids, and ledger events for every experiment. |

## 8. Verification Steps

1. Run baseline after each story: `pytest`.
2. Run targeted safety checks after config/adapter/autonomy changes: safety tests plus endpoint-aware static no-trade/no-signed-route scan for forbidden order/cancel/position/leverage/margin/private/auth/signature/API-key terms and exchange HTTP `POST`/`DELETE` actions in implementation modules.
3. Run adapter fake-client tests for Binance request parameters, chunking, no-key behavior, and endpoint error handling.
4. Run storage/manifest tests for schema version, hash, source metadata, row counts, and retention notes.
5. Run PIT/leakage tests with synthetic future-leak fixture expected to fail validation.
6. Run model artifact tests proving reproducibility from config + input hashes.
7. Run model-signal backtest diagnostics tests for deterministic metric outputs.
8. Run autonomous loop dry-run tests proving config-only mutation, ledger completeness, and bounded repeated experiments.
9. Run fixture e2e CLI: ingest/replay fixture -> build features -> train/score model -> backtest -> report -> ledger entry.
10. Optional manual smoke outside CI: public Binance data pull for a small BTCUSDT/ETHUSDT 1h window without API keys, saving artifacts and report.
11. Final quality gate: full test suite, no-trade scan, fixture e2e, docs check, ai-slop-cleaner on changed files, code-review APPROVE/CLEAR before any durable goal is marked complete.

## 9. ADR

### ADR: Build an API-key-free public futures research engine before sandbox/live integration

**Status:** Proposed for next phase; implementation not started.  
**Decision:** Extend the current `autocrypto-lab` skeleton into an API-key-free Binance/USDⓈ-M public futures backtest system with local historical artifacts, PIT feature tables, real multi-factor model outputs, model-driven strategy backtests, and an autonomous config-only experiment loop. Do not implement live trading, order endpoints, sandbox order flows, or API-key/account integrations in this phase.

**Drivers**
- The user clarified that API keys are not needed for backtesting and public Binance/futures data should come first.
- The repo already has a passing walking skeleton; the next value jump is replacing fixtures/toy diagnostics with real public-data research artifacts.
- Autonomous strategy/model generation is only credible if it is constrained to validated configs and auditable ledgers.

**Alternatives considered**
1. **Dependency-light incremental engine on current package** — chosen because it delivers the next credible vertical slice with low churn and strong tests.
2. **Warehouse/model-platform rewrite first** — deferred because it adds dependencies and delays evidence before the current skeleton proves concrete bottlenecks.
3. **Fixture-only autonomous generator first** — rejected for this phase because it fails the public futures data priority and risks remaining a toy demo.
4. **Sandbox/live trading integration now** — rejected because it violates the explicit next-phase safety boundary and is unnecessary for backtesting.

**Consequences**
- The system remains research-only and local-first.
- Public endpoint retention/limit constraints become first-class artifact metadata.
- Model sophistication starts with reproducible baseline artifacts rather than opaque ML complexity.
- A later phase may add read-only account context, richer storage/model dependencies, sandbox trading, or live trading only after separate planning and safety review.

**Follow-ups**
- If real public-data artifact volume becomes large, run a dependency decision for DuckDB/Parquet/Pandas/PyArrow.
- If model baselines are too limited, add a model-family expansion story after PIT/storage/autonomy are stable.
- If sandbox/live trading is later requested, require a new RALPLAN focused on safety, credentials, exchange testnet, and explicit user approval.

## 10. Available Agent Roster and Staffing Guidance

### Available agent types

- `planner` — sequencing, acceptance criteria, risk and test-shape planning.
- `explore` — fast repo-local file/symbol/pattern mapping.
- `researcher` — official docs and citation-backed external reference gathering.
- `dependency-expert` — package/storage/model dependency decisions.
- `architect` — system boundaries, artifact contracts, PIT/data/model architecture review.
- `executor` — implementation/refactoring for bounded story slices.
- `test-engineer` — test strategy, fixtures, leakage tests, CI determinism.
- `debugger` — root-cause analysis for failing tests or data/model defects.
- `verifier` — completion evidence, claim validation, test adequacy.
- `code-reviewer` — final comprehensive review.
- `code-simplifier` — cleanup after implementation without behavior changes.
- `writer` — README, docs, report narrative, limitation language.

### Recommended durable follow-up: `$ultragoal`

Use `$ultragoal` by default for the next phase because it preserves a durable repo-native goal ledger and fits the sequential story plan.

Suggested ultragoal brief:

```text
Build the next phase of autocrypto-lab as an API-key-free public Binance USDⓈ-M futures backtest research system. Implement public-data ingestion, local historical artifacts, PIT feature tables, real multi-factor model artifacts, model-driven cost-aware backtests, and an autonomous config-only experiment loop. Preserve the no-live-trading/no-order/no-API-key boundary for this phase. Use fixture/fake HTTP tests for CI and optional manual public-data smoke only.
```

Suggested story decomposition for `$ultragoal`:

1. Config and safety boundary extensions.
2. Public futures adapter contracts + fake-client tests.
3. Local raw/normalized storage and manifests.
4. PIT feature table builder.
5. Multi-factor model artifact layer.
6. Model-signal strategy/backtest diagnostics.
7. Autonomous config-only loop and ledger expansion.
8. CLI/report/dashboard/docs polish.
9. Final quality gate and code review.

Goal-mode follow-up suggestions:
- Use `$ultragoal` generally and by default for this implementation phase.
- Use `$autoresearch-goal` only if additional source-backed market-data/provider research becomes the main task.
- Use `$performance-goal` only after the vertical system exists and bottlenecks are measurable.
- Use `$ralph` only as a fallback for a stuck single-owner fix/verification loop after the plan or team run exposes a concrete blocker.

### Recommended `$team` staffing if parallel execution is later approved

Only launch `$team` after the user approves development. Suggested team size: **4 executor-role workers with explicit lane assignments**, plus leader-owned ultragoal checkpointing.

Launch hint:

```bash
omx team 4:executor "Implement the approved public futures factor autonomy phase from .omx/plans/ralplan-public-futures-factor-autonomy.md; preserve no-live-trading boundary and return tests/evidence per lane."
```

Lane guidance:

1. **Data lane — executor, medium reasoning**
   - Owns `adapters.py`, `data.py`, storage fixtures/tests for public Binance request planning and fake-client ingestion.
2. **PIT/model lane — executor, high reasoning**
   - Owns `pit.py`, `factors.py`, model artifact contracts, model signal outputs, and leakage tests.
3. **Backtest/autonomy lane — executor, high reasoning**
   - Owns `backtest.py`, `autonomous.py`, `ledger.py`, pipeline integration, Pareto diagnostics, and config-only loop tests.
4. **Verification/docs lane — executor or test-engineer if available, medium/high reasoning**
   - Owns cross-cutting tests, CLI fixture e2e, safety scan, README/report limitation language, and final evidence collection.

If using OMX Team, keep `$ultragoal` as the leader-owned durable ledger. Workers should report evidence only; they should not mutate `.omx/ultragoal` or Codex goal state.

## Stop Rule

This plan is complete when the user confirms it captures intent. Development must not start until the user explicitly approves a follow-up execution mode such as `$ultragoal` or `$team`.

## 11. Architect Review Amendments Applied

The Architect review returned `WATCH`, not because Option A was wrong, but because execution boundaries needed to be sharper. This plan was amended to require:

1. A strict `public_only` phase mode that rejects credentials, private reads, signed routes, and current v1 `allow_private_read=True` behavior.
2. Endpoint-specific raw artifacts before normalized PIT joins, so funding/OI/basis are not hidden inside one OHLCV-shaped table.
3. A mandatory model artifact contract before strategy backtests: `model_id`, features, weights/rules, train/eval windows, input hashes, signal output path, metrics, and artifact hash.
4. Backtests that consume persisted `signal_score`/`model_id` outputs, not the current first-factor shortcut.
5. Required ledger schema fields for data snapshot ids, feature table id, model artifact id, and signal artifact id.
6. Endpoint-aware safety scans for private/signed/order/leverage/margin routes and exchange HTTP `POST`/`DELETE` actions.
7. Optional Binance public archive ZIP/CHECKSUM provenance for longer kline history, while keeping REST chunking and fake-client tests as the default implementation path.

## 12. Critic Non-Blocking Improvements Applied

The Critic returned `APPROVE` with three non-blocking improvements. They are accepted as execution guidance:

### 12.1 Raw response schema tables required before implementation

Before writing adapter/storage code, execution must define schema tables for at least:

| Source | Endpoint / source | Required identity fields | Time field | Key limits / notes |
|---|---|---|---|---|
| Futures klines | `/fapi/v1/klines` or public archive ZIP | symbol, interval, open_time | open_time / close_time | REST limit max 1500; archive checksum if used |
| Funding rate | `/fapi/v1/fundingRate` | symbol | fundingTime | REST limit max 1000; ascending/inclusive windows |
| Open interest stats | `/futures/data/openInterestHist` | symbol, period | timestamp | period includes 1h; max 500; latest 1 month noted |
| Basis | `/futures/data/basis` | pair, contractType, period | timestamp | contractType PERPETUAL; max 500; latest 30 days noted |
| Optional long/short ratio | Binance public market-data endpoint | symbol/pair, period | timestamp | optional after core four sources |
| Optional taker buy/sell volume | Binance public market-data endpoint | symbol/pair, period | timestamp | optional after core four sources |

### 12.2 Symbol/pair mapping acceptance test

Execution must add acceptance tests for canonical asset mapping, e.g.:

- `BTC` -> `BTCUSDT` futures symbol / pair.
- `ETH` -> `ETHUSDT`.
- `SOL` -> `SOLUSDT`.
- `XRP` -> `XRPUSDT`.
- Unknown assets fail validation rather than being inferred silently.

### 12.3 Path-aware safety scan

The no-trade/no-signed-route scan must be path-aware:

- It should scan implementation modules under `src/autocrypto_lab/` for private/signed/order/leverage/margin/position routes and exchange HTTP `POST`/`DELETE` actions.
- It should avoid false-positive blocking on docs, tests, fixtures, or explicit denylist definitions.
- It should fail if runtime adapter code emits auth/signature headers or accepts API key/secret config in this public-only phase.

## 13. Final Consensus Status

- Planner: produced the RALPLAN-DR plan.
- Architect: `WATCH`; requested stricter public-only, endpoint-schema, model-artifact, ledger, and safety boundaries. Amendments applied.
- Critic: `APPROVE`; no blocking issues. Non-blocking improvements applied in Section 12.
- Execution status: **not started**. This is planning-only per user instruction.
