"""DataGuard: de-duplicate, repair coordinates, and quarantine or flag bulk-synced records."""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from server.quality.config import QUALITY, CleanMode, QualityConfig
from server.quality.detectors import (
    area_reference,
    bulk_scanned_courier_days,
    duplicate_records,
    offset_from_area_km,
    running_bulk_share,
)


@dataclass
class DataGuard:
    reference: pd.DataFrame
    config: QualityConfig = field(default_factory=lambda: QUALITY)

    @classmethod
    def fit(cls, records: pd.DataFrame, config: QualityConfig = QUALITY) -> "DataGuard":
        """Per-area reference points (robust medians) from historical records."""
        return cls(area_reference(records), config)

    def clean(self, records: pd.DataFrame, mode: CleanMode) -> tuple[pd.DataFrame, dict]:
        mode = CleanMode(mode)
        out = records.copy()
        duplicate = duplicate_records(out)
        out = out.loc[~duplicate].copy()
        offset = offset_from_area_km(out, self.reference)
        repair = np.isfinite(offset) & (offset > self.config.max_area_offset_km)
        ref = self.reference.reindex(out["aoi_id"].to_numpy())
        out.loc[repair, "lat"] = ref["lat"].to_numpy()[repair]
        out.loc[repair, "lng"] = ref["lng"].to_numpy()[repair]
        if mode is CleanMode.TRAIN:
            bulk = bulk_scanned_courier_days(out, self.config.bulk_scan_share)
        else:
            bulk = running_bulk_share(out) >= self.config.bulk_scan_share
        report = {
            "input_rows": len(records),
            "duplicates_dropped": int(duplicate.sum()),
            "coordinates_repaired": int(repair.sum()),
            "bulk_scanned_rows": int(bulk.sum()),
        }
        if mode is CleanMode.TRAIN:
            out = out.loc[~bulk]
            report["quarantined_rows"] = int(bulk.sum())
        else:
            out["guard_bulk_scan"] = bulk.to_numpy()
        report["output_rows"] = len(out)
        return out.reset_index(drop=True), report


def feed_is_stale(live: pd.DataFrame, max_feed_age_min: float, max_upload_lag_min: float) -> np.ndarray:
    """Uploads running late, or no new delivery for a while since the first one today."""
    age = live["feed_age_min"].where(live["n_done_today"] > 0).to_numpy()
    return (age > max_feed_age_min) | (live["upload_lag_min"].to_numpy() > max_upload_lag_min)


def review_flags(live: pd.DataFrame, packages: pd.DataFrame, config: QualityConfig = QUALITY) -> pd.DataFrame:
    """Per prediction: stale feed and/or bulk-synced courier-day."""
    stale = feed_is_stale(live, config.stale_feed_minutes, config.stale_feed_minutes)
    if "guard_bulk_scan" in packages:
        cur = live["cur_row"].to_numpy()
        bulk = np.where(cur >= 0, packages["guard_bulk_scan"].to_numpy()[np.maximum(cur, 0)], False).astype(bool)
    else:
        bulk = np.zeros(len(live), dtype=bool)
    return pd.DataFrame({"flag_stale_feed": stale, "flag_bulk_scan": bulk, "needs_review": stale | bulk}, index=live.index)
