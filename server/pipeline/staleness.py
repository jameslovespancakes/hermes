"""Training data for the staleness-aware ETA model: the same history with simulated upload delays.

A random share of courier-days gets an upload lag (event time unchanged, receive time later), so the model sees
couriers whose feeds run behind and learns from `feed_age_min` / `upload_lag_min`. Labels are the true remaining
times; route features come from the fold model that never saw that courier-day.
"""

import numpy as np
import pandas as pd

from server.config import SEED
from server.models.route import ROUTE_INPUT_COLS, add_route_outputs, predict_route
from server.pipeline.features import live_table, package_table
from server.quality.config import QUALITY, QualityConfig

STALENESS_EXTRA_COLS = ["feed_age_min", "upload_lag_min"]


def delayed_uploads(records: pd.DataFrame, share: float, min_lag: float, max_lag: float, seed: int = 31) -> pd.DataFrame:
    """Copy of `records` where a random share of courier-days uploads deliveries late (received_at = event + lag)."""
    out = records.copy()
    keys = out["courier_id"].astype(str) + "|" + out["delivered_at"].dt.strftime("%m-%d")
    unique = np.sort(keys.unique())
    rng = np.random.default_rng(seed)
    lag_minutes = np.where(rng.uniform(size=len(unique)) < share, rng.uniform(min_lag, max_lag, len(unique)), 0.0)
    lag = pd.to_timedelta(keys.map(dict(zip(unique, lag_minutes, strict=True))).to_numpy(), unit="m")
    base = out["received_at"] if "received_at" in out else out["delivered_at"]
    out["received_at"] = base + lag
    return out


def staleness_rows(
    records: pd.DataFrame,
    city: str,
    events: pd.DataFrame,
    truth: pd.Series,
    cutoff: pd.Timestamp,
    route_model,
    fold_models: list,
    fold_of: dict,
    config: QualityConfig = QUALITY,
) -> pd.DataFrame:
    """Live rows from a delay-augmented copy of `records`, labelled with TRUE remaining minutes.

    Ghost rows (delivered but not yet received) and non-real records are model inputs only, never targets.
    """
    delayed = delayed_uploads(records, config.augment_share, config.augment_min_lag_min, config.augment_max_lag_min)
    packages = package_table(delayed, city)
    live = live_table(packages, cutoff, events)
    keys = (live["courier_s"] + "|" + live["day"]).map(fold_of)
    scores = predict_route(route_model, live)
    for k, model in enumerate(fold_models):
        mask = (keys == k).to_numpy()
        if mask.any():
            scores[mask] = model.predict(live.loc[mask, ROUTE_INPUT_COLS])
    live = add_route_outputs(live, scores)
    true_delivered = live["_order_id"].map(truth)
    live["remaining_min"] = ((true_delivered - live["s"]).dt.total_seconds() / 60).astype("float32")
    live["_delivered_at"] = true_delivered.to_numpy()
    return live.loc[(true_delivered.notna() & (live["remaining_min"] > 0)).to_numpy()]


def sample_rows(rows: pd.DataFrame, cutoff: pd.Timestamp, n: int) -> pd.DataFrame:
    """Fit-period staleness rows with outcomes known by the cutoff, capped at n (seeded)."""
    fit = rows.loc[(rows["s"] < cutoff) & (rows["_delivered_at"] < cutoff)]
    return fit.sample(n=min(n, len(fit)), random_state=SEED)
