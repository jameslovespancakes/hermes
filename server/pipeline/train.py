"""Train the bundle, evaluate it through the serving predictor, and gate its promotion."""

import importlib.metadata
import json
import pickle
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from server.config import DATA_DIR, DEFAULT_SPLIT, ENSEMBLE_SEEDS, ETA_PARAMS, FIT_SAMPLE, MODEL_STORE, ROUTE_PARAMS, SEED, Split
from server.data.download import sha256_file
from server.data.loading import load_city
from server.data.splits import fit_rows, stop_rows
from server.features.zones import Zones, zone_features
from server.models.bundle import ModelBundle
from server.models.eta import fit_eta
from server.models.later import fit_later_day
from server.models.risk import fit_risk
from server.models.route import add_route_outputs, courier_day_folds, fit_route_folds
from server.models.zone import add_zone_outputs, fit_zone_folds
from server.pipeline.evaluate import evaluate_predictions
from server.pipeline.features import checkpoints, eta_columns, habit_columns, live_table, package_table
from server.pipeline.staleness import STALENESS_EXTRA_COLS, sample_rows, staleness_rows
from server.quality.config import QUALITY, CleanMode, QualityConfig
from server.quality.gating import audited_gate
from server.quality.guard import DataGuard
from server.quality.monitor import fit_baseline
from server.serving.predictor import LiveETAPredictor


def train_bundle(
    records: pd.DataFrame,
    city: str,
    split: Split = DEFAULT_SPLIT,
    *,
    use_guard: bool = True,
    use_staleness: bool = True,
    staleness_events: pd.DataFrame | None = None,
    truth: pd.Series | None = None,
    config: QualityConfig = QUALITY,
    log=print,
) -> ModelBundle:
    """Fit on events before split.fit_end, early-stop on fit_end..stop_end."""
    info: dict = {}
    guard = None
    if use_guard:
        guard = DataGuard(config).fit(records.loc[records["accepted_at"] < split.fit_cutoff])
        records, info["guard"] = guard.clean(records, CleanMode.TRAIN)
    packages = package_table(records, city)
    zones = Zones.fit(packages, split.fit_cutoff)
    live = live_table(packages, split.fit_cutoff)
    live = live.loc[live["s"] < split.stop_cutoff]
    live = pd.concat([live, zone_features(live, packages, zones)], axis=1)
    zone_scores, zone_model, zone_folds = fit_zone_folds(live, split.fit_cutoff)
    live = add_zone_outputs(live, zone_scores)
    route_scores, route_model, route_folds = fit_route_folds(live, split.fit_cutoff)
    live = add_route_outputs(live, route_scores)
    log(f"[{city}] route models fitted")

    columns = eta_columns(habit_columns(packages))
    fit, stop = fit_rows(live, split), stop_rows(live, split)
    eta = fit_eta(fit, stop, columns, seeds=ENSEMBLE_SEEDS)
    later = fit_later_day(fit, stop, columns)
    risk = fit_risk(fit, stop, columns)
    info.update(fit_rows=len(fit), stop_rows=len(stop), eta_rounds=[int(m.best_iteration_) for m in eta.models])
    log(f"[{city}] ETA models: {info['eta_rounds']} rounds on {len(fit):,} rows")

    staleness = None
    if use_staleness:
        fold_of = dict(zip(live["courier_s"] + "|" + live["day"], courier_day_folds(live), strict=False))
        events = staleness_events if staleness_events is not None else checkpoints(records, city, records["delivered_at"].min(), split.stop_cutoff)
        truth = truth if truth is not None else records.set_index("order_id")["delivered_at"]
        rows = staleness_rows(
            records, city, events, truth, split.fit_cutoff, zones, (zone_model, zone_folds), (route_model, route_folds), fold_of, config
        )
        stale_fit = pd.concat([fit, sample_rows(rows, split.fit_cutoff, config.augment_sample)], ignore_index=True)
        stale_stop = pd.concat([stop, rows.loc[(rows["s"] >= split.fit_cutoff) & (rows["s"] < split.stop_cutoff)]], ignore_index=True)
        staleness = fit_eta(stale_fit, stale_stop, columns + STALENESS_EXTRA_COLS)
        info.update(staleness_fit_rows=len(stale_fit))
        log(f"[{city}] staleness-aware model fitted on {len(stale_fit):,} rows")

    return ModelBundle(
        city=city,
        route_model=route_model,
        eta=eta,
        habit_columns=habit_columns(packages),
        trained_through=split.fit_end,
        zones=zones,
        zone_model=zone_model,
        later=later,
        risk=risk,
        staleness=staleness,
        guard=guard,
        monitor=fit_baseline(live, records, split.fit_cutoff, config),
        info=info,
    )


