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


def bulk_scanned_courier_days(records: pd.DataFrame, min_share: float) -> pd.Series:
    """Rows on courier-days where at least `min_share` of deliveries share an identical timestamp with another."""
    day = records["delivered_at"].dt.normalize()
    shared = records.duplicated(["courier_id", "delivered_at"], keep=False) & records["delivered_at"].notna()
    share = shared.groupby([records["courier_id"], day]).transform("mean")
    return (share >= min_share).fillna(False)


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
