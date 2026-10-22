"""Live context at each moment: the area right now, the courier's recent days, real GPS position, and depot."""

import numpy as np
import pandas as pd

from server.features.geometry import haversine_km

MINUTE = np.timedelta64(1, "m")
FAR_KM = 0.5


def visible_at(packages: pd.DataFrame) -> pd.Series:
    return packages["_received_at"] if "_received_at" in packages else packages["_delivered_at"]


def courier_key(values: pd.Series) -> np.ndarray:
    codes, uniques = pd.factorize(values.astype(str))
    return pd.Index(uniques).str.split(":").str[-1].to_numpy()[codes]


def rank_in_event(live: pd.DataFrame, values) -> np.ndarray:
    rank = pd.Series(values, index=live.index).groupby(live["event"]).rank(method="first") - 1
    return (rank / (live["n_pending"] - 1).clip(lower=1)).astype("float32").to_numpy()


def window_stats(row_keys, row_times, event_keys, event_times, event_values, windows) -> dict[str, np.ndarray]:
    """Per row: count and mean value of same-key events in (t - w, t] for each window, plus the count up to t."""
    n = len(row_times)
    out = {"n_all": np.zeros(n, np.float32)}
    for w in windows:
        out[f"n_{w}"] = np.zeros(n, np.float32)
        out[f"mean_{w}"] = np.full(n, np.nan, np.float32)
    events = pd.DataFrame({"k": event_keys, "t": event_times, "v": event_values})
    events = events.loc[events["k"].isin(set(row_keys))].sort_values(["k", "t"])
    lookup = {k: (g["t"].to_numpy(), np.concatenate([[0.0], np.cumsum(g["v"].to_numpy(dtype=float))])) for k, g in events.groupby("k", sort=False)}
    rows = pd.DataFrame({"k": row_keys, "t": row_times, "i": np.arange(n)})
    for k, g in rows.groupby("k", sort=False):
        if k not in lookup:
            continue
        times, cumsum = lookup[k]
        t, i = g["t"].to_numpy(), g["i"].to_numpy()
        hi = np.searchsorted(times, t, "right")
        out["n_all"][i] = hi
        for w in windows:
            lo = np.searchsorted(times, t - w * MINUTE, "right")
            count = hi - lo
            out[f"n_{w}"][i] = count
            with np.errstate(invalid="ignore", divide="ignore"):
                out[f"mean_{w}"][i] = np.where(count > 0, (cumsum[hi] - cumsum[lo]) / np.maximum(count, 1), np.nan)
    return out


def area_now(live: pd.DataFrame, packages: pd.DataFrame) -> pd.DataFrame:
    accepted = packages["_accepted_at"].to_numpy("datetime64[ns]")
    seen = visible_at(packages).to_numpy("datetime64[ns]")
    duration = (packages["_delivered_at"].to_numpy("datetime64[ns]") - accepted) / MINUTE
    s, rows = live["s"].to_numpy("datetime64[ns]"), live["row"].to_numpy()
    done = ~np.isnat(seen)
    out = {}
    for level, column in (("aoi", "aoi_id"), ("region", "region_id"), ("city", None)):
        keys = packages[column].astype(str).to_numpy() if column else np.full(len(packages), "all")
        delivered = window_stats(keys[rows], s, keys[done], seen[done], duration[done], (60, 180))
        taken = window_stats(keys[rows], s, keys, accepted, np.ones(len(keys)), (60,))
        out[f"{level}_deliveries_60m"] = delivered["n_60"]
        out[f"{level}_recent_duration_180m"] = delivered["mean_180"]
        out[f"{level}_accepted_60m"] = taken["n_60"]
        out[f"{level}_pending_now"] = taken["n_all"] - delivered["n_all"]
    frame = pd.DataFrame(out, index=live.index)
    usual = live["hab_ca_typical_duration"].replace(0, np.nan) if "hab_ca_typical_duration" in live else np.nan
    frame["aoi_recent_vs_usual"] = (frame["aoi_recent_duration_180m"] / usual).astype("float32")
    return frame


def courier_recent(live: pd.DataFrame, packages: pd.DataFrame) -> pd.DataFrame:
    delivered = pd.to_datetime(packages["_delivered_at"])
    days = pd.DataFrame(
        {
            "c": courier_key(packages["courier_id"]),
            "day": delivered.dt.normalize(),
            "t": delivered,
            "duration": (delivered - pd.to_datetime(packages["_accepted_at"])).dt.total_seconds() / 60,
        }
    ).dropna()
    days = days.loc[days["c"].isin(_moments(live)[0])]
    per_day = days.groupby(["c", "day"]).agg(n=("t", "size"), first=("t", "min"), last=("t", "max"), duration=("duration", "median")).reset_index()
    per_day["pace"] = (per_day["last"] - per_day["first"]).dt.total_seconds() / 60 / (per_day["n"] - 1).clip(lower=1)
    per_day = per_day.sort_values(["c", "day"])
    rolling = per_day.groupby("c")[["n", "pace", "duration"]].transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean())
    lookup = rolling.set_axis(per_day["c"] + "|" + per_day["day"].astype(str))
    key = pd.Series(courier_key(live["courier_s"]), index=live.index) + "|" + pd.to_datetime(live["s"]).dt.normalize().astype(str)
    out = pd.DataFrame(index=live.index)
    for source, name in (("n", "courier_3d_deliveries"), ("pace", "courier_3d_pace_min"), ("duration", "courier_3d_package_min")):
        out[name] = key.map(lookup[source]).astype("float32").to_numpy()
    out["pace_vs_3d"] = (live["pace_today_min"] / out["courier_3d_pace_min"]).astype("float32")
    return out


