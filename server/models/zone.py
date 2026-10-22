"""Next-zone model: which pending zone the courier visits next (out-of-fold by courier-day in training)."""

import lightgbm as lgb
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from server.config import ROUTE_FOLDS, SEED, THREADS
from server.models.route import courier_day_folds

ZONE_INPUTS = [
    "dist_from_courier_gps_km",
    "dist_from_courier_km",
    "dist_from_depot_km",
    "zone_is_current",
    "zone_pending",
    "p_zone_next_all",
    "p_zone_next_courier",
    "zone_usual_clock_rel_now",
    "elapsed_min",
    "hab_ca_rank_now",
    "hab_ca_rel_now",
    "aoi_deliveries_60m",
    "p_courier_next_area",
    "p_all_next_area",
    "n_pending",
    "clock_s",
]
NEAREST = ["dist_from_courier_gps_km", "dist_from_courier_km", "dist_from_depot_km", "elapsed_min", "hab_ca_rank_now", "hab_ca_rel_now"]
PARAMS = {"n_estimators": 400, "learning_rate": 0.05, "num_leaves": 127, "min_child_samples": 50, "colsample_bytree": 0.8}


def zone_table(live: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """One row per (moment, pending zone) and the zone-row index of every live row."""
    key = pd.factorize(live["event"].astype(np.int64) * 100_000 + live["zone_id"].astype(np.int64))[0]
    agg = {c: ("min" if c in NEAREST else "first") for c in ZONE_INPUTS}
    agg.update({"event": "first", "s": "first", "courier_s": "first", "day": "first"})
    if "_delivered_at" in live:
        agg["_delivered_at"] = "max"
    table = live.assign(_zk=key).groupby("_zk").agg(agg)
    if "true_pos" in live:
        table["label"] = 0
        table.loc[np.unique(key[(live["true_pos"] == 0).to_numpy()]), "label"] = 1
    return table, key


def _fit(rows: pd.DataFrame) -> lgb.LGBMClassifier:
    model = lgb.LGBMClassifier(**PARAMS, random_state=SEED, n_jobs=THREADS, verbosity=-1)
    with threadpool_limits(limits=THREADS):
        return model.fit(rows[ZONE_INPUTS], rows["label"])


def _proba(model, rows: pd.DataFrame) -> np.ndarray:
    with threadpool_limits(limits=THREADS):
        return model.predict_proba(rows[ZONE_INPUTS])[:, 1]


def fit_zone_folds(live: pd.DataFrame, cutoff: pd.Timestamp) -> tuple[np.ndarray, lgb.LGBMClassifier, list]:
    """Out-of-fold next-zone probability per live row, the full model, and the per-fold models."""
    table, key = zone_table(live)
    last = table.groupby("event")["_delivered_at"].transform("max")
    trainable = ((table["s"] < cutoff) & (last < cutoff)).to_numpy()
    fold = courier_day_folds(table)
    prob = np.full(len(table), np.nan)
    folds = []
    for k in range(ROUTE_FOLDS):
        folds.append(_fit(table.loc[trainable & (fold != k)]))
        held = trainable & (fold == k)
        prob[held] = _proba(folds[k], table.loc[held])
    full = _fit(table.loc[trainable])
    prob[~trainable] = _proba(full, table.loc[~trainable])
    return prob[key], full, folds


def predict_zone(model, live: pd.DataFrame) -> np.ndarray:
    table, key = zone_table(live)
    return _proba(model, table)[key]


def add_zone_outputs(live: pd.DataFrame, prob: np.ndarray) -> pd.DataFrame:
    live = live.copy()
    live["p_zone_model"] = prob.astype("float32")
    live["p_zone_model_rank"] = (live.groupby("event")["p_zone_model"].rank(ascending=False, method="dense") - 1).astype("float32")
    return live
