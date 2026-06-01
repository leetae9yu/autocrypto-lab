# Context Snapshot: crypto-quant-research-pipeline

- Timestamp UTC: 20260601T041514Z
- Task statement: Build/plan a reproducible crypto quant research project/pipeline.
- Desired outcome: Execution-ready requirements for a portfolio-quality Research Engineer/Quant Dev project.
- Stated solution: Data collection -> time alignment -> feature generation -> backtesting -> cost modeling -> report generation for crypto factors and BTC ETF regime comparison.
- Probable intent hypothesis: Demonstrate rigorous quant research engineering and reproducible methodology, not claim a live profitable trading strategy.
- Known facts/evidence:
  - User wants public data such as Binance OHLCV, funding, open interest, basis, volume, macro indicators.
  - Core factor families: momentum, reversal, volatility, flow/supply-demand, derivatives-market factors.
  - Core regime event: US spot BTC ETF introduction; ETF flow data period is short and should be treated as regime context, not long-history direct alpha.
  - Results must disclose sample limitations and overlapping market regimes.
  - Repository appears greenfield: only `.omx` files found; no source/package files yet. `omx explore` was attempted but did not return promptly, so local file listing was used.
- Constraints:
  - Deep-interview only; no direct implementation in this mode.
  - Need explicit non-goals and decision boundaries before handoff.
  - Must preserve reproducibility and honest statistical interpretation.
- Unknowns/open questions:
  - Primary deliverable shape: report, notebooks, package/CLI pipeline, dashboard, or all of these.
  - First-pass asset universe, timeframe, bar granularity, and data sources.
  - How rigorous the statistical inference/backtesting should be for v1.
  - Time/cost limits and dependency preferences.
- Decision-boundary unknowns:
  - What the agent may choose autonomously: stack, directory layout, data schemas, factor set, metrics, report format.
  - What requires confirmation: paid data, live trading, API keys, external services, exact research claims.
- Likely codebase touchpoints:
  - Greenfield project structure; likely Python data/research pipeline, tests, notebooks/reports, configuration, docs.
- Prompt-safe initial-context summary status: not_needed

## Initial user idea

크립토 퀀트 리서치 프로젝트: Binance 등 공개 데이터를 이용해 OHLCV, 펀딩비, 미결제약정, 현물-선물 베이시스, 거래량, 매크로 지표를 수집하고, 모멘텀·리버설·변동성·수급·파생시장 팩터가 향후 수익률을 설명하는지 검증한다. 핵심 실험은 미국 현물 BTC ETF 도입 전후 market structure/regime change로 기존 팩터의 IC, 분위별 수익률, 롱숏 성과, 변동성, 드로다운 변화 비교. Production-ready 전략 주장이 아니라 Research Engineer/Quant Dev 포트폴리오 프로젝트.
