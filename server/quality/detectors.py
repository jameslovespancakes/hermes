"""Record-level data-quality checks."""

import numpy as np
import pandas as pd

from server.features.geometry import haversine_km


def record_keys(records: pd.DataFrame) -> pd.DataFrame:
    """What makes two records the same delivery: courier, acceptance, area, delivery time, coordinates (~10 m)."""
    keys = records[["courier_id", "accepted_at", "aoi_id", "delivered_at"]].copy()
    keys["lat"], keys["lng"] = records["lat"].round(4), records["lng"].round(4)
    return keys


def duplicate_records(records: pd.DataFrame) -> pd.Series:
    """Re-sent copies of the same delivery scan (lowest id kept); parcels not yet delivered are never copies."""
    keys = record_keys(records)
    order = records["order_id"].argsort(kind="stable")
    repeat = keys.iloc[order].duplicated(keep="first").reindex(records.index)
    return repeat & records["delivered_at"].notna()


def running_bulk_share(records: pd.DataFrame) -> pd.Series:
    """Share of identical timestamps so far on each courier-day (uses only earlier records)."""
    day = records["delivered_at"].dt.normalize()
    shared = (records.duplicated(["courier_id", "delivered_at"], keep=False) & records["delivered_at"].notna()).astype(float)
    frame = pd.DataFrame({"c": records["courier_id"].astype(str), "day": day, "t": records["delivered_at"], "shared": shared})
    at_time = frame.groupby(["c", "day", "t"], dropna=False).agg(n=("shared", "size"), s=("shared", "sum")).reset_index()
    at_time = at_time.sort_values(["c", "day", "t"])
    grouped = at_time.groupby(["c", "day"], dropna=False)
    at_time["share"] = grouped["s"].cumsum() / grouped["n"].cumsum()
    merged = frame.merge(at_time[["c", "day", "t", "share"]], on=["c", "day", "t"], how="left")
    return pd.Series(merged["share"].to_numpy(), index=records.index).fillna(0.0)


def area_reference(records: pd.DataFrame) -> pd.DataFrame:
    """Robust per-area reference point (median destination coordinates)."""
    return records.groupby("aoi_id")[["lat", "lng"]].median()


def offset_from_area_km(records: pd.DataFrame, reference: pd.DataFrame) -> np.ndarray:
    ref = reference.reindex(records["aoi_id"].to_numpy())
    return haversine_km(records["lat"].to_numpy(), records["lng"].to_numpy(), ref["lat"].to_numpy(), ref["lng"].to_numpy())


RECENT_RECEIPTS = 20  # a device's clock is judged on its last 20 uploads


def clock_offset_min(records: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Minutes to add to each record's accept and delivery time when its courier's device clock runs fast.

    A delivery stamped after the server received it is impossible unless the device clock is ahead; the median gap
    over the device's last uploads (only those received before the record is looked up) estimates by how much.
    Gaps within the timestamps' 1-minute resolution are ignored. Without receive times there is nothing to check.
    """
    zero = np.zeros(len(records))
    if "received_at" not in records:
        return zero, zero
    done = records["received_at"].notna() & records["delivered_at"].notna()
    obs = pd.DataFrame(
        {
            "c": records.loc[done, "courier_id"].astype(str).to_numpy(),
            "t": records.loc[done, "received_at"].to_numpy("datetime64[ns]"),
            "lag": ((records.loc[done, "received_at"] - records.loc[done, "delivered_at"]).dt.total_seconds() / 60).to_numpy(),
        }
    ).sort_values("t", kind="stable")
    obs["ahead"] = obs.groupby("c")["lag"].transform(lambda x: x.rolling(RECENT_RECEIPTS, min_periods=3).median())
    obs["shift"] = np.where(obs["ahead"] < -1, obs["ahead"], 0.0)

    def at(when: pd.Series) -> np.ndarray:
        q = pd.DataFrame({"c": records["courier_id"].astype(str).to_numpy(), "t": when.to_numpy("datetime64[ns]"), "i": np.arange(len(records))})
        q = q.dropna(subset=["t"]).sort_values("t", kind="stable")
        m = pd.merge_asof(q, obs[["c", "t", "shift"]], on="t", by="c", allow_exact_matches=False)
        return m.set_index("i")["shift"].reindex(np.arange(len(records))).fillna(0.0).to_numpy()

    return at(records["accepted_at"]), at(records["received_at"].where(done))


def revisit_gap_min(records: pd.DataFrame, quantile: float) -> float:
    """How long couriers normally leave an area and come back the same day for a parcel: the `quantile` of the time
    between a delivery and the courier's previous same-day delivery in that area after the parcel was accepted."""
    done = records.loc[records["delivered_at"].notna()]
    key = done["courier_id"].astype(str) + "|" + done["aoi_id"].astype(str)
    frame = pd.DataFrame(
        {"k": key.to_numpy(), "t": done["delivered_at"].to_numpy("datetime64[ns]"), "a": done["accepted_at"].to_numpy("datetime64[ns]")}
    )
    frame = frame.sort_values(["k", "t"], kind="stable")
    prev = frame.groupby("k")["t"].shift()
    gap = (frame["t"] - prev).dt.total_seconds() / 60
    same_day = prev.dt.normalize() == frame["t"].dt.normalize()
    return float(gap[(prev >= frame["a"]) & (gap > 0) & same_day].quantile(quantile))


# How much each training record counts: courier-days whose records look machine-made count for less.
#
# Two signs, neither about speed: a delivery that shares its exact minute with another of the courier's deliveries
# (no courier hands over two parcels in the same minute; never seen in clean LaDe data), and travel between two
# consecutive drop-offs faster than any courier rides. Each courier-day's share of such records is shrunk towards
# the fleet's typical share with a prior estimated from every courier-day (empirical Bayes), so a day with few
# records moves little; its records then count 1 - that share.
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
