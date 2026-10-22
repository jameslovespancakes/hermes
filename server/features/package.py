"""Per-package inputs known at acceptance: time of day, destination, city-scoped IDs, acceptance GPS geometry."""

import numpy as np
import pandas as pd

from server.config import CATEGORICAL, CATS
from server.features.geometry import haversine_km

META = {"accepted_at": "_accepted_at", "delivered_at": "_delivered_at", "duration_minutes": "_duration_minutes", "order_id": "_order_id"}


def package_features(records: pd.DataFrame, city: str) -> pd.DataFrame:
    """Model-ready package table; outcome columns are kept only as underscore-prefixed metadata."""
    f = records[CATEGORICAL + ["lng", "lat", "accept_gps_lng", "accept_gps_lat"]].copy()
    accepted = records["accepted_at"]
    f["accept_hour"] = accepted.dt.hour
    f["accept_minute_of_day"] = f["accept_hour"] * 60 + accepted.dt.minute + accepted.dt.second / 60
    for name in ["lng", "lat", "accept_gps_lng", "accept_gps_lat"]:
        f[name] = pd.to_numeric(f[name], errors="coerce")
    f.loc[~(f["lng"].between(-180, 180) & f["lat"].between(-90, 90)), ["lng", "lat"]] = np.nan
    gps_ok = (records["accept_gps_at"] <= accepted) & f["accept_gps_lng"].between(-180, 180) & f["accept_gps_lat"].between(-90, 90)
    f.loc[~gps_ok, ["accept_gps_lng", "accept_gps_lat"]] = np.nan
    f["accept_gps_age_minutes"] = ((accepted - records["accept_gps_at"]).dt.total_seconds() / 60).where(gps_ok)
    f["accept_gps_missing"] = (~gps_ok).astype(int)
    f["straight_line_km"] = haversine_km(f["accept_gps_lat"], f["accept_gps_lng"], f["lat"], f["lng"])
    for name in CATEGORICAL:
        f[name] = pd.Categorical(city + ":" + f[name].astype("string").replace("-1", pd.NA))
    f["city"] = pd.Categorical([city] * len(f))
    for column in f.columns.difference(CATS):
        f[column] = f[column].astype("float32")
    for source, target in META.items():
        f[target] = records[source].to_numpy()
    for source, target in (("delivery_gps_lat", "_gps_lat"), ("delivery_gps_lng", "_gps_lng")):
        values = pd.to_numeric(records[source], errors="coerce")
        f[target] = values.where(values.between(-180, 180) & (values != 0)).to_numpy(dtype="float32")
    if "received_at" in records:
        f["_received_at"] = records["received_at"].to_numpy()
    return f
