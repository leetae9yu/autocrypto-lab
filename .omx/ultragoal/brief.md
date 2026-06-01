Build the next phase of autocrypto-lab from .omx/plans/ralplan-public-futures-factor-autonomy.md.

Objective: implement an API-key-free public Binance USDⓈ-M futures research system with local historical artifacts, PIT feature tables, real multi-factor model artifacts, model-signal cost-aware backtests, and an autonomous config-only experiment loop.

Hard constraints:
- No live trading, no order placement, no sandbox order execution, no account-key integration.
- Public-only phase: reject API keys/secrets/private reads/signed routes/order/cancel/position/leverage/margin endpoints and exchange HTTP POST/DELETE actions in implementation modules.
- CI/default tests require no network, credentials, or live Binance availability; use fake HTTP/fixtures.
- Minimum cadence >= 1h.
- Backtests for final phase must consume persisted model_id/signal_score artifacts, not direct single-factor shortcut.
- Autonomous loop may mutate configs/artifacts only, never Python source at runtime.
- Ledger provenance must include hypothesis, config diff/hash/snapshot, raw/normalized data snapshot ids, feature table id, model artifact id, signal artifact id, metrics, rationale, decision.
- Commit per step and push to origin main.

Source plan: .omx/plans/ralplan-public-futures-factor-autonomy.md