def score_events(predictor: LiveETAPredictor, records: pd.DataFrame, events: pd.DataFrame, cutoff: pd.Timestamp, truth: pd.Series) -> pd.DataFrame:
    """Predictions joined with true remaining minutes, for real packages still pending at each event."""
    out = predictor.predict_events(records, events, cutoff, diagnostics=True)
    out["actual"] = (out["order_id"].map(truth) - pd.to_datetime(out["s"])).dt.total_seconds().to_numpy() / 60
    return out.loc[np.isfinite(out["actual"]) & (out["actual"] > 0)].reset_index(drop=True)


def _load_champion(city: str) -> ModelBundle | None:
    """The stored model, or None if there is none or it uses an older format."""
    path = MODEL_STORE / city / "model.pkl"
    try:
        champion = ModelBundle.load(path)
    except (OSError, TypeError, AttributeError, pickle.UnpicklingError):
        return None
    return champion if vars(champion).get("zones") is not None else None


def train_city(city: str, split: Split = DEFAULT_SPLIT, force: bool = False, log=print) -> dict:
    """Train -> evaluate on the test window -> gate against the stored champion -> store. Returns metrics."""
    started = time.perf_counter()
    records, exclusions = load_city(city, accepted_before=split.data_cutoff)
    truth = records.set_index("order_id")["delivered_at"]
    bundle = train_bundle(records, city, split, log=log)
    candidate = LiveETAPredictor(bundle)
    test = score_events(candidate, records, checkpoints(records, city, split.stop_cutoff, split.data_cutoff), split.fit_cutoff, truth)
    metrics = {
        "city": city,
        "target": "minutes until delivery, re-predicted after every courier delivery",
        "split": {
            "fit": f"events < {split.fit_end} with outcomes < {split.fit_end} (sampled to {FIT_SAMPLE:,})",
            "early_stopping": f"events {split.fit_end}..{split.stop_end} with outcomes < {split.stop_end}",
            "test": f"events {split.stop_end}..{split.test_end}, all outcomes",
            "data_cutoff": f"packages accepted before {split.test_end}",
        },
        "rows": {"packages": len(records), "test_predictions": len(test), "test_packages": int(test["order_id"].nunique())},
        "record_exclusions": exclusions,
        "training": bundle.info,
        **evaluate_predictions(test),
    }
    decision = None
    champion = None if force else _load_champion(city)
    if champion is not None:
        events = checkpoints(records, city, split.fit_cutoff, split.stop_cutoff)
        decision = audited_gate(
            score_events(LiveETAPredictor(champion), records, events, split.fit_cutoff, truth),
            score_events(candidate, records, events, split.fit_cutoff, truth),
            truth,
            split.stop_cutoff,
        )
        metrics["gate"] = decision.__dict__
        log(f"[{city}] gate: {decision.reason} (champion {decision.champion_mae:.2f} vs candidate {decision.challenger_mae:.2f})")
    store = MODEL_STORE / city if decision is None or decision.promote else MODEL_STORE / city / "candidate"
    digest = bundle.save(store / "model.pkl")
    metrics["seconds"] = time.perf_counter() - started
    (store / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str) + "\n", encoding="utf-8")
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "city": city,
        "seed": SEED,
        "fit_sample": FIT_SAMPLE,
        "route_params": ROUTE_PARAMS,
        "eta_params": ETA_PARAMS,
        "eta_columns": bundle.eta.columns,
        "ensemble_seeds": ENSEMBLE_SEEDS,
        "quality_config": QUALITY.__dict__,
        "promoted": decision is None or decision.promote,
        "model_sha256": digest,
        "source_manifest_sha256": sha256_file(DATA_DIR / f"manifest_{city}.json"),
        "versions": {p: importlib.metadata.version(p) for p in ["lightgbm", "numpy", "pandas"]},
        "top_features_by_gain_share": _top_features(bundle.eta.models[0], bundle.eta.columns),
    }
    (store / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")
    log(f"[{city}] test MAE {metrics['overall']['mae']:.2f} min (median {metrics['overall']['median_ae']:.1f}); saved to {store}")
    return metrics


def _top_features(model, columns: list[str], k: int = 15) -> dict:
    gain = model.booster_.feature_importance("gain")
    share = gain / gain.sum()
    return {columns[i]: round(float(share[i]), 4) for i in np.argsort(share)[::-1][:k]}
