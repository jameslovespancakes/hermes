"""DataGuard: de-duplicate, correct fast device clocks, repair coordinates, weight (training) or flag (serving)
machine-made records, and flag parcels a courier seems to have passed without scanning."""

from dataclasses import dataclass, field
from typing import Literal, get_args

import numpy as np
import pandas as pd

from server.features.context import visible_at
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

CourierIssue = Literal["lagging", "silent", "bulk", "clock"]
ParcelDataIssue = Literal["moved", "resent", "missed"]
COURIER_ISSUES = get_args(CourierIssue)
DATA_ISSUES = COURIER_ISSUES + get_args(ParcelDataIssue)


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
        """De-duplicate, correct fast clocks and repair coordinates, then weight (TRAIN) or flag (SERVE) the records."""
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
            self._serve_flags(out, had_copy, repair, offset, accept_shift)
        report["output_rows"] = len(out)
        return out.reset_index(drop=True), report

    def _serve_flags(self, out: pd.DataFrame, had_copy: pd.Series, repair: np.ndarray, offset: np.ndarray, accept_shift: np.ndarray) -> None:
        """Mark each record's bulk-synced scan, moved address, removed copy and corrected clock (in place)."""
        out["guard_bulk_scan"] = (running_bulk_share(out) >= self.config.bulk_scan_share).to_numpy()
        out["guard_moved_km"] = np.where(repair, offset, np.nan)
        out["guard_resent"] = had_copy.loc[out.index].to_numpy()
        out["guard_clock_min"] = np.where(accept_shift != 0, -accept_shift, np.nan)


def _feed_age(live: pd.DataFrame) -> np.ndarray:
    """Minutes since the courier's last event, counted only once they have delivered today."""
    return live["feed_age_min"].where(live["n_done_today"] > 0).to_numpy()


def feed_is_stale(live: pd.DataFrame, max_feed_age_min: float, max_upload_lag_min: float) -> np.ndarray:
    """Uploads running late, or no new delivery for a while since the first one today."""
    age = _feed_age(live)
    return (age > max_feed_age_min) | (live["upload_lag_min"].to_numpy() > max_upload_lag_min)


def minutes_since_area_visit(live: pd.DataFrame, packages: pd.DataFrame) -> np.ndarray:
    """Per live row: minutes since its courier last delivered in its area, if that was today and after it was accepted."""
    seen = visible_at(packages)
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


def data_issues(live: pd.DataFrame, packages: pd.DataFrame, guard: DataGuard | None, config: QualityConfig = QUALITY) -> pd.DataFrame:
    """Per prediction, its data problems (in priority order) and their one-line reasons."""
    age = _feed_age(live)
    lag = live["upload_lag_min"].to_numpy()
    rows, cur = live["row"].to_numpy(), live["cur_row"].to_numpy()
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
    issues = [[kind for kind in DATA_ISSUES if kind in flags and flags[kind][0][i]] for i in range(len(live))]
    reasons = [[flags[kind][1](i) for kind in kinds] for i, kinds in enumerate(issues)]
    return pd.DataFrame({"data_issues": issues, "review_reasons": reasons}, index=live.index)
