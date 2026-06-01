# RALPLAN — CPU-Friendly Autonomous Research Loop

## RALPLAN-DR Summary

### Principles
1. **CPU-first research autonomy**: only pure-Python/light CPU models by default; no LSTM, Transformer, GPU, or deep-learning dependency.
2. **Config-only mutation**: the autonomous agent changes experiment configs, model family, factor params, windows, and thresholds—not runtime source code.
3. **Real walk-forward evidence**: candidate evaluation must use the existing Binance public-data walk-forward pipeline, not in-sample fixture shortcuts.
4. **Auditability over hype**: every hypothesis, config diff, artifact id, metric, and adopt/defer/stop decision is ledgered.
5. **Safety invariant**: API-key-free public data, no private/signed/order routes, no trading, >=1h cadence, no investment-advice claims.

### Top decision drivers
1. Show a credible Quant Dev/Research Engineer portfolio artifact: autonomous loop + reproducible artifacts.
2. Keep execution local/CPU-friendly so it runs on the current machine without GPU provisioning.
3. Preserve deterministic CI tests while allowing optional/manual real Binance smoke runs.

### Viable options

| Option | Summary | Pros | Cons | Decision |
|---|---|---|---|---|
| A. Pure-Python model registry + bounded config search | Add registered CPU model families implemented in stdlib, candidate generator, evaluator, ledger | No new deps; CI-safe; easy to inspect; enough for portfolio proof | Models are simpler than sklearn/XGBoost | **Choose for next phase** |
| B. Add scikit-learn now | Ridge/logistic/random forest via sklearn | More realistic ML roster; faster development for classic ML | Adds dependency and version/CI burden; more surface for leakage mistakes | Defer until pure-Python loop works |
| C. Agent edits research source code | Let AI create new model code during loop | Maximum flexibility | Unsafe, unreproducible, violates config-only autonomy | Reject |
| D. GPU/deep sequence models | LSTM/Transformer/TFT | Popular quant buzzwords | Not runnable in current system; overkill; high overfit risk | Reject |

**Decision:** Option A now, with an explicit later extension point for optional sklearn once the loop, ledger, and evaluator are stable.

---

## PRD

### Goal
Build a config-only autonomous research loop that can propose CPU-friendly model/factor/window candidates, run actual Binance public-data walk-forward backtests, compare results using research diagnostics, and ledger self-feedback decisions.

### Non-goals
- No live/sandbox order placement.
- No private/account/signed API routes or API keys.
- No GPU/deep-learning models.
- No investment advice or production-alpha claim.
- No runtime code mutation by the autonomous loop.

### User workflow
1. User runs a CLI command such as:
   ```bash
   PYTHONPATH=src python3 -m autocrypto_lab.cli run-agent-loop \
     --output-dir artifacts/agent_loop \
     --run-id agent_loop \
     --symbols BTC,ETH,SOL,XRP \
     --interval 1h \
     --lookback-hours 168 \
     --train-periods 48 \
     --test-periods 12 \
     --max-candidates 6
   ```
2. The agent builds baseline config and candidate configs.
3. For each candidate:
   - run public Binance walk-forward backtest
   - persist raw/normalized/feature/model/signal/report artifacts
   - compute metrics and diagnostics
   - write ledger entry with config diff, hypothesis, artifact ids, metrics, decision
4. The loop ranks candidates via Pareto/research diagnostics.
5. It emits a summary report and ledger JSONL.

### CPU-friendly model roster v1
All models must share the same artifact contract: `model_id`, `model_type`, `features`, `weights`, `train_window`, `eval_window`, `input_hash`, `metrics`, `signal_score`.

1. `walk_forward_weighted_score` — current correlation-weighted factor score.
2. `walk_forward_equal_weight_score` — equal-weight normalized factor score baseline.
3. `walk_forward_sign_weight_score` — sign(IC)-only robust score to reduce overfit to tiny IC magnitudes.
4. `walk_forward_ridge_score` — optional pure-Python ridge linear score if small-matrix solver remains simple/tested; otherwise defer to next story.

### Candidate search v1
- Deterministic candidate templates, not free-form code generation.
- Candidate dimensions:
  - factor set: momentum, reversal, volatility, flow, derivatives_pressure
  - factor params: lookback values for momentum/reversal/volatility
  - model family: weighted/equal/sign-weighted
  - walk-forward train/test/step windows
  - fee/slippage assumptions
- Hard budget: `max_candidates`, default small.
- Stop policy: stop after budget, or after N consecutive `defer`, or when no candidate improves diagnostics.

### Evaluator policy
Candidate decisions must not use net return alone. Use:
- net_return_after_funding
- max_drawdown
- IC
- quantile monotonicity / spread
- turnover and cost survival
- periods/fold count minimum
- robustness flags

Decision outcomes:
- `adopt`: improves Pareto vs baseline and diagnostics pass
- `continue`: diagnostics informative but not better enough
- `defer`: weak diagnostics, cost failure, or insufficient folds
- `stop`: budget exhausted / no viable candidate

