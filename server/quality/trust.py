"""How much each training record counts: courier-days whose records look machine-made count for less.

Two signs, neither about speed: a delivery that shares its exact minute with another of the courier's deliveries
(no courier hands over two parcels in the same minute; never seen in clean LaDe data), and travel between two
consecutive drop-offs faster than any courier rides. Each courier-day's share of such records is shrunk towards
the fleet's typical share with a prior estimated from every courier-day (empirical Bayes), so a day with few
records moves little; its records then count 1 - that share.
"""

import numpy as np
import pandas as pd

from server.features.geometry import haversine_km

MAX_SPEED_KMH = 60.0
MIN_LEG_KM = 1.0


def suspicious(records: pd.DataFrame) -> pd.Series:
    """Per delivered record: shares its minute with another of the courier's deliveries, or implies impossible travel."""
    done = records.loc[records["delivered_at"].notna(), ["courier_id", "delivered_at", "lat", "lng"]]
    shared = done.duplicated(["courier_id", "delivered_at"], keep=False)
    order = done.sort_values(["courier_id", "delivered_at"], kind="stable")
    prev = order.groupby("courier_id").shift()
    same_day = prev["delivered_at"].dt.normalize() == order["delivered_at"].dt.normalize()
    km = haversine_km(prev["lat"].to_numpy(), prev["lng"].to_numpy(), order["lat"].to_numpy(), order["lng"].to_numpy())
    hours = (order["delivered_at"] - prev["delivered_at"]).dt.total_seconds().to_numpy() / 3600
    with np.errstate(divide="ignore", invalid="ignore"):
        jump = same_day.to_numpy() & (km > MIN_LEG_KM) & (km / hours > MAX_SPEED_KMH)
    out = pd.Series(False, index=records.index)
    out.loc[done.index] = shared.to_numpy()
    out.loc[order.index] |= jump
    return out


def record_weights(records: pd.DataFrame) -> pd.Series:
    """1 - each courier-day's shrunk share of suspicious records (1 everywhere when nothing looks suspicious)."""
    flag = suspicious(records).astype(float)
    day = records["delivered_at"].dt.normalize()
    stats = flag.groupby([records["courier_id"], day]).agg(["sum", "size"])
    share = stats["sum"] / stats["size"]
    mean, var = float(share.mean()), float(share.var())
    if mean == 0.0 or var == 0.0:
        return pd.Series(1.0, index=records.index)
    strength = max(mean * (1 - mean) / var - 1, 0.0)
    shrunk = (stats["sum"] + mean * strength) / (stats["size"] + strength)
    keys = pd.MultiIndex.from_arrays([records["courier_id"], day])
    return pd.Series(1 - shrunk.reindex(keys).fillna(mean).to_numpy(), index=records.index)
