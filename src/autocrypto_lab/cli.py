"""Command line entrypoint for autocrypto-lab."""

from __future__ import annotations

import argparse
from pathlib import Path

from autocrypto_lab import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autocrypto",
        description="Local-first crypto quant research pipeline.",
    )
    parser.add_argument("--version", action="version", version=f"autocrypto {__version__}")
    sub = parser.add_subparsers(dest="command")

    sample = sub.add_parser("sample-info", help="Print bundled sample fixture path.")
    sample.add_argument("--root", default="tests/fixtures", help="Fixture root directory.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "sample-info":
        root = Path(args.root)
        print(root / "ohlcv_1h.csv")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
