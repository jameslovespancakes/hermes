"""Courier area-to-area movement habits ("after area X this courier usually goes to area Y")."""

import numpy as np
import pandas as pd


def _day(times) -> np.ndarray:
    return np.asarray(times, dtype="datetime64[ns]").astype("datetime64[D]").view(np.int64)


def _before(move_keys: np.ndarray, move_days: np.ndarray, query_keys: np.ndarray, day: np.ndarray) -> np.ndarray:
    """Per query row: moves with the same integer key on days strictly before its `day`."""
    daily = pd.DataFrame({"k": move_keys, "d": move_days}).groupby(["k", "d"]).size().rename("n").reset_index()
    daily["n"] = daily.groupby("k")["n"].cumsum()
    q = pd.DataFrame({"k": query_keys, "d": day, "i": np.arange(len(day))}).sort_values("d", kind="stable")
    merged = pd.merge_asof(q, daily.sort_values("d", kind="stable"), on="d", by="k", allow_exact_matches=False)
    return merged.set_index("i")["n"].reindex(np.arange(len(day))).fillna(0).to_numpy()


def add_transitions(live: pd.DataFrame, packages: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    """Add p_courier_next_area, p_all_next_area, support, and within-event ranks, from moves on earlier days before `cutoff` (returns a copy)."""
    live = live.copy()
    aoi = packages["aoi_id"].astype(str).to_numpy()
    cur_row = live["cur_row"].to_numpy()
    live["cur_aoi"] = np.where(cur_row >= 0, aoi[np.maximum(cur_row, 0)], "nan")
    done = packages.loc[packages["_delivered_at"] < cutoff].sort_values(["courier_id", "_delivered_at"])
    prev = done.groupby("courier_id", observed=True).shift()
    same_day = done["_delivered_at"].dt.normalize() == prev["_delivered_at"].dt.normalize()
    moves = done.loc[same_day]
    courier, couriers = pd.factorize(np.r_[moves["courier_id"].astype(str).to_numpy(), live["courier_s"].to_numpy()])
    area, areas = pd.factorize(
        np.r_[
            prev.loc[same_day, "aoi_id"].astype(str).to_numpy(),
            moves["aoi_id"].astype(str).to_numpy(),
            live["cur_aoi"].astype(str).to_numpy(),
            live["aoi_id"].astype(str).to_numpy(),
        ]
    )
    m, q, n = len(moves), len(live), np.int64(len(areas))
    a, b = area[:m].astype(np.int64), area[m : 2 * m].astype(np.int64)
    qa, qb = area[2 * m : 2 * m + q].astype(np.int64), area[2 * m + q :].astype(np.int64)
    c, qc = courier[:m].astype(np.int64) * n * n, courier[m:].astype(np.int64) * n * n
    d, day = _day(moves["_delivered_at"]), np.minimum(_day(live["s"]), _day([cutoff])[0])
    n_cab, n_ca = _before(c + a * n + b, d, qc + qa * n + qb, day), _before(c + a, d, qc + qa, day)
    n_gab, n_ga = _before(a * n + b, d, qa * n + qb, day), _before(a, d, qa, day)
    live["p_courier_next_area"] = np.where(n_ca > 0, n_cab / np.maximum(n_ca, 1), np.nan).astype("float32")
    live["p_all_next_area"] = np.where(n_ga > 0, n_gab / np.maximum(n_ga, 1), np.nan).astype("float32")
    live["courier_transition_support"] = n_ca.astype("float32")
    spread = (live["n_pending"] - 1).clip(lower=1)
    for column in ["p_courier_next_area", "p_all_next_area"]:
        live[column + "_rank"] = (live.groupby("event")[column].rank(method="first", ascending=False) - 1) / spread
    return live
