"""Live queries: at a courier event time s, one row per package that courier still holds.

Causality: a package is pending at s if accepted at or before s and not recorded delivered at or before s.
Only deliveries at or before s shape any feature; unknown deliveries (NaT) are treated as still pending.
The courier's location is the destination of their most recent delivery at or before s.
"""

import numpy as np
import pandas as pd

from server.config import LIVE_COLS
from server.features.geometry import greedy_tour, haversine_km, rank_fraction

MINUTE = np.timedelta64(1, "m")
_ROUTE_SHAPE = ("greedy_pos", "greedy_pos_frac", "greedy_km", "aoi_greedy_pos_frac", "aoi_earlier_count")


def _event_rows(s, idx, a, d, d_known_sorted, lat, lng, aoi, usual_ca, usual_end, usual_pace):
    pending_mask = (a <= s) & ~(d <= s)            # NaT deliveries compare False -> still pending
    if not pending_mask.any():
        return None
    pend = idx[pending_mask]
    n = len(pend)
    k1 = np.searchsorted(d_known_sorted, s, "right")
    last = d_known_sorted[k1 - 1] if k1 else None
    done_now = idx[d == last] if last is not None else idx[:0]
    clat = np.nanmean(lat[done_now]) if len(done_now) else np.nan
    clng = np.nanmean(lng[done_now]) if len(done_now) else np.nan
    day = s.astype("datetime64[D]")
    k0 = np.searchsorted(d_known_sorted, day, "left")
    n_today = k1 - k0
    first_today = d_known_sorted[k0] if n_today > 0 else None
    since_first = (s - first_today) / MINUTE if first_today is not None else np.nan
    pace = since_first / (n_today - 1) if n_today >= 2 else np.nan
    clock_s = (s - day) / MINUTE
    plat, plng = lat[pend], lng[pend]
    q = {"row": pend, "s": np.full(n, s), "cur_row": np.full(n, done_now[0] if len(done_now) else -1),
         "elapsed_min": (s - a[pending_mask]) / MINUTE, "clock_s": np.full(n, clock_s),
         "n_pending": np.full(n, n, float), "n_done_today": np.full(n, n_today, float),
         "n_done_last_hour": np.full(n, k1 - np.searchsorted(d_known_sorted, s - 60 * MINUTE, "right"), float),
         "pace_today_min": np.full(n, pace), "minutes_since_first_delivery_today": np.full(n, since_first)}
    dist = haversine_km(clat, clng, plat, plng)
    q["dist_from_courier_km"], q["dist_rank"] = dist, rank_fraction(dist)
    if np.isfinite(plat).all() and np.isfinite(plng).all() and np.isfinite(clat):
        order, cumulative = greedy_tour(clat, clng, plat, plng)
        codes, inv = np.unique(aoi[pend], return_inverse=True)
        sizes = np.bincount(inv)
        area_order, _ = greedy_tour(clat, clng, np.bincount(inv, plat) / sizes, np.bincount(inv, plng) / sizes)
        earlier = np.array([sizes[area_order < area_order[k]].sum() for k in range(len(codes))])
        q.update({"greedy_pos": order.astype(float), "greedy_pos_frac": order / max(n - 1, 1), "greedy_km": cumulative,
                  "aoi_greedy_pos_frac": area_order[inv] / max(len(codes) - 1, 1), "aoi_earlier_count": earlier[inv].astype(float)})
    else:
        q.update({name: np.full(n, np.nan) for name in _ROUTE_SHAPE})
    _, inv2, counts = np.unique(aoi[pend], return_inverse=True, return_counts=True)
    q["same_aoi_pending"] = counts[inv2].astype(float)
    q["at_current_aoi"] = np.isin(aoi[pend], aoi[done_now]).astype(float)
    relative = usual_ca[pend] - clock_s
    q["hab_ca_rel_now"], q["hab_ca_rank_now"] = relative, rank_fraction(relative)
    q["hab_shift_end_rel_now"] = usual_end[pend] - clock_s
    pace_used = pace if np.isfinite(pace) else np.nanmean(usual_pace[pend])
    q["est_stops_x_pace"] = (q["greedy_pos"] + 1) * pace_used
    q["remaining_min"] = (d[pending_mask] - s) / MINUTE   # NaN when the outcome is unknown
    return pd.DataFrame(q)


def build_live_queries(packages: pd.DataFrame, events: pd.DataFrame | None = None) -> pd.DataFrame:
    """Live query rows. `packages` needs package + habit columns.

    events: optional (courier_id, s) pairs; by default every recorded delivery time of every courier.
    """
    acc = packages["_accepted_at"].to_numpy()
    dlv = packages["_delivered_at"].to_numpy()
    lat, lng = packages["lat"].to_numpy(float), packages["lng"].to_numpy(float)
    acc_clock = (packages["_accepted_at"] - packages["_accepted_at"].dt.normalize()).dt.total_seconds().to_numpy() / 60
    usual_ca = packages["hab_ca_minutes_until_usual_delivery"].to_numpy() + acc_clock
    usual_end = packages["hab_courier_minutes_until_usual_shift_end"].to_numpy() + acc_clock
    usual_pace = (packages["hab_courier_usual_shift_hours"] * 60 / packages["hab_courier_usual_deliveries_per_day"]).to_numpy()
    aoi = pd.factorize(packages["aoi_id"].astype(str))[0]
    wanted = None
    if events is not None:
        wanted = {c: np.unique(g["s"].to_numpy(dtype="datetime64[ns]")) for c, g in events.groupby(events["courier_id"].astype(str))}
    chunks = []
    for courier, group in packages.groupby("courier_id", observed=True, sort=False):
        if wanted is not None and str(courier) not in wanted:
            continue
        idx = group.index.to_numpy()
        a, d = acc[idx], dlv[idx]
        known = d[~np.isnat(d)]
        d_known_sorted = np.sort(known)
        times = np.unique(known) if wanted is None else wanted[str(courier)]
        for s in times:
            rows = _event_rows(s, idx, a, d, d_known_sorted, lat, lng, aoi, usual_ca, usual_end, usual_pace)
            if rows is not None:
                chunks.append(rows)
    if not chunks:
        return pd.DataFrame(columns=["row", "s", "cur_row", *LIVE_COLS, "remaining_min"])
    live = pd.concat(chunks, ignore_index=True)
    for column in LIVE_COLS + ["remaining_min"]:
        live[column] = live[column].astype("float32")
    return live


def annotate_events(live: pd.DataFrame, packages: pd.DataFrame, package_cols: list[str]) -> pd.DataFrame:
    """Attach package/habit inputs and event bookkeeping (event id, day, true order for training labels)."""
    rows = live["row"].to_numpy()
    live = pd.concat([live.reset_index(drop=True), packages[package_cols].iloc[rows].reset_index(drop=True)], axis=1)
    live["_delivered_at"] = packages["_delivered_at"].to_numpy()[rows]
    live["_order_id"] = packages["_order_id"].to_numpy()[rows]
    live["courier_s"] = packages["courier_id"].astype(str).to_numpy()[rows]
    live["event"] = pd.factorize(live["courier_s"] + "|" + live["s"].astype(str))[0]
    live["day"] = pd.to_datetime(live["s"]).dt.strftime("%m-%d")
    by_event = live.groupby("event")
    spread = (live["n_pending"] - 1).clip(lower=1)
    live["true_pos"] = ((by_event["remaining_min"].rank(method="first") - 1) / spread).astype("float32")
    live["elapsed_rank"] = (by_event["elapsed_min"].rank(method="first") - 1) / spread
    return live
