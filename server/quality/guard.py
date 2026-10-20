"""DataGuard: clean delivery records before training and before serving, and flag what cannot be fixed.

Training mode drops duplicates, repairs implausible coordinates, and quarantines bulk-scanned courier-days
(their delivery times are not real event times, so they would teach wrong durations).
Serving mode drops duplicates and repairs coordinates but keeps bulk-scanned records, marking them so the
prediction can be flagged for human review. Feed age is flagged at prediction time (see `oversight_flags`).
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from server.quality.detectors import (
    area_reference,
    bulk_scanned_courier_days,
    duplicate_records,
    offset_from_area_km,
    running_bulk_share,
)


@dataclass(frozen=True)
class GuardConfig:
    max_area_offset_km: float = 1.5      # clean data: 0.3% of rows exceed this
    bulk_scan_share: float = 0.3         # clean data: no courier-day has any shared timestamp
    stale_feed_minutes: float = 45.0     # oversight: no visible delivery for this long while holding packages


@dataclass
class DataGuard:
    config: GuardConfig = field(default_factory=GuardConfig)
    reference: pd.DataFrame | None = None

    def fit(self, records: pd.DataFrame) -> "DataGuard":
        """Learn per-area reference points (robust medians) from historical records."""
        self.reference = area_reference(records)
        return self

    def clean(self, records: pd.DataFrame, mode: str) -> tuple[pd.DataFrame, dict]:
        if mode not in ("train", "serve"):
            raise ValueError("mode must be 'train' or 'serve'")
        if self.reference is None:
            raise RuntimeError("DataGuard.fit must be called first")
        out = records.copy()
        duplicate = duplicate_records(out)
        out = out.loc[~duplicate].copy()
        offset = offset_from_area_km(out, self.reference)
        repair = np.isfinite(offset) & (offset > self.config.max_area_offset_km)
        ref = self.reference.reindex(out["aoi_id"].to_numpy())
        out.loc[repair, "lat"] = ref["lat"].to_numpy()[repair]
        out.loc[repair, "lng"] = ref["lng"].to_numpy()[repair]
        if mode == "train":   # offline cleaning of past days may use the whole day
            bulk = bulk_scanned_courier_days(out, self.config.bulk_scan_share)
        else:                 # serving: only deliveries recorded so far that day
            bulk = running_bulk_share(out) >= self.config.bulk_scan_share
        report = {"input_rows": len(records), "duplicates_dropped": int(duplicate.sum()), "coordinates_repaired": int(repair.sum()),
                  "bulk_scanned_rows": int(bulk.sum())}
        if mode == "train":
            out = out.loc[~bulk]
            report["quarantined_rows"] = int(bulk.sum())
        else:
            out["guard_bulk_scan"] = bulk.to_numpy()
        report["output_rows"] = len(out)
        return out.reset_index(drop=True), report


DEFAULT_GUARD = GuardConfig()


def oversight_flags(live: pd.DataFrame, packages: pd.DataFrame, config: GuardConfig = DEFAULT_GUARD) -> pd.DataFrame:
    """Per prediction: stale feed and/or bulk-scanned courier-day. Flagged predictions go to a dispatcher."""
    stale = live["feed_age_min"].to_numpy() > config.stale_feed_minutes
    if "guard_bulk_scan" in packages:
        cur = live["cur_row"].to_numpy()
        bulk = np.where(cur >= 0, packages["guard_bulk_scan"].to_numpy()[np.maximum(cur, 0)], False).astype(bool)
    else:
        bulk = np.zeros(len(live), dtype=bool)
    return pd.DataFrame({"flag_stale_feed": stale, "flag_bulk_scan": bulk, "flag_review": stale | bulk}, index=live.index)
