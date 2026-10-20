"""Train and evaluate the live ETA model for one city, then store it in server/model_store/<city>/."""

import importlib.metadata
import json
import time
from datetime import datetime, timezone

import numpy as np

from server.config import (DATA_DIR, ETA_PARAMS, FIT_SAMPLE, LIVE_COLS, MODEL_STORE, PACKAGE_COLS, ROUTE_OUTPUT_COLS,
                           ROUTE_PARAMS, SEED, TRANSITION_COLS, Split)
from server.data.download import sha256_file
from server.data.loading import load_city
from server.data.splits import fit_rows, stop_rows, test_rows
from server.models.bundle import ModelBundle
from server.models.eta import fit_eta, predict_eta
from server.models.route import add_route_outputs, fit_route_out_of_fold
from server.pipeline.evaluate import evaluate
from server.pipeline.features import habit_columns, live_table, package_table


def eta_columns(habit_cols: list[str]) -> list[str]:
    return PACKAGE_COLS + habit_cols + LIVE_COLS + TRANSITION_COLS + ROUTE_OUTPUT_COLS


def train_city(city: str, split: Split = Split(), log=print) -> dict:
    """End-to-end: load -> features -> route model (out-of-fold) -> ETA model -> evaluate -> save. Returns metrics."""
    started = time.perf_counter()
    records, exclusions = load_city(city, accepted_before=split.data_cutoff)
    packages = package_table(records, city)
    log(f"[{city}] {len(packages):,} packages; building live queries...")
    live = live_table(packages, split.fit_cutoff)
    log(f"[{city}] {len(live):,} live queries ({time.perf_counter() - started:.0f}s); fitting route model...")
    scores, route_model = fit_route_out_of_fold(live, split.fit_cutoff)
    live = add_route_outputs(live, scores)
    columns = eta_columns(habit_columns(packages))
    fit, stop, test = fit_rows(live, split), stop_rows(live, split), test_rows(live, split)
    log(f"[{city}] fitting ETA model on {len(fit):,} rows...")
    eta_model, schema = fit_eta(fit, stop, columns)
    predicted = predict_eta(eta_model, schema, test, columns)
    metrics = {"city": city, "target": "minutes until delivery, re-predicted after every courier delivery",
               "split": {"fit": f"events < {split.fit_end} with outcomes < {split.fit_end} (sampled to {len(fit):,})",
                         "early_stopping": f"events {split.fit_end}..{split.stop_end} with outcomes < {split.stop_end}",
                         "test": f"events {split.stop_end}..{split.test_end}, all outcomes",
                         "data_cutoff": f"packages accepted before {split.test_end}"},
               "rows": {"packages": len(packages), "live_queries": len(live), "fit": len(fit), "early_stopping": len(stop),
                        "test": len(test), "test_packages": int(test["row"].nunique())},
               "record_exclusions": exclusions, "eta_rounds": int(eta_model.best_iteration_),
               **evaluate(test, predicted), "seconds": time.perf_counter() - started}
    store = MODEL_STORE / city
    bundle = ModelBundle(city=city, route_model=route_model, eta_model=eta_model, eta_columns=columns, eta_schema=schema,
                         habit_columns=habit_columns(packages), trained_through=split.fit_end,
                         info={"split": metrics["split"], "metrics_overall": metrics["overall"]})
    digest = bundle.save(store / "model.pkl")
    store.mkdir(parents=True, exist_ok=True)
    (store / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(), "city": city, "seed": SEED, "fit_sample": FIT_SAMPLE,
                "route_params": ROUTE_PARAMS, "eta_params": ETA_PARAMS, "eta_columns": columns,
                "model_sha256": digest, "source_manifest_sha256": sha256_file(DATA_DIR / f"manifest_{city}.json"),
                "versions": {p: importlib.metadata.version(p) for p in ["lightgbm", "numpy", "pandas"]},
                "top_features_by_gain_share": _top_features(eta_model, columns)}
    (store / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    log(f"[{city}] test MAE {metrics['overall']['mae']:.2f} min (median {metrics['overall']['median_ae']:.1f}); saved to {store}")
    return metrics


def _top_features(model, columns: list[str], k: int = 15) -> dict:
    gain = model.booster_.feature_importance("gain")
    share = gain / gain.sum()
    order = np.argsort(share)[::-1][:k]
    return {columns[i]: round(float(share[i]), 4) for i in order}
