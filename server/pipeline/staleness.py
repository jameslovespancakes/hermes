"""Training rows for the staleness-aware model: history replayed with simulated upload delays, true labels."""

import numpy as np
import pandas as pd

from server.config import SEED
from server.features.zones import Zones, zone_features
from server.models.route import add_route_outputs, predict_route
from server.models.zone import add_zone_outputs, predict_zone
from server.pipeline.features import live_table, package_table
from server.quality.config import QUALITY, QualityConfig

STALENESS_EXTRA_COLS = ["feed_age_min", "upload_lag_min"]


def delayed_uploads(records: pd.DataFrame, share: float, min_lag: float, max_lag: float, seed: int = 31) -> pd.DataFrame:
    """A random share of courier-days uploads deliveries late (received_at = event time + lag)."""
    out = records.copy()
    keys = out["courier_id"].astype(str) + "|" + out["delivered_at"].dt.strftime("%m-%d")
    unique = np.sort(keys.unique())
    rng = np.random.default_rng(seed)
    lag_minutes = np.where(rng.uniform(size=len(unique)) < share, rng.uniform(min_lag, max_lag, len(unique)), 0.0)
    lag = pd.to_timedelta(keys.map(dict(zip(unique, lag_minutes, strict=True))).to_numpy(), unit="m")
    out["received_at"] = (out["received_at"] if "received_at" in out else out["delivered_at"]) + lag
    return out


def by_fold(live: pd.DataFrame, fold_of: dict, full, folds: list, predict) -> np.ndarray:
    """Predictions from the fold model that never saw the row's courier-day (full model otherwise)."""
    keys = (live["courier_s"] + "|" + live["day"]).map(fold_of).to_numpy()
    out = np.empty(len(live))
    for k, model in [(np.nan, full), *enumerate(folds)]:
        mask = np.isnan(keys) if k is np.nan else keys == k
        if mask.any():
            out[mask] = predict(model, live.loc[mask])
    return out


def staleness_rows(
    records: pd.DataFrame,
    city: str,
    events: pd.DataFrame,
    truth: pd.Series,
    cutoff: pd.Timestamp,
    zones: Zones,
    zone_models: tuple,
    route_models: tuple,
    fold_of: dict,
    config: QualityConfig = QUALITY,
) -> pd.DataFrame:
    delayed = delayed_uploads(records, config.augment_share, config.augment_min_lag_min, config.augment_max_lag_min)
    packages = package_table(delayed, city)
    live = live_table(packages, cutoff, events)
    live = pd.concat([live, zone_features(live, packages, zones)], axis=1)
    live = add_zone_outputs(live, by_fold(live, fold_of, *zone_models, predict_zone))
    live = add_route_outputs(live, by_fold(live, fold_of, *route_models, predict_route))
    delivered = live["_order_id"].map(truth)
    live["remaining_min"] = ((delivered - live["s"]).dt.total_seconds() / 60).astype("float32")
    live["_delivered_at"] = delivered.to_numpy()
    return live.loc[(delivered.notna() & (live["remaining_min"] > 0)).to_numpy()]


def sample_rows(rows: pd.DataFrame, cutoff: pd.Timestamp, n: int) -> pd.DataFrame:
    fit = rows.loc[(rows["s"] < cutoff) & (rows["_delivered_at"] < cutoff)]
    return fit.sample(n=min(n, len(fit)), random_state=SEED)
