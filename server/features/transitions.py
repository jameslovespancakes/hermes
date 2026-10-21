"""Courier area-to-area movement habits ("after area X this courier usually goes to area Y").

Counts come from consecutive same-day deliveries completed before `cutoff`. Events before the cutoff
(training events) subtract their own courier-day's transitions, so no event learns from its own day.
"""

import numpy as np
import pandas as pd


def _lookup(series: pd.Series, *keys) -> np.ndarray:
    index = pd.MultiIndex.from_arrays(list(keys)) if len(keys) > 1 else pd.Index(keys[0])
    return series.reindex(index).fillna(0).to_numpy()


def add_transitions(live: pd.DataFrame, packages: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    """Add p_courier_next_area, p_all_next_area, support, and within-event ranks to `live` (returns a copy)."""
    live = live.copy()
    aoi = packages["aoi_id"].astype(str).to_numpy()
    cur_row = live["cur_row"].to_numpy()
    live["cur_aoi"] = np.where(cur_row >= 0, aoi[np.maximum(cur_row, 0)], "nan")
    done = packages.loc[packages["_delivered_at"] < cutoff].sort_values(["courier_id", "_delivered_at"])
    prev = done.groupby("courier_id", observed=True).shift()
    same_day = done["_delivered_at"].dt.normalize() == prev["_delivered_at"].dt.normalize()
    moves = pd.DataFrame(
        {
            "c": done["courier_id"].astype(str),
            "a": prev["aoi_id"].astype(str),
            "b": done["aoi_id"].astype(str),
            "day": done["_delivered_at"].dt.strftime("%m-%d"),
        }
    ).loc[same_day]
    cab, ca = moves.groupby(["c", "a", "b"]).size(), moves.groupby(["c", "a"]).size()
    gab, ga = moves.groupby(["a", "b"]).size(), moves.groupby("a").size()
    own_cab, own_ca = moves.groupby(["c", "day", "a", "b"]).size(), moves.groupby(["c", "day", "a"]).size()
    own_gab, own_ga = own_cab.groupby(level=["day", "a", "b"]).sum(), own_ca.groupby(level=["day", "a"]).sum()
    c, cur, item, day = live["courier_s"], live["cur_aoi"].astype(str), live["aoi_id"].astype(str), live["day"]
    before = (live["s"] < cutoff.to_datetime64()).to_numpy()
    n_cab = _lookup(cab, c, cur, item) - np.where(before, _lookup(own_cab, c, day, cur, item), 0)
    n_ca = _lookup(ca, c, cur) - np.where(before, _lookup(own_ca, c, day, cur), 0)
    n_gab = _lookup(gab, cur, item) - np.where(before, _lookup(own_gab, day, cur, item), 0)
    n_ga = _lookup(ga, cur) - np.where(before, _lookup(own_ga, day, cur), 0)
    live["p_courier_next_area"] = np.where(n_ca > 0, n_cab / np.maximum(n_ca, 1), np.nan).astype("float32")
    live["p_all_next_area"] = np.where(n_ga > 0, n_gab / np.maximum(n_ga, 1), np.nan).astype("float32")
    live["courier_transition_support"] = n_ca.astype("float32")
    spread = (live["n_pending"] - 1).clip(lower=1)
    for column in ["p_courier_next_area", "p_all_next_area"]:
        live[column + "_rank"] = (live.groupby("event")[column].rank(method="first", ascending=False) - 1) / spread
    return live
