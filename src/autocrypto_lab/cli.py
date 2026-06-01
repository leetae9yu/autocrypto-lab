"""Command line entrypoint for autocrypto-lab."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from autocrypto_lab import __version__
from autocrypto_lab.autonomous import evaluate_candidate_configs
from autocrypto_lab.pipeline import parse_utc, run_fixture_pipeline, run_public_binance_pipeline, run_public_fixture_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autocrypto",
        description="Local-first crypto quant research pipeline.",
    )
    parser.add_argument("--version", action="version", version=f"autocrypto {__version__}")
    sub = parser.add_subparsers(dest="command")

    sample = sub.add_parser("sample-info", help="Print bundled sample fixture path.")
    sample.add_argument("--root", default="tests/fixtures", help="Fixture root directory.")

    run = sub.add_parser("run-sample", help="Run the fixture walking-skeleton pipeline.")
    run.add_argument("--input", default="tests/fixtures/ohlcv_1h.csv")
    run.add_argument("--output-dir", default="artifacts/sample_run")
    run.add_argument("--run-id", default="sample_run")

    public = sub.add_parser("run-public-fixture", help="Run API-key-free public futures fixture pipeline with model artifacts.")
    public.add_argument("--input", default="tests/fixtures/ohlcv_1h.csv")
    public.add_argument("--output-dir", default="artifacts/public_fixture_run")
    public.add_argument("--run-id", default="public_fixture_run")

    live_public = sub.add_parser("run-public-binance", help="Download real API-key-free Binance USDⓈ-M public futures data and run model/backtest.")
    live_public.add_argument("--output-dir", default="artifacts/public_binance_run")
    live_public.add_argument("--run-id", default="public_binance_run")
    live_public.add_argument("--symbols", default="BTC,ETH", help="Comma-separated base assets from BTC,ETH,SOL,XRP.")
    live_public.add_argument("--interval", default="1h", help="Binance kline interval; v1 enforces >=1h.")
    live_public.add_argument("--start", help="UTC ISO start, e.g. 2026-05-30T00:00:00Z. Defaults to now-lookback-hours.")
    live_public.add_argument("--end", help="UTC ISO end, e.g. 2026-06-01T00:00:00Z. Defaults to now.")
    live_public.add_argument("--lookback-hours", type=int, default=72, help="Used when --start is omitted.")
    live_public.add_argument("--train-periods", type=int, default=12, help="Walk-forward train window length in interval periods.")
    live_public.add_argument("--test-periods", type=int, default=6, help="Walk-forward out-of-sample test window length in interval periods.")
    live_public.add_argument("--step-periods", type=int, help="Walk-forward step length in interval periods. Defaults to test-periods.")

    agent_loop = sub.add_parser("run-agent-loop", help="Run CPU-friendly config-only autonomous candidate loop on public Binance data.")
    agent_loop.add_argument("--output-dir", default="artifacts/agent_loop_run")
    agent_loop.add_argument("--run-id", default="agent_loop_run")
    agent_loop.add_argument("--symbols", default="BTC,ETH", help="Comma-separated base assets from BTC,ETH,SOL,XRP.")
    agent_loop.add_argument("--interval", default="1h", help="Binance kline interval; v1 enforces >=1h.")
    agent_loop.add_argument("--factors", default="momentum,derivatives_pressure", help="Comma-separated factor names or DSL basics.")
    agent_loop.add_argument("--start", help="UTC ISO start. Defaults to now-lookback-hours.")
    agent_loop.add_argument("--end", help="UTC ISO end. Defaults to now.")
    agent_loop.add_argument("--lookback-hours", type=int, default=72, help="Used when --start is omitted.")
    agent_loop.add_argument("--max-candidates", type=int, default=3, help="Maximum generated candidate configs to evaluate.")
    agent_loop.add_argument("--train-periods", type=int, default=24, help="Default walk-forward train window length.")
    agent_loop.add_argument("--test-periods", type=int, default=6, help="Default out-of-sample test window length.")
    agent_loop.add_argument("--step-periods", type=int, help="Default walk-forward step length. Defaults to test-periods.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "sample-info":
        root = Path(args.root)
        print(root / "ohlcv_1h.csv")
        return 0
    if args.command == "run-sample":
        outputs = run_fixture_pipeline(
            Path(args.input),
            Path(args.output_dir),
            {"run_id": args.run_id, "symbols": ["BTC", "ETH"], "interval": "1h"},
        )
        for name, path in outputs.items():
            print(f"{name}: {path}")
        return 0
    if args.command == "run-public-fixture":
        outputs = run_public_fixture_pipeline(
            Path(args.input),
            Path(args.output_dir),
            {"run_id": args.run_id, "symbols": ["BTC", "ETH"], "interval": "1h", "factors": ["momentum", "volatility", "derivatives_pressure"]},
        )
        for name, path in outputs.items():
            print(f"{name}: {path}")
        return 0
    if args.command == "run-public-binance":
        end = parse_utc(args.end) if args.end else datetime.now(timezone.utc)
        start = parse_utc(args.start) if args.start else end - timedelta(hours=args.lookback_hours)
        symbols = [symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()]
        outputs = run_public_binance_pipeline(
            Path(args.output_dir),
            {
                "run_id": args.run_id,
                "symbols": symbols,
                "interval": args.interval,
                "factors": ["momentum", "volatility", "derivatives_pressure"],
            },
            start=start,
            end=end,
            train_periods=args.train_periods,
            test_periods=args.test_periods,
            step_periods=args.step_periods,
        )
        for name, path in outputs.items():
            print(f"{name}: {path}")
        return 0
    if args.command == "run-agent-loop":
        end = parse_utc(args.end) if args.end else datetime.now(timezone.utc)
        start = parse_utc(args.start) if args.start else end - timedelta(hours=args.lookback_hours)
        symbols = [symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()]
        factors = [factor.strip() for factor in args.factors.split(",") if factor.strip()]
        summary = evaluate_candidate_configs(
            Path(args.output_dir),
            {
                "run_id": args.run_id,
                "symbols": symbols,
                "interval": args.interval,
                "factors": factors,
            },
            start=start,
            end=end,
            max_candidates=args.max_candidates,
            train_periods=args.train_periods,
            test_periods=args.test_periods,
            step_periods=args.step_periods,
        )
        print(f"summary: {summary['summary_path']}")
        print(f"ledger: {summary['ledger_path']}")
        print(f"best_candidate_id: {summary['best_candidate_id']}")
        print(f"candidate_count: {summary['candidate_count']}")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
