"""Vertical walking skeleton pipeline."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from autocrypto_lab.adapters import BinancePublicFuturesAdapter, PublicFuturesRequest, futures_symbol
from autocrypto_lab.backtest import information_coefficient, run_long_short, run_signal_backtest
from autocrypto_lab.config import load_config
from autocrypto_lab.data import load_ohlcv_csv
from autocrypto_lab.factors import add_forward_returns, apply_factor_dsl, build_public_futures_feature_table
from autocrypto_lab.manifest import RunManifest, stable_hash, write_manifest
from autocrypto_lab.models import RANDOM_FOREST_MODEL_FAMILY, SKLEARN_REGRESSOR_MODEL_FAMILIES, WEIGHT_MODE_BY_MODEL_FAMILY, fit_walk_forward_random_forest_model, fit_walk_forward_sklearn_regressor_model, fit_walk_forward_weighted_score_model, fit_weighted_score_model, score_model, write_model_artifacts
from autocrypto_lab.pit import validate_feature_label_order
from autocrypto_lab.report import write_markdown_report
from autocrypto_lab.regime import write_regime_report
from autocrypto_lab.dashboard import write_dashboard
from autocrypto_lab.storage import PublicDataArtifactManifest, write_public_normalized_artifact, write_public_raw_artifact


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def ms_to_utc(value: Any) -> datetime:
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)


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


def normalize_klines(rows: list[Any], symbol: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "timestamp": ms_to_utc(row[0]),
                "known_at": ms_to_utc(row[6]),
                "symbol": symbol,
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            }
        )
    return out


def normalize_funding(rows: list[dict[str, Any]], symbol: str) -> list[dict[str, Any]]:
    return [
        {
            "timestamp": ms_to_utc(row["fundingTime"]),
            "known_at": ms_to_utc(row["fundingTime"]),
            "symbol": symbol,
            "funding_rate": float(row.get("fundingRate", 0.0)),
        }
        for row in rows
    ]


def normalize_open_interest(rows: list[dict[str, Any]], symbol: str) -> list[dict[str, Any]]:
    return [
        {
            "timestamp": ms_to_utc(row["timestamp"]),
            "known_at": ms_to_utc(row["timestamp"]),
            "symbol": symbol,
            "open_interest": float(row.get("sumOpenInterest", row.get("openInterest", 0.0))),
        }
        for row in rows
    ]


def normalize_basis(rows: list[dict[str, Any]], symbol: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        raw_basis = row.get("basisRate", row.get("basis", row.get("spot_future_basis", 0.0)))
        out.append(
            {
                "timestamp": ms_to_utc(row["timestamp"]),
                "known_at": ms_to_utc(row["timestamp"]),
                "symbol": symbol,
                "spot_future_basis": float(raw_basis),
            }
        )
    return out


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
    return _write_public_lineage(output_dir, "public_fixture", sources, featured, {"fixture_replay": True})


def _write_public_lineage(output_dir: Path, source_prefix: str, sources: dict[str, tuple[str, str, list[dict[str, Any]], list[str]]], featured: list[dict[str, Any]], metadata: dict[str, Any]) -> dict[str, Any]:
    data_dir = output_dir / "data"
    raw_manifests: list[PublicDataArtifactManifest] = []
    normalized_manifests: list[PublicDataArtifactManifest] = []
    all_raw_ids: list[str] = []
    for name, (endpoint, interval_or_period, rows, inherited_raw_ids) in sources.items():
        window = {
            "start": min((row["timestamp"] for row in rows), default=None),
            "end": max((row["timestamp"] for row in rows), default=None),
            **metadata,
        }
        if inherited_raw_ids:
            raw_ids = inherited_raw_ids
        else:
            raw = write_public_raw_artifact(
                data_dir,
                source=f"{source_prefix}_{name}",
                endpoint=endpoint,
                symbol="MULTI",
                interval_or_period=interval_or_period,
                request_window=window,
                rows=rows,
                metadata=metadata,
            )
            raw_manifests.append(raw)
            raw_ids = [raw.artifact_id]
        all_raw_ids.extend(raw_ids)
        normalized = write_public_normalized_artifact(
            data_dir,
            source=f"{source_prefix}_{name}",
            endpoint=endpoint,
            symbol="MULTI",
            interval_or_period=interval_or_period,
            rows=rows,
            fieldnames=_fieldnames(rows),
            raw_artifact_ids=raw_ids,
            request_window=window,
            metadata=metadata,
        )
        normalized_manifests.append(normalized)
    feature_table = write_public_normalized_artifact(
        data_dir,
        source=f"{source_prefix}_features",
        endpoint="feature_table",
        symbol="MULTI",
        interval_or_period=str(metadata.get("interval", "1h")),
        rows=featured,
        fieldnames=_fieldnames(featured),
        raw_artifact_ids=[manifest.artifact_id for manifest in normalized_manifests],
        request_window={},
        metadata={**metadata, "feature_table": True},
    )
    return {
        "raw_manifests": raw_manifests,
        "normalized_manifests": normalized_manifests,
        "feature_table": feature_table,
        "artifact_lineage": {
            "raw_data_snapshot_ids": all_raw_ids,
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
            "klines": ("/fapi/v1/klines", cfg.interval, klines, []),
            "funding": ("/fapi/v1/fundingRate", "8h", funding, []),
            "open_interest": ("/futures/data/openInterestHist", cfg.interval, open_interest, []),
            "basis": ("/futures/data/basis", cfg.interval, basis, []),
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


def _fetch_raw(adapter: BinancePublicFuturesAdapter, request: PublicFuturesRequest, output_dir: Path, asset: str, interval_or_period: str) -> tuple[list[Any], str]:
    rows = adapter.fetch(request)
    if not isinstance(rows, list):
        raise ValueError(f"Binance public endpoint returned non-list payload for {request.endpoint}")
    raw = write_public_raw_artifact(
        output_dir / "data",
        source="binance_usdm_public",
        endpoint=request.endpoint,
        symbol=futures_symbol(asset),
        interval_or_period=interval_or_period,
        request_window=dict(request.params),
        rows=rows,
        retention_note=request.retention_note,
    )
    return rows, raw.artifact_id


def run_public_binance_pipeline(
    output_dir: Path,
    raw_config: dict,
    *,
    start: datetime,
    end: datetime,
    adapter: BinancePublicFuturesAdapter | None = None,
    train_periods: int = 12,
    test_periods: int = 6,
    step_periods: int | None = None,
) -> dict[str, Path]:
    cfg = load_config({**raw_config, "public_only": True, "allow_private_read": False})
    adapter = adapter or BinancePublicFuturesAdapter()
    config_hash = stable_hash({**raw_config, "start": start.isoformat(), "end": end.isoformat()})
    all_klines: list[dict[str, Any]] = []
    all_funding: list[dict[str, Any]] = []
    all_open_interest: list[dict[str, Any]] = []
    all_basis: list[dict[str, Any]] = []
    raw_ids: dict[str, list[str]] = {"klines": [], "funding": [], "open_interest": [], "basis": []}

    for asset in cfg.symbols:
        symbol = futures_symbol(asset)
        kline_raw: list[Any] = []
        for request in adapter.plan_kline_requests(asset, cfg.interval, start, end):
            rows, artifact_id = _fetch_raw(adapter, request, output_dir, asset, cfg.interval)
            kline_raw.extend(rows)
            raw_ids["klines"].append(artifact_id)
        all_klines.extend(normalize_klines(kline_raw, symbol))

        funding_raw: list[dict[str, Any]] = []
        for request in adapter.plan_funding_requests(asset, start, end):
            rows, artifact_id = _fetch_raw(adapter, request, output_dir, asset, "8h")
            funding_raw.extend(rows)
            raw_ids["funding"].append(artifact_id)
        all_funding.extend(normalize_funding(funding_raw, symbol))

        oi_request = adapter.open_interest_request(asset, cfg.interval, start, end)
        oi_rows, oi_artifact_id = _fetch_raw(adapter, oi_request, output_dir, asset, cfg.interval)
        raw_ids["open_interest"].append(oi_artifact_id)
        all_open_interest.extend(normalize_open_interest(oi_rows, symbol))

        basis_request = adapter.basis_request(asset, cfg.interval, start, end)
        basis_rows, basis_artifact_id = _fetch_raw(adapter, basis_request, output_dir, asset, cfg.interval)
        raw_ids["basis"].append(basis_artifact_id)
        all_basis.extend(normalize_basis(basis_rows, symbol))

    features = cfg.factor_specs()
    featured = build_public_futures_feature_table(all_klines, all_funding, all_open_interest, all_basis, horizon=cfg.horizon_periods, factor_specs=features)
    validate_feature_label_order(featured)
    lineage = _write_public_lineage(
        output_dir,
        "binance_usdm_public",
        {
            "klines": ("/fapi/v1/klines", cfg.interval, all_klines, raw_ids["klines"]),
            "funding": ("/fapi/v1/fundingRate", "8h", all_funding, raw_ids["funding"]),
            "open_interest": ("/futures/data/openInterestHist", cfg.interval, all_open_interest, raw_ids["open_interest"]),
            "basis": ("/futures/data/basis", cfg.interval, all_basis, raw_ids["basis"]),
        },
        featured,
        {"source": "binance_usdm_public", "start": start.isoformat(), "end": end.isoformat(), "interval": cfg.interval},
    )
    selected_model_family = cfg.model if cfg.model in (*WEIGHT_MODE_BY_MODEL_FAMILY, RANDOM_FOREST_MODEL_FAMILY, *SKLEARN_REGRESSOR_MODEL_FAMILIES) else "walk_forward_weighted_score"
    model_params = dict(cfg.model_params)
    if selected_model_family == RANDOM_FOREST_MODEL_FAMILY:
        model, scored = fit_walk_forward_random_forest_model(
            featured,
            features=[spec["name"] for spec in features],
            model_id=f"{cfg.run_id}_{selected_model_family}",
            train_periods=train_periods,
            test_periods=test_periods,
            step_periods=step_periods,
            n_estimators=int(model_params.get("n_estimators", 100)),
            max_depth=int(model_params["max_depth"]) if model_params.get("max_depth") is not None else None,
            min_samples_leaf=int(model_params.get("min_samples_leaf", 5)),
            random_state=int(model_params.get("random_state", 42)),
            n_jobs=int(model_params.get("n_jobs", 1)),
        )
    elif selected_model_family in SKLEARN_REGRESSOR_MODEL_FAMILIES:
        model, scored = fit_walk_forward_sklearn_regressor_model(
            featured,
            features=[spec["name"] for spec in features],
            model_id=f"{cfg.run_id}_{selected_model_family}",
            train_periods=train_periods,
            test_periods=test_periods,
            step_periods=step_periods,
            model_family=selected_model_family,
            model_params=model_params,
        )
    else:
        model, scored = fit_walk_forward_weighted_score_model(
            featured,
            features=[spec["name"] for spec in features],
            model_id=f"{cfg.run_id}_{selected_model_family}",
            train_periods=train_periods,
            test_periods=test_periods,
            step_periods=step_periods,
            model_family=selected_model_family,
        )
    model_dir = output_dir / "models"
    persisted_model = write_model_artifacts(model_dir, model, scored)
    metrics = run_signal_backtest(
        scored,
        fee_bps=cfg.fee_bps,
        slippage_bps=cfg.slippage_bps,
        rebalance_periods=int(model_params.get("backtest_rebalance_periods", model_params.get("rebalance_periods", 1))),
        min_score_spread=float(model_params.get("min_score_spread", 0.0)),
    )
    metrics["factor_model"] = persisted_model.model_id
    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True, default=str), encoding="utf-8")

    report_path = output_dir / "report.md"
    regime_path = output_dir / "regime_report.md"
    dashboard_path = output_dir / "dashboard.html"
    manifest_path = output_dir / "manifest.json"
    write_markdown_report(report_path, cfg.run_id, metrics, limitations=["Live Binance public-data pull with walk-forward train/test splits; results are research diagnostics, not investment advice or a production strategy."])
    write_regime_report(regime_path, scored, factor="signal_score")
    write_dashboard(dashboard_path, [report_path, regime_path, Path(persisted_model.signal_output_path)], output_dir / "ledger.jsonl")
    artifact_lineage = {
        **lineage["artifact_lineage"],
        "model_artifact_id": persisted_model.artifact_hash,
        "signal_artifact_id": stable_hash(scored),
    }
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
                "metrics": str(metrics_path),
            },
            source_metadata={
                "source": "binance_usdm_public",
                "symbols": list(cfg.symbols),
                "interval": cfg.interval,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "walk_forward": {"train_periods": train_periods, "test_periods": test_periods, "step_periods": step_periods or test_periods},
                "model_family": selected_model_family,
                "factor_specs": features,
                "public_only": True,
                "artifact_lineage": artifact_lineage,
            },
        ),
    )
    return {"report": report_path, "regime_report": regime_path, "dashboard": dashboard_path, "manifest": manifest_path, "model": model_dir / f"{persisted_model.model_id}.model.json", "signals": Path(persisted_model.signal_output_path), "feature_table": Path(lineage["feature_table"].path), "metrics": metrics_path}
