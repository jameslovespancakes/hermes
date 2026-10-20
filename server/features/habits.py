"""Courier and area habits learned from PREVIOUS days only.

For a package accepted on day d, every habit uses deliveries completed on days d-28 .. d-1. Packages whose
delivery is unknown (NaT, e.g. still pending at prediction time) contribute nothing to history.
"""

import numpy as np
import pandas as pd

from server.config import HABIT_WINDOW_DAYS

HABIT_KEYS = {"ca": ["courier", "aoi"], "cab": ["courier", "aoi", "bucket"], "cb": ["courier", "bucket"],
              "ab": ["aoi", "bucket"], "a": ["aoi"]}


def _key_codes(frame: pd.DataFrame, columns: list[str]) -> np.ndarray:
    if len(columns) > 1:
        return pd.MultiIndex.from_frame(frame[columns].astype(str)).factorize()[0]
    return pd.factorize(frame[columns[0]].astype(str))[0]


def _window_sums(daily: pd.DataFrame, queries: pd.DataFrame, value_cols: list[str]) -> np.ndarray:
    """Per query (key, day d): sum of daily values over completion days in [d - window, d)."""
    daily = daily.sort_values(["day", "key"])
    cumulative = daily.groupby("key")[value_cols].cumsum()
    daily = pd.concat([daily[["key", "day"]], cumulative], axis=1).sort_values("day")
    totals = {}
    for label, shift in [("end", 0), ("start", HABIT_WINDOW_DAYS)]:
        q = queries.assign(day=queries["day"] - pd.Timedelta(days=shift)).sort_values("day")
        merged = pd.merge_asof(q, daily, on="day", by="key", allow_exact_matches=False)
        totals[label] = merged.set_index("row")[value_cols].reindex(queries["row"]).fillna(0).to_numpy()
    return totals["end"] - totals["start"]


def habit_features(packages: pd.DataFrame) -> pd.DataFrame:
    """Habit columns (prefix 'hab_') aligned to `packages`.

    Per key in HABIT_KEYS (courier/area/3-hour acceptance bucket combinations): count, typical duration,
    same-day share, and minutes until the usual same-day delivery clock time. Per courier: usual shift end,
    deliveries per day, and shift length.
    """
    accepted, delivered = packages["_accepted_at"], packages["_delivered_at"]
    acc_day, dlv_day = accepted.dt.normalize(), delivered.dt.normalize()
    acc_clock = ((accepted - acc_day).dt.total_seconds() / 60).to_numpy()
    dlv_clock = (delivered - dlv_day).dt.total_seconds() / 60
    same_day = (dlv_day == acc_day).astype(float)
    base = pd.DataFrame({"courier": packages["courier_id"].astype(str), "aoi": packages["aoi_id"].astype(str),
                         "bucket": (accepted.dt.hour // 3).astype(str), "day": dlv_day,
                         "logdur": np.log1p(packages["_duration_minutes"]), "same": same_day,
                         "clock_same": dlv_clock * same_day})
    rows = np.arange(len(packages))
    out = {}
    for name, columns in HABIT_KEYS.items():
        codes = _key_codes(base, columns)
        history = (base.assign(key=codes).groupby(["key", "day"])
                   .agg(n=("logdur", "size"), s_log=("logdur", "sum"), n_same=("same", "sum"), s_clock=("clock_same", "sum"))
                   .reset_index())
        n, s_log, n_same, s_clock = _window_sums(history, pd.DataFrame({"key": codes, "day": acc_day.to_numpy(), "row": rows}),
                                                 ["n", "s_log", "n_same", "s_clock"]).T
        with np.errstate(invalid="ignore", divide="ignore"):
            out[f"hab_{name}_count"] = n
            out[f"hab_{name}_typical_duration"] = np.where(n > 0, np.expm1(s_log / n), np.nan)
            out[f"hab_{name}_same_day_frac"] = np.where(n > 0, n_same / n, np.nan)
            out[f"hab_{name}_minutes_until_usual_delivery"] = np.where(n_same > 0, s_clock / n_same, np.nan) - acc_clock
    shift = (base.assign(clock=dlv_clock).groupby(["courier", "day"])
             .agg(last=("clock", "max"), first=("clock", "min"), count=("clock", "size")).reset_index())
    shift["key"] = pd.factorize(shift["courier"])[0]
    shift["days"] = 1.0
    lookup = dict(zip(shift["courier"], shift["key"], strict=True))
    queries = pd.DataFrame({"key": base["courier"].map(lookup).fillna(-1).astype(int).to_numpy(), "day": acc_day.to_numpy(), "row": rows})
    last, first, count, days = _window_sums(shift[["key", "day", "last", "first", "count", "days"]], queries,
                                            ["last", "first", "count", "days"]).T
    with np.errstate(invalid="ignore", divide="ignore"):
        out["hab_courier_minutes_until_usual_shift_end"] = np.where(days > 0, last / days, np.nan) - acc_clock
        out["hab_courier_usual_deliveries_per_day"] = np.where(days > 0, count / days, np.nan)
        out["hab_courier_usual_shift_hours"] = np.where(days > 0, (last - first) / days / 60, np.nan)
    return pd.DataFrame(out, index=packages.index).astype("float32")
