# Final Quality Gate — Public Futures Factor Autonomy Phase

Scope: `.omx/ultragoal/goals.json` G001–G009 for the public-data-first Binance/USDⓈ-M futures factor research phase.

## Behavior Lock / Verification

- `python3 -m pytest -q` → **67 passed**.
- `PYTHONPATH=src python3 -m autocrypto_lab.cli run-public-fixture --output-dir /tmp/autocrypto-final-public-smoke-v3 --run-id final_public_v3` → generated `report.md`, `regime_report.md`, `dashboard.html`, `manifest.json`, `models/final_public_v3_weighted_score.model.json`, `models/final_public_v3_weighted_score_signals.json`, and a public fixture `feature_table` artifact.
- `PYTHONPATH=src python3 -m autocrypto_lab.cli run-sample --output-dir /tmp/autocrypto-final-sample-v3 --run-id final_sample_v3` → generated legacy fixture report/regime/dashboard/manifest artifacts.
- `python3 -m compileall -q src tests` → pass.

## AI Slop Cleaner Pass

Cleanup plan: inspect changed `src/`, `tests/`, `README.md`, `pyproject.toml`, and OMX planning artifacts for fallback-like code, silent defaults, bypass/workaround signals, dead code, duplicate abstractions, weak boundaries, and missing regression tests.

Fallback findings: no masking fallback slop in runtime code or tests. Slop scan only found planning prose in `.omx/plans/*` using “fallback” or “compatibility”; these are non-runtime workflow notes.

Cleanup/remediation completed after final review:
- Replaced route denylist-only safety with explicit public endpoint allowlist plus signed/private query/header rejection.
- Rejected forbidden and unknown top-level config keys before config construction.
- Required ledger provenance fields for raw, normalized, feature, model, and signal artifact IDs.
- Made PIT joins respect source `known_at` when present.
- Made model artifact hashes deterministic by excluding `created_at` and output paths.
- Required every signal-backtest row to carry `signal_score` and a consistent non-empty `model_id`.
- Wired public fixture raw/normalized/feature-table lineage into run manifest metadata.

## Static / Safety Gates

- AST no-trade/no-signed-route scan over `src/autocrypto_lab` → **pass** (`no forbidden trade/signed routes`).
- The implemented public phase exposes no order create/cancel/position-changing functions and no exchange POST/DELETE action path.
- Backtests and public fixture replay remain API-key-free; live trading and sandbox order execution are intentionally not implemented.

## Review Gate

- Code-reviewer lane: **APPROVE** after recheck; no remaining CRITICAL/HIGH/MEDIUM/LOW findings.
- Architect lane: **CLEAR**; prior BLOCK items resolved.

## Remaining Risks / Explicit Limits

- The public fixture weighted-score demo is in-sample and validates pipeline shape, artifact contracts, and safety—not production alpha or investment advice.
- Manual/live public Binance downloads and larger historical archive checksum workflows are future extensions.
- Live/sandbox trading requires a separate explicit phase with keys, permissions, and safety design; not included here.
