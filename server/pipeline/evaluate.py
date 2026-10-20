"""Evaluation metrics: ETA error overall and by time remaining; route-order quality per event."""

import numpy as np
import pandas as pd

from server.config import HORIZONS


def error_summary(actual: np.ndarray, predicted: np.ndarray) -> dict:
    err = np.abs(np.asarray(actual) - np.asarray(predicted))
    return {"n": int(len(err)), "mae": float(err.mean()), "median_ae": float(np.median(err)),
            "within_30_pct": float(np.mean(err <= 30) * 100)}


def by_time_remaining(actual: np.ndarray, predicted: np.ndarray) -> dict:
    out = {}
    for label, lo, hi in HORIZONS:
        mask = ((actual > lo) & (actual <= hi)) if lo else (actual <= hi)
        if mask.any():
            out[label] = error_summary(actual[mask], predicted[mask])
    return out


def route_hit_rates(rows: pd.DataFrame, score_col: str = "route_score") -> tuple[float, float]:
    """% of events (3+ pending) whose true next stop is predicted first; share of the true next 3 in the top 3."""
    sub = rows.loc[rows["n_pending"] >= 3]
    true_rank = sub.groupby("event")["remaining_min"].rank(method="first") - 1
    pred_rank = sub.groupby("event")[score_col].rank(method="first") - 1
    next_stop = ((true_rank == 0) & (pred_rank == 0)).groupby(sub["event"]).sum().mean()
    next_three = ((true_rank < 3) & (pred_rank < 3)).groupby(sub["event"]).sum().div(3).mean()
    return float(next_stop * 100), float(next_three * 100)


def route_order_agreement(rows: pd.DataFrame, score_col: str = "route_score", min_pending: int = 3) -> float:
    """Mean per-event Spearman correlation between predicted and true delivery order."""
    sub = rows.loc[rows["n_pending"] >= min_pending, ["event", "remaining_min", score_col]].dropna()
    g = sub.groupby("event")
    frame = pd.DataFrame({"m": sub["event"].to_numpy(), "x": g["remaining_min"].rank().to_numpy(), "y": g[score_col].rank().to_numpy()})
    frame["x"] -= frame.groupby("m")["x"].transform("mean")
    frame["y"] -= frame.groupby("m")["y"].transform("mean")
    sums = frame.assign(xy=frame.x * frame.y, xx=frame.x ** 2, yy=frame.y ** 2).groupby("m")[["xy", "xx", "yy"]].sum()
    ok = (sums.xx > 0) & (sums.yy > 0)
    return float((sums.xy[ok] / np.sqrt(sums.xx[ok] * sums.yy[ok])).mean())


def evaluate(test: pd.DataFrame, predicted: np.ndarray) -> dict:
    actual = test["remaining_min"].to_numpy()
    next_stop, next_three = route_hit_rates(test)
    return {"overall": error_summary(actual, predicted), "by_time_remaining": by_time_remaining(actual, predicted),
            "route": {"next_stop_pct": next_stop, "next3_pct": next_three, "order_agreement_spearman": route_order_agreement(test)}}
