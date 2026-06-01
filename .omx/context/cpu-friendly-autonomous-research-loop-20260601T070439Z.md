# Context Snapshot — CPU-friendly Autonomous Research Loop

## Task statement
Plan the next phase for autocrypto-lab: an AI Agent/autonomous loop that can change factor/model configs, run real Binance public-data walk-forward backtests, inspect results, self-feedback, and ledger decisions. Models must be CPU-friendly; no LSTM/GPU-heavy deep learning.

## Desired outcome
A consensus implementation plan (not code) for config-only autonomy v2:
- generate hypotheses and config candidates
- choose among registered CPU-friendly model families and hyperparameters
- run real Binance public-data walk-forward backtests
- compare diagnostics/Pareto frontier
- record every change/result/rationale in ledger
- stop/adopt/defer safely without investment-advice claims

## Known facts/evidence
- Repo has real `run-public-binance` CLI using Binance public USDⓈ-M endpoints without API keys.
- Latest walk-forward implementation pushed: `6bfbd3d Evaluate public futures signals walk-forward`.
- Current real-data model path uses `walk_forward_weighted_score` only.
- Current tests passed: 69 tests after walk-forward phase.
- Existing safety constraints reject API keys, private/signed/order routes, POST/DELETE exchange actions, and sub-1h cadence.
- Current autonomous loop is dry-run/config-ledger oriented; it does not yet execute real walk-forward candidate loops or model-family selection.

## Constraints
- CPU-friendly only: no LSTM/Transformer/GPU-needed models.
- Public/free data first; API-key-free Binance public futures path remains default.
- No live/sandbox trading or order endpoints.
- Minimum interval/rebalance cadence >=1h.
- Config-only autonomy: agent mutates configs/hyperparams/model family, not runtime source code.
- Ledger is mandatory for hypothesis, config diff, run artifacts, diagnostics, and decision.
- Results are research diagnostics, not investment advice.
- Prefer no heavy dependencies unless justified; deterministic fixture tests must remain CI-safe.

## Unknowns/open questions
- Whether to add scikit-learn now or start with pure-Python/statistical models only.
- Exact candidate budget/default search policy.
- How long real-data smoke should run in CI vs manual.
- How rich model registry should be in first implementation slice.

## Likely codebase touchpoints
- `src/autocrypto_lab/models.py` model registry/families
- `src/autocrypto_lab/autonomous.py` real runner/evaluator loop
- `src/autocrypto_lab/pipeline.py` reusable public Binance pipeline hooks
- `src/autocrypto_lab/ledger.py` candidate/decision fields
- `src/autocrypto_lab/config.py` model family/hyperparam schema
- `src/autocrypto_lab/cli.py` autonomous run command
- tests around config-only mutation, model registry, walk-forward candidates, safety, ledger provenance
