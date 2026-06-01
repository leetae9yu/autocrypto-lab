"""Vertical walking skeleton pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from autocrypto_lab.backtest import information_coefficient, run_long_short, run_signal_backtest
from autocrypto_lab.config import load_config
from autocrypto_lab.data import load_ohlcv_csv
from autocrypto_lab.factors import add_forward_returns, apply_factor_dsl, build_public_futures_feature_table
from autocrypto_lab.manifest import RunManifest, stable_hash, write_manifest
from autocrypto_lab.models import fit_weighted_score_model, score_model, write_model_artifacts
from autocrypto_lab.pit import validate_feature_label_order
from autocrypto_lab.report import write_markdown_report
from autocrypto_lab.regime import write_regime_report
from autocrypto_lab.dashboard import write_dashboard
from autocrypto_lab.storage import PublicDataArtifactManifest, write_public_normalized_artifact, write_public_raw_artifact


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


def _fixture_public_sources(input_csv: Path, symbols: tuple[str, ...]) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    rows = load_ohlcv_csv(input_csv)
    rows = [row for row in rows if row["symbol"] in symbols]
    klines = []
    funding = []
    open_interest = []
    basis = []
    for row in rows:
        public_symbol = f"{row['symbol']}USDT"
        kline = dict(row)
        kline["symbol"] = public_symbol
        klines.append(kline)
        funding.append({"timestamp": row["timestamp"], "symbol": public_symbol, "funding_rate": row.get("funding_rate", 0.0)})
        open_interest.append({"timestamp": row["timestamp"], "symbol": public_symbol, "open_interest": row.get("open_interest", 0.0)})
        basis.append({"timestamp": row["timestamp"], "symbol": public_symbol, "spot_future_basis": row.get("spot_future_basis", 0.0)})
    return klines, funding, open_interest, basis


def _fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    preferred = [
        "timestamp",
        "known_at",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "funding_rate",
        "open_interest",
        "spot_future_basis",
        "momentum",
        "volatility",
        "derivatives_pressure",
        "source_known_at",
        "forward_return",
        "label_timestamp",
        "label_available",
        "model_id",
        "signal_score",
    ]
    keys = set().union(*(row.keys() for row in rows)) if rows else set()
    return [key for key in preferred if key in keys] + sorted(keys - set(preferred))


def _write_public_fixture_lineage(output_dir: Path, sources: dict[str, tuple[str, str, list[dict[str, Any]]]], featured: list[dict[str, Any]]) -> dict[str, Any]:
    data_dir = output_dir / "data"
    raw_manifests: list[PublicDataArtifactManifest] = []
    normalized_manifests: list[PublicDataArtifactManifest] = []
    for name, (endpoint, interval_or_period, rows) in sources.items():
        window = {
            "start": min((row["timestamp"] for row in rows), default=None),
            "end": max((row["timestamp"] for row in rows), default=None),
            "fixture_source": True,
        }
        raw = write_public_raw_artifact(
            data_dir,
            source=f"public_fixture_{name}",
            endpoint=endpoint,
            symbol="MULTI",
            interval_or_period=interval_or_period,
            request_window=window,
            rows=rows,
            metadata={"fixture_replay": True},
        )
        normalized = write_public_normalized_artifact(
            data_dir,
            source=f"public_fixture_{name}",
            endpoint=endpoint,
            symbol="MULTI",
            interval_or_period=interval_or_period,
            rows=rows,
            fieldnames=_fieldnames(rows),
            raw_artifact_ids=[raw.artifact_id],
            request_window=window,
            metadata={"fixture_replay": True},
        )
        raw_manifests.append(raw)
        normalized_manifests.append(normalized)
    feature_table = write_public_normalized_artifact(
        data_dir,
        source="public_fixture_features",
        endpoint="feature_table",
        symbol="MULTI",
        interval_or_period="1h",
        rows=featured,
        fieldnames=_fieldnames(featured),
        raw_artifact_ids=[manifest.artifact_id for manifest in normalized_manifests],
        request_window={},
        metadata={"feature_table": True},
    )
    return {
        "raw_manifests": raw_manifests,
        "normalized_manifests": normalized_manifests,
        "feature_table": feature_table,
        "artifact_lineage": {
            "raw_data_snapshot_ids": [manifest.artifact_id for manifest in raw_manifests],
            "normalized_data_snapshot_ids": [manifest.artifact_id for manifest in normalized_manifests],
            "feature_table_id": feature_table.artifact_id,
        },
    }


def run_public_fixture_pipeline(input_csv: Path, output_dir: Path, raw_config: dict) -> dict[str, Path]:
    cfg = load_config({**raw_config, "public_only": True, "allow_private_read": False})
    config_hash = stable_hash(raw_config)
    klines, funding, open_interest, basis = _fixture_public_sources(input_csv, cfg.symbols)
    features = cfg.factor_specs()
    featured = build_public_futures_feature_table(klines, funding, open_interest, basis, horizon=cfg.horizon_periods, factor_specs=features)
    validate_feature_label_order(featured)
    lineage = _write_public_fixture_lineage(
        output_dir,
        {
            "klines": ("/fapi/v1/klines", cfg.interval, klines),
            "funding": ("/fapi/v1/fundingRate", "8h", funding),
            "open_interest": ("/futures/data/openInterestHist", cfg.interval, open_interest),
            "basis": ("/futures/data/basis", cfg.interval, basis),
        },
        featured,
    )
    model = fit_weighted_score_model(featured, features=[spec["name"] for spec in features], model_id=f"{cfg.run_id}_weighted_score")
    scored = score_model(featured, model)
    model_dir = output_dir / "models"
    persisted_model = write_model_artifacts(model_dir, model, scored)
    metrics = run_signal_backtest(scored, fee_bps=cfg.fee_bps, slippage_bps=cfg.slippage_bps)
    metrics["factor_model"] = persisted_model.model_id
    report_path = output_dir / "report.md"
    regime_path = output_dir / "regime_report.md"
    dashboard_path = output_dir / "dashboard.html"
    manifest_path = output_dir / "manifest.json"
    write_markdown_report(report_path, cfg.run_id, metrics, limitations=["Fixture replay validates the public futures pipeline shape; live public-data pulls are optional manual smoke checks."])
    write_regime_report(regime_path, scored, factor="signal_score")
    write_dashboard(dashboard_path, [report_path, regime_path, Path(persisted_model.signal_output_path)], output_dir / "ledger.jsonl")
    write_manifest(
        manifest_path,
        RunManifest(
            run_id=cfg.run_id,
            config_hash=config_hash,
            artifact_paths={
                "report": str(report_path),
                "regime_report": str(regime_path),
                "dashboard": str(dashboard_path),
                "model": str(model_dir / f"{persisted_model.model_id}.model.json"),
                "signals": persisted_model.signal_output_path,
                "feature_table": lineage["feature_table"].path,
            },
            source_metadata={
                "input_csv": str(input_csv),
                "symbols": list(cfg.symbols),
                "interval": cfg.interval,
                "factor_specs": features,
                "public_only": True,
                "artifact_lineage": {
                    **lineage["artifact_lineage"],
                    "model_artifact_id": persisted_model.artifact_hash,
                    "signal_artifact_id": stable_hash(scored),
                },
            },
        ),
    )
    return {"report": report_path, "regime_report": regime_path, "dashboard": dashboard_path, "manifest": manifest_path, "model": model_dir / f"{persisted_model.model_id}.model.json", "signals": Path(persisted_model.signal_output_path), "feature_table": Path(lineage["feature_table"].path)}
