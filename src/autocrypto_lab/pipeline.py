"""Vertical walking skeleton pipeline."""

from __future__ import annotations

from pathlib import Path

from autocrypto_lab.backtest import information_coefficient, run_long_short
from autocrypto_lab.config import load_config
from autocrypto_lab.data import load_ohlcv_csv
from autocrypto_lab.factors import add_forward_returns, add_momentum
from autocrypto_lab.manifest import RunManifest, stable_hash, write_manifest
from autocrypto_lab.pit import validate_feature_label_order
from autocrypto_lab.report import write_markdown_report


def run_fixture_pipeline(input_csv: Path, output_dir: Path, raw_config: dict) -> dict[str, Path]:
    cfg = load_config(raw_config)
    config_hash = stable_hash(raw_config)
    rows = load_ohlcv_csv(input_csv)
    rows = [row for row in rows if row["symbol"] in cfg.symbols]
    featured = add_forward_returns(add_momentum(rows), horizon=cfg.horizon_periods)
    validate_feature_label_order(featured)
    metrics = run_long_short(featured, factor="momentum", fee_bps=cfg.fee_bps, slippage_bps=cfg.slippage_bps)
    metrics["ic"] = information_coefficient(featured, "momentum")
    report_path = output_dir / "report.md"
    manifest_path = output_dir / "manifest.json"
    write_markdown_report(report_path, cfg.run_id, metrics)
    write_manifest(
        manifest_path,
        RunManifest(
            run_id=cfg.run_id,
            config_hash=config_hash,
            artifact_paths={"report": str(report_path)},
            source_metadata={"input_csv": str(input_csv), "symbols": list(cfg.symbols), "interval": cfg.interval},
        ),
    )
    return {"report": report_path, "manifest": manifest_path}
