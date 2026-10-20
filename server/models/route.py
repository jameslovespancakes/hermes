"""Route-order model: predicts each pending package's position in the courier's upcoming delivery order.

Training targets are true positions within each event (known only afterwards). For training-period events
the predictions are out-of-fold by courier-day, so the ETA model never learns from a route prediction that
saw its own label. Other events use a model fitted on all eligible training events.
"""

import lightgbm as lgb
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from server.config import ROUTE_FOLDS, ROUTE_INPUT_COLS, ROUTE_PARAMS, SEED, THREADS


def _fit(rows: pd.DataFrame) -> lgb.LGBMRegressor:
    model = lgb.LGBMRegressor(**ROUTE_PARAMS, random_state=SEED, n_jobs=THREADS, verbosity=-1)
    with threadpool_limits(limits=THREADS):
        model.fit(rows[ROUTE_INPUT_COLS], rows["true_pos"])
    return model


def courier_day_folds(live: pd.DataFrame) -> np.ndarray:
    """Fold id per row; every courier-day stays in one fold (deterministic)."""
    group = pd.factorize(live["courier_s"] + "|" + live["day"])[0]
    return np.random.default_rng(SEED).integers(0, ROUTE_FOLDS, group.max() + 1)[group]


def trainable_events(live: pd.DataFrame, cutoff: pd.Timestamp) -> np.ndarray:
    """Rows of events before the cutoff whose whole pending set was delivered before the cutoff."""
    cutoff = cutoff.to_datetime64()
    event_last_delivery = live.groupby("event")["_delivered_at"].transform("max")
    return ((live["s"] < cutoff) & (event_last_delivery < cutoff) & (live["n_pending"] >= 2)).to_numpy()


def fit_route_out_of_fold(live: pd.DataFrame, cutoff: pd.Timestamp) -> tuple[np.ndarray, lgb.LGBMRegressor]:
    """Route scores for every row (out-of-fold where trainable) and the full model for later events."""
    trainable = trainable_events(live, cutoff)
    fold = courier_day_folds(live)
    scores = np.full(len(live), np.nan)
    for k in range(ROUTE_FOLDS):
        held = trainable & (fold == k)
        scores[held] = _fit(live.loc[trainable & (fold != k)]).predict(live.loc[held, ROUTE_INPUT_COLS])
    full = _fit(live.loc[trainable])
    scores[~trainable] = full.predict(live.loc[~trainable, ROUTE_INPUT_COLS])
    return scores, full


def predict_route(model: lgb.LGBMRegressor, live: pd.DataFrame) -> np.ndarray:
    with threadpool_limits(limits=THREADS):
        return model.predict(live[ROUTE_INPUT_COLS])


def add_route_outputs(live: pd.DataFrame, scores: np.ndarray) -> pd.DataFrame:
    """route_score, route_ahead (predicted packages before this one), and route_ahead_x_pace (minutes)."""
    live = live.copy()
    live["route_score"] = scores
    live["route_ahead"] = (live.groupby("event")["route_score"].rank(method="first") - 1).astype("float32")
    pace = live["pace_today_min"].fillna(live["hab_courier_usual_shift_hours"] * 60 / live["hab_courier_usual_deliveries_per_day"])
    live["route_ahead_x_pace"] = ((live["route_ahead"] + 1) * pace).astype("float32")
    return live
