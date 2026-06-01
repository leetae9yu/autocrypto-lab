"""Command line entrypoint for autocrypto-lab."""

from __future__ import annotations

import argparse
from pathlib import Path

from autocrypto_lab import __version__
from autocrypto_lab.pipeline import run_fixture_pipeline, run_public_fixture_pipeline


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
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
