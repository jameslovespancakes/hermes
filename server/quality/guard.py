"""DataGuard: de-duplicate, correct fast device clocks, repair coordinates, weight (training) or flag (serving)
machine-made records, and flag parcels a courier seems to have passed without scanning."""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from server.quality.config import QUALITY, CleanMode, QualityConfig
from server.quality.detectors import (
    area_reference,
    clock_offset_min,
    duplicate_records,
    offset_from_area_km,
    record_keys,
    record_weights,
    revisit_gap_min,
    running_bulk_share,
)


@dataclass
class DataGuard:
    reference: pd.DataFrame
    missed_after_min: float
    config: QualityConfig = field(default_factory=lambda: QUALITY)

    @classmethod
    def fit(cls, records: pd.DataFrame, config: QualityConfig = QUALITY) -> "DataGuard":
        """Per-area reference points, and how long couriers normally leave an area before coming back, from history."""
        return cls(area_reference(records), revisit_gap_min(records, config.revisit_quantile), config)

    def misplaced(self, records: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """Each record's distance from its area's reference point, and whether that is too far to be real."""
        offset = offset_from_area_km(records, self.reference)
        return offset, np.isfinite(offset) & (offset > self.config.max_area_offset_km)

    def clean(self, records: pd.DataFrame, mode: CleanMode) -> tuple[pd.DataFrame, dict]:
        mode = CleanMode(mode)
        out = records.copy()
        duplicate = duplicate_records(out)
        had_copy = record_keys(out).duplicated(keep=False) & out["delivered_at"].notna() & ~duplicate
        out = out.loc[~duplicate].copy()
        accept_shift, delivery_shift = clock_offset_min(out)
        out["accepted_at"] += pd.to_timedelta(accept_shift, unit="m")
        out["delivered_at"] += pd.to_timedelta(delivery_shift, unit="m")
        out["duration_minutes"] = (out["delivered_at"] - out["accepted_at"]).dt.total_seconds() / 60
        offset, repair = self.misplaced(out)
        ref = self.reference.reindex(out["aoi_id"].to_numpy())
        out.loc[repair, "lat"] = ref["lat"].to_numpy()[repair]
        out.loc[repair, "lng"] = ref["lng"].to_numpy()[repair]
        report = {
            "input_rows": len(records),
            "duplicates_dropped": int(duplicate.sum()),
            "clock_corrected_rows": int((accept_shift != 0).sum() + (delivery_shift != 0).sum()),
            "coordinates_repaired": int(repair.sum()),
        }
        if mode is CleanMode.TRAIN:
            out["weight"] = record_weights(out).to_numpy()
            report["mean_weight"] = float(out["weight"].mean())
        else:
            out["guard_bulk_scan"] = (running_bulk_share(out) >= self.config.bulk_scan_share).to_numpy()
            out["guard_moved_km"] = np.where(repair, offset, np.nan)
            out["guard_resent"] = had_copy.loc[out.index].to_numpy()
            out["guard_clock_min"] = np.where(accept_shift != 0, -accept_shift, np.nan)
        report["output_rows"] = len(out)
        return out.reset_index(drop=True), report


def feed_is_stale(live: pd.DataFrame, max_feed_age_min: float, max_upload_lag_min: float) -> np.ndarray:
    """Uploads running late, or no new delivery for a while since the first one today."""
    age = live["feed_age_min"].where(live["n_done_today"] > 0).to_numpy()
    return (age > max_feed_age_min) | (live["upload_lag_min"].to_numpy() > max_upload_lag_min)


def minutes_since_area_visit(live: pd.DataFrame, packages: pd.DataFrame) -> np.ndarray:
    """Per live row: minutes since its courier last delivered in its area, if that was today and after it was accepted."""
    seen = packages["_received_at"] if "_received_at" in packages else packages["_delivered_at"]
    key = packages["courier_id"].astype(str) + "|" + packages["aoi_id"].astype(str)
    rows = live["row"].to_numpy()
    wanted = key.isin(set(key.to_numpy()[rows])) & seen.notna()
    visits = pd.DataFrame({"k": key[wanted].to_numpy(), "t": seen[wanted].to_numpy("datetime64[ns]")}).sort_values("t")
    query = pd.DataFrame({"k": key.to_numpy()[rows], "s": live["s"].to_numpy("datetime64[ns]"), "i": np.arange(len(live))}).sort_values("s")
    last = pd.merge_asof(query, visits, left_on="s", right_on="t", by="k").set_index("i")["t"].reindex(np.arange(len(live))).to_numpy()
    accepted = packages["_accepted_at"].to_numpy("datetime64[ns]")[rows]
    s = live["s"].to_numpy("datetime64[ns]")
    today = last.astype("datetime64[D]") == s.astype("datetime64[D]")
    return np.where((last >= accepted) & today, (s - last) / np.timedelta64(1, "m"), np.nan)


DATA_ISSUES = ("lagging", "silent", "bulk", "clock", "moved", "resent", "missed")
COURIER_ISSUES = ("lagging", "silent", "bulk", "clock")  # about the courier's device: shown once, on the courier


def data_issues(live: pd.DataFrame, packages: pd.DataFrame, guard: DataGuard | None, config: QualityConfig = QUALITY) -> pd.DataFrame:
    """Per prediction, one column per data problem (in priority order) and its one-line reason."""
    age = live["feed_age_min"].where(live["n_done_today"] > 0).to_numpy()
    lag = live["upload_lag_min"].to_numpy()
    rows, cur = live["row"].to_numpy(), live["cur_row"].to_numpy()
    none = np.zeros(len(live), bool)
    flags = {
        "lagging": (lag > config.stale_feed_minutes, lambda i: f"Scans reach us {lag[i]:.0f} min late"),
        "silent": (age > config.stale_feed_minutes, lambda i: f"No scans from the courier for {age[i]:.0f} min"),
    }
    if guard is not None:
        moved = packages["guard_moved_km"].to_numpy()[rows]
        clock = packages["guard_clock_min"].to_numpy()[rows]
        away = np.where(live["at_current_aoi"].to_numpy() == 0, minutes_since_area_visit(live, packages), np.nan)
        flags |= {
            "bulk": (
                np.where(cur >= 0, packages["guard_bulk_scan"].to_numpy()[np.maximum(cur, 0)], False).astype(bool),
                lambda i: "Scans uploaded in bulk, so times are unreliable",
            ),
            "clock": (np.isfinite(clock), lambda i: f"Clock {clock[i]:.0f} min fast, corrected"),
            "moved": (np.isfinite(moved), lambda i: f"Address was {moved[i]:.1f} km off its area and was moved"),
            "resent": (packages["guard_resent"].to_numpy()[rows].astype(bool), lambda i: "A duplicate of this record was removed"),
            "missed": (
                away > guard.missed_after_min,
                lambda i: f"Not scanned; courier left {away[i]:.0f} min ago",
            ),
        }
    out = pd.DataFrame({kind: flags[kind][0] if kind in flags else none for kind in DATA_ISSUES}, index=live.index)
    out["issues"] = [[k for k in DATA_ISSUES if out[k].iat[i]] for i in range(len(out))]
    out["reasons"] = [[flags[k][1](i) for k in kinds] for i, kinds in enumerate(out["issues"])]
    return out
