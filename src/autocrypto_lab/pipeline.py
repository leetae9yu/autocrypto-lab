"""Vertical walking skeleton pipeline."""

from __future__ import annotations

from pathlib import Path

from autocrypto_lab.backtest import information_coefficient, run_long_short
from autocrypto_lab.config import load_config
from autocrypto_lab.data import load_ohlcv_csv
from autocrypto_lab.factors import add_forward_returns, apply_factor_dsl
from autocrypto_lab.manifest import RunManifest, stable_hash, write_manifest
from autocrypto_lab.pit import validate_feature_label_order
from autocrypto_lab.report import write_markdown_report
from autocrypto_lab.regime import write_regime_report
from autocrypto_lab.dashboard import write_dashboard


def run_fixture_pipeline(input_csv: Path, output_dir: Path, raw_config: dict) -> dict[str, Path]:
    cfg = load_config(raw_config)
    config_hash = stable_hash(raw_config)
    rows = load_ohlcv_csv(input_csv)
    rows = [row for row in rows if row["symbol"] in cfg.symbols]
    factor_specs = cfg.factor_specs()
    primary_factor = factor_specs[0]["name"]
    featured = add_forward_returns(apply_factor_dsl(rows, factor_specs), horizon=cfg.horizon_periods)
    validate_feature_label_order(featured)
    metrics = run_long_short(featured, factor=primary_factor, fee_bps=cfg.fee_bps, slippage_bps=cfg.slippage_bps)
    metrics["ic"] = information_coefficient(featured, primary_factor)
    metrics["factor"] = primary_factor
    report_path = output_dir / "report.md"
    regime_path = output_dir / "regime_report.md"
    dashboard_path = output_dir / "dashboard.html"
    manifest_path = output_dir / "manifest.json"
    write_markdown_report(report_path, cfg.run_id, metrics)
    write_regime_report(regime_path, featured, factor=primary_factor)
    write_dashboard(dashboard_path, [report_path, regime_path], output_dir / "ledger.jsonl")
    write_manifest(
        manifest_path,
        RunManifest(
            run_id=cfg.run_id,
            config_hash=config_hash,
            artifact_paths={"report": str(report_path), "regime_report": str(regime_path), "dashboard": str(dashboard_path)},
            source_metadata={"input_csv": str(input_csv), "symbols": list(cfg.symbols), "interval": cfg.interval, "factor_specs": factor_specs},
        ),
    )
    return {"report": report_path, "regime_report": regime_path, "dashboard": dashboard_path, "manifest": manifest_path}
