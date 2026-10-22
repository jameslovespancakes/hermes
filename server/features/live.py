"""Live queries: each pending package at each courier moment, with causal live inputs."""

import numpy as np
import pandas as pd

from server.config import LIVE_COLS
from server.features.live_kernel import COLUMNS, live_rows


def build_live_queries(packages: pd.DataFrame, events: pd.DataFrame | None = None) -> pd.DataFrame:
    """Live query rows for every recorded delivery moment, or for the given (courier, moment) events."""
    as_ns = lambda column: packages[column].to_numpy("datetime64[ns]").view(np.int64)  # noqa: E731
    delivered = packages["_delivered_at"].to_numpy("datetime64[ns]")
    event_time = "_received_at" in packages
    received = packages["_received_at"].to_numpy("datetime64[ns]") if event_time else delivered
    accepted_clock = (packages["_accepted_at"] - packages["_accepted_at"].dt.normalize()).dt.total_seconds().to_numpy() / 60
    usual_pace = (packages["hab_courier_usual_shift_hours"] * 60 / packages["hab_courier_usual_deliveries_per_day"]).to_numpy()

    code, couriers = pd.factorize(packages["courier_id"].astype(str))
    groups = np.argsort(code, kind="stable")
    starts = np.searchsorted(code[groups], np.arange(len(couriers) + 1))
    if events is None:
        per_group = [np.unique(delivered[groups[starts[g] : starts[g + 1]]]) for g in range(len(couriers))]
        per_group = [t[~np.isnat(t)] for t in per_group]
    else:
        wanted = {c: np.unique(g["s"].to_numpy("datetime64[ns]")) for c, g in events.groupby(events["courier_id"].astype(str))}
        per_group = [wanted.get(c, np.array([], "datetime64[ns]")) for c in couriers]
    times = np.concatenate([t.view(np.int64) for t in per_group]) if per_group else np.array([], np.int64)
    t_starts = np.concatenate([[0], np.cumsum([len(t) for t in per_group])]).astype(np.int64)

    rows, moments, cur, values = live_rows(
        groups.astype(np.int64),
        starts.astype(np.int64),
        times,
        t_starts,
        as_ns("_accepted_at"),
        delivered.view(np.int64),
        ~np.isnat(delivered),
        received.view(np.int64),
        ~np.isnat(received),
        event_time,
        packages["lat"].to_numpy(float),
        packages["lng"].to_numpy(float),
        pd.factorize(packages["aoi_id"].astype(str))[0].astype(np.int64),
        packages["hab_ca_minutes_until_usual_delivery"].to_numpy(float) + accepted_clock,
        packages["hab_courier_minutes_until_usual_shift_end"].to_numpy(float) + accepted_clock,
        usual_pace,
    )
    live = pd.DataFrame(values, columns=list(COLUMNS))
    live.insert(0, "row", rows)
    live.insert(1, "s", moments.view("datetime64[ns]"))
    live.insert(2, "cur_row", cur)
    for column in LIVE_COLS + ["feed_age_min", "upload_lag_min", "remaining_min"]:
        live[column] = live[column].astype("float32")
    return live


def annotate_events(live: pd.DataFrame, packages: pd.DataFrame, package_cols: list[str]) -> pd.DataFrame:
    """Attach package/habit inputs and event bookkeeping (event id, day, true order for training labels)."""
    rows = live["row"].to_numpy()
    live = pd.concat([live.reset_index(drop=True), packages[package_cols].iloc[rows].reset_index(drop=True)], axis=1)
    live["_delivered_at"] = packages["_delivered_at"].to_numpy()[rows]
    live["_order_id"] = packages["_order_id"].to_numpy()[rows]
    live["courier_s"] = packages["courier_id"].astype(str).to_numpy()[rows]
    s = live["s"].to_numpy()
    starts = np.r_[True, (s[1:] != s[:-1]) | (live["courier_s"].to_numpy()[1:] != live["courier_s"].to_numpy()[:-1])]
    live["event"] = np.cumsum(starts) - 1
    days, day_index = np.unique(s.astype("datetime64[D]"), return_inverse=True)
    live["day"] = pd.Index(days).strftime("%m-%d").to_numpy()[day_index]
    by_event = live.groupby("event")
    spread = (live["n_pending"] - 1).clip(lower=1)
    live["true_pos"] = ((by_event["remaining_min"].rank(method="first") - 1) / spread).astype("float32")
    live["elapsed_rank"] = (by_event["elapsed_min"].rank(method="first") - 1) / spread
    return live
