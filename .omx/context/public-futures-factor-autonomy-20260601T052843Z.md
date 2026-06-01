# Context Snapshot: public futures factor autonomy

## Task statement
Plan the next phase of `autocrypto-lab` without starting implementation: move from a toy factor diagnostics skeleton to an API-key-free public futures data + factor model + autonomous config research loop system. User explicitly said development must not start yet.

## Desired outcome
A RALPLAN consensus plan with PRD and test spec for:
- Binance/public futures data ingestion without API keys for backtesting.
- Local historical storage and point-in-time aligned feature tables.
- Real factor model artifacts, not just single-factor diagnostics.
- Agent/autonomous config loop that proposes factor/model configs, runs backtests, evaluates Pareto frontier/research diagnostics, and ledgers every hypothesis/config diff/result/decision.
- Clear boundary for later read-only account, sandbox/testnet, and live trading phases.

## Known repo facts
- Current branch `main` is pushed to `origin/main`.
- Current v1 has package/CLI skeleton under `src/autocrypto_lab/` and tests under `tests/`.
- Current e2e CLI is `PYTHONPATH=src python3 -m autocrypto_lab.cli run-sample --output-dir ... --run-id ...`.
- Current test suite is passing: 42 tests.
- Existing files relevant to next phase: `adapters.py`, `storage.py`, `data.py`, `config.py`, `factors.py`, `backtest.py`, `autonomous.py`, `ledger.py`, `pipeline.py`, `dashboard.py`.
- Current system computes basic factors and diagnostics, but does not yet implement public futures API ingestion, large historical storage, multi-factor model fitting/scoring, repeated autonomous experiment execution, or strategy/model artifact generation.

## External evidence
Official Binance USDⓈ-M Futures public market-data docs expose public endpoints relevant to backtesting without account API keys:
- `/fapi/v1/klines` for futures klines.
- `/fapi/v1/fundingRate` for funding rate history.
- `/futures/data/openInterestHist` for open interest statistics.
- `/futures/data/basis` for basis.
Docs also list long/short ratio and taker buy/sell volume endpoints in the USDⓈ-M Futures market-data navigation.

## Constraints
- No development/implementation during this ralplan turn.
- API-key-free backtesting first; trading keys only later for sandbox/live phases.
- Minimum cadence remains >= 1h.
- No live order endpoints in this phase.
- No investment advice/profit guarantee.
- Public/free data first.
- Ledger provenance is mandatory.

## Unknowns/open questions
- Exact first historical lookback period and symbols for real ingestion can default to BTC/ETH/SOL/XRP, 1h, API-available windows.
- Whether to use stdlib CSV/JSONL first or introduce pandas/pyarrow/duckdb later; default should avoid dependencies unless explicitly approved.
- Whether to model with simple linear/score-based engines first or add statistical libraries; default should implement dependency-light baseline and leave richer models as follow-up.

## Likely touchpoints for future implementation
- `src/autocrypto_lab/adapters.py`: exchange-neutral public futures adapter protocol + Binance implementation.
- `src/autocrypto_lab/storage.py`: partitioned local snapshots/feature/model artifacts.
- `src/autocrypto_lab/config.py`: ingestion/model/autonomy config schema.
- `src/autocrypto_lab/factors.py`: feature table construction and factor families.
- `src/autocrypto_lab/backtest.py`: model-based signal scoring, portfolio simulation, costs.
- `src/autocrypto_lab/autonomous.py`: repeated config-only experiment loop.
- `src/autocrypto_lab/ledger.py`: expanded experiment ledger events.
- `src/autocrypto_lab/cli.py` and `pipeline.py`: e2e commands.
- `tests/`: API-free fake HTTP/fixture tests, PIT alignment, model artifact tests, autonomy ledger tests.