### Ledger requirements
Every candidate ledger entry must include:
- run_id, parent/baseline run_id
- hypothesis
- config_snapshot and config_diff
- config_hash
- model_family and hyperparams
- raw_data_snapshot_ids
- normalized_data_snapshot_ids
- feature_table_id
- model_artifact_id
- signal_artifact_id
- report/dashboard/manifest paths
- metrics
- decision
- rationale
- known limitations

---

## Test Spec

### Unit tests
- config accepts only CPU-friendly registered model families/hyperparams.
- candidate generator produces deterministic configs and never unknown keys/private keys.
- model registry rejects unknown/GPU model names.
- equal/sign-weighted model artifacts produce `signal_score` and walk-forward metadata.
- evaluator decision does not adopt based on net return alone.

### Integration tests
- fake Binance adapter candidate loop evaluates at least 2 candidates and writes ledger entries with artifact ids.
- candidate artifacts are isolated by run_id/candidate_id.
- summary ranks candidates and records best/adopt/defer decisions.

### Safety tests
- no API key/private/signed/order route accepted.
- autonomous loop cannot mutate runtime code paths.
- sub-1h interval rejected.

### E2E/manual smoke
- real Binance public smoke for small budget:
  ```bash
  run-agent-loop --lookback-hours 48 --train-periods 24 --test-periods 6 --max-candidates 2
  ```
- CI remains deterministic with fake adapter/fixtures only.

---

## Ultragoal story decomposition — commit per step

### G001 — CPU model registry contract
Add config schema and model registry contract for CPU-friendly model families. Include unknown/GPU model rejection tests.
Commit intent: `Constrain autonomous models to CPU-friendly registry`

### G002 — Additional pure-Python score models
Implement equal-weight and sign-weight walk-forward score models under existing artifact contract. Tests prove OOS scoring and artifact metadata.
Commit intent: `Add CPU-friendly walk-forward score models`

### G003 — Candidate generator
Implement deterministic config candidate generator for factor/model/window/hyperparam templates with budget and config-only mutation guarantees.
Commit intent: `Generate bounded config-only research candidates`

### G004 — Real evaluator loop
Wire candidate configs into reusable public Binance/fake-adapter walk-forward evaluator; isolate artifacts by candidate run_id.
Commit intent: `Evaluate autonomous candidates with walk-forward backtests`

### G005 — Ledger and summary report
Extend ledger/summary to record candidate artifact lineage, metrics, decision, rationale, and Pareto ranking.
Commit intent: `Ledger autonomous candidate feedback decisions`

### G006 — CLI and docs
Add `run-agent-loop` CLI and README usage for CPU-friendly autonomous loop.
Commit intent: `Expose CPU-friendly autonomous research loop`

### G007 — Final verification gate
Run deterministic tests, real small Binance smoke, no-trade scan, slop scan, architecture review, and push.
Commit intent: `Verify autonomous research loop safety and reproducibility`

---

## Available agent roster / follow-up staffing

- `executor`: implement stories G001-G006.
- `test-engineer`: strengthen deterministic fake-adapter and leakage tests.
- `architect`: final sign-off on config-only boundary, model registry, and evaluator loop.
- `code-reviewer`: final security/safety review.
- `verifier`: completion evidence and command audit.

Recommended follow-up: `$ultragoal` durable sequential execution with commit per story. Use `$team` only if splitting implementation lanes by disjoint files. `$ralph` fallback only if a single blocker needs persistent fix/verification.

---

## Architect Review — CLEAR

Architectural status: **CLEAR**.

- The selected Option A is the correct near-term architecture because it proves autonomous research behavior without introducing GPU/deep-learning or dependency risk.
- The strongest counterargument is that pure-Python score models may look less impressive than sklearn/XGBoost; however the project currently needs a safe, auditable loop before richer estimators. Optional sklearn remains a later extension after the ledger/evaluator is stable.
- Main tradeoff: model sophistication vs reproducibility/safety. The plan chooses reproducibility and config-only control first, which matches the user constraints and current codebase maturity.
- Execution via ultragoal is feasible with commit-per-story boundaries because model registry, candidate generation, evaluator loop, ledger, CLI, and final verification are separable.

## Critic Evaluation — APPROVE

Verdict: **APPROVE**.

- Principle-option consistency: pass. CPU-only, config-only, public-data-only constraints are reflected in every story.
- Alternatives: pass. GPU/deep and source-mutating autonomy are explicitly rejected; sklearn is fairly deferred.
- Testability: pass. Unit, integration, safety, and manual e2e checks are concrete.
- Acceptance criteria: pass. Every story has a commit intent and verifiable evidence.
- Risk mitigation: pass. Safety invariants and ledger requirements are first-class.

## Final handoff

Proceed with `$ultragoal` as requested. Use the G001-G007 decomposition above and commit after every story. Do not start live/sandbox trading work in this phase.