def _moments(live: pd.DataFrame) -> tuple[set, set]:
    return set(courier_key(live["courier_s"])), set(pd.to_datetime(live["s"]).dt.normalize().unique())


def _today_asof(live: pd.DataFrame, frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Latest same-day value of `columns` per courier at each live moment (frame has c, t, day)."""
    moments = pd.DataFrame({"c": courier_key(live["courier_s"]), "t": live["s"].to_numpy("datetime64[ns]"), "i": np.arange(len(live))})
    frame = frame.sort_values("t", kind="stable").drop_duplicates(["c", "t"], keep="last")
    merged = pd.merge_asof(moments.sort_values("t", kind="stable"), frame, on="t", by="c")
    merged = merged.loc[merged["day"] == merged["t"].dt.normalize()]
    out = pd.DataFrame(np.nan, index=np.arange(len(live)), columns=columns)
    out.loc[merged["i"].to_numpy(), columns] = merged[columns].to_numpy()
    return out


def courier_gps(live: pd.DataFrame, packages: pd.DataFrame) -> pd.DataFrame:
    cur = live["cur_row"].to_numpy()
    last = np.maximum(cur, 0)
    has = cur >= 0

    def at_last(values) -> np.ndarray:
        return np.where(has, np.asarray(values)[last], np.nan)

    gps_lat, gps_lng = at_last(packages["_gps_lat"]), at_last(packages["_gps_lng"])
    rows = live["row"].to_numpy()
    out = pd.DataFrame(index=live.index)
    out["last_confirm_km_from_address"] = haversine_km(gps_lat, gps_lng, at_last(packages["lat"]), at_last(packages["lng"])).astype("float32")
    out["dist_from_courier_gps_km"] = haversine_km(gps_lat, gps_lng, packages["lat"].to_numpy()[rows], packages["lng"].to_numpy()[rows]).astype(
        "float32"
    )
    out["dist_rank_gps"] = rank_in_event(live, out["dist_from_courier_gps_km"].fillna(1e9).to_numpy())
    far = haversine_km(packages["_gps_lat"], packages["_gps_lng"], packages["lat"], packages["lng"]) > FAR_KM
    seen = pd.to_datetime(visible_at(packages))
    confirmations = (
        pd.DataFrame({"c": courier_key(packages["courier_id"]), "t": seen, "far": far.astype(float)})
        .dropna(subset=["t"])
        .sort_values("t", kind="stable")
    )
    confirmations["day"] = confirmations["t"].dt.normalize()
    couriers, days = _moments(live)
    confirmations = confirmations.loc[confirmations["c"].isin(couriers) & confirmations["day"].isin(days)]
    group = confirmations.groupby(["c", "day"])
    confirmations["share"] = group["far"].cumsum() / (group.cumcount() + 1)
    out["far_confirm_share_today"] = _today_asof(live, confirmations, ["share"])["share"].astype("float32").to_numpy()
    return out


def depot(live: pd.DataFrame, packages: pd.DataFrame) -> pd.DataFrame:
    accepted = pd.to_datetime(packages["_accepted_at"])
    pickups = pd.DataFrame(
        {"c": courier_key(packages["courier_id"]), "t": accepted, "lat": packages["accept_gps_lat"], "lng": packages["accept_gps_lng"]}
    ).dropna()
    pickups["day"] = pickups["t"].dt.normalize()
    couriers, days = _moments(live)
    pickups = pickups.loc[pickups["c"].isin(couriers) & pickups["day"].isin(days)].sort_values("t", kind="stable")
    group = pickups.groupby(["c", "day"])
    pickups["dlat"] = group["lat"].transform(lambda x: x.expanding().median())
    pickups["dlng"] = group["lng"].transform(lambda x: x.expanding().median())
    where = _today_asof(live, pickups, ["dlat", "dlng"])
    rows = live["row"].to_numpy()
    out = pd.DataFrame(index=live.index)
    out["dist_from_depot_km"] = haversine_km(
        where["dlat"].to_numpy(), where["dlng"].to_numpy(), packages["lat"].to_numpy()[rows], packages["lng"].to_numpy()[rows]
    ).astype("float32")
    out["dist_rank_depot"] = rank_in_event(live, out["dist_from_depot_km"].fillna(1e9).to_numpy())
    position = np.where((live["n_done_today"] == 0).to_numpy(), out["dist_from_depot_km"], live["dist_from_courier_km"])
    out["dist_from_position_or_depot_km"] = position.astype("float32")
    out["dist_rank_position_or_depot"] = rank_in_event(live, np.nan_to_num(position, nan=1e9))
    return out


def context_features(live: pd.DataFrame, packages: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([area_now(live, packages), courier_recent(live, packages), courier_gps(live, packages), depot(live, packages)], axis=1)
