"""Data contract: expectations every batch of delivery records must meet."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from server.quality.config import QUALITY, QualityConfig
from server.quality.detectors import duplicate_records

REQUIRED = ["order_id", "courier_id", "aoi_id", "lat", "lng", "accepted_at", "delivered_at"]


@dataclass(frozen=True)
class Expectation:
    name: str
    observed: float
    threshold: float
    passed: bool


def _pct(mask) -> float:
    return float(np.mean(mask) * 100)


def city_bounds(records: pd.DataFrame, pad_deg: float = 0.05) -> tuple[float, float, float, float]:
    """Bounding box of destinations (0.1-99.9 percentiles, padded), learned from trusted history."""
    lat_lo, lat_hi = np.nanquantile(records["lat"], [0.001, 0.999])
    lng_lo, lng_hi = np.nanquantile(records["lng"], [0.001, 0.999])
    return lat_lo - pad_deg, lat_hi + pad_deg, lng_lo - pad_deg, lng_hi + pad_deg


def validate(batch: pd.DataFrame, bounds: tuple[float, float, float, float], config: QualityConfig = QUALITY) -> list[Expectation]:
    """Check one batch (e.g. one day of records). Returns every expectation with its observed value."""
    missing = [c for c in REQUIRED if c not in batch]
    if missing:
        return [Expectation(f"required columns present (missing {missing})", len(missing), 0, False)]
    if batch.empty:
        return []
    delivered = batch["delivered_at"].dropna()
    lat_lo, lat_hi, lng_lo, lng_hi = bounds
    outside = ~(batch["lat"].between(lat_lo, lat_hi) & batch["lng"].between(lng_lo, lng_hi))
    shared = batch.duplicated(["courier_id", "delivered_at"], keep=False) & batch["delivered_at"].notna()
    checks = [
        ("order ids unique", _pct(batch["order_id"].duplicated()), config.max_duplicate_order_id_pct),
        ("delivered not before accepted", _pct(batch["delivered_at"] < batch["accepted_at"]), config.max_delivered_before_accepted_pct),
        ("destinations inside the city", _pct(outside), config.max_outside_city_pct),
        ("courier timestamps not repeated", _pct(shared), config.max_shared_timestamp_pct),
        ("delivery times not bunched on the hour", _pct((delivered.dt.minute == 0) & (delivered.dt.second == 0)), config.max_on_the_hour_pct),
        ("no re-sent records", _pct(duplicate_records(batch)), config.max_resent_record_pct),
    ]
    return [Expectation(name, observed, threshold, observed <= threshold) for name, observed, threshold in checks]


def daily_report(records: pd.DataFrame, bounds, config: QualityConfig = QUALITY, by: str = "delivered_at") -> pd.DataFrame:
    """One row per day: each expectation's observed value and whether the whole batch passed."""
    rows = []
    for day, batch in records.groupby(records[by].dt.normalize()):
        results = validate(batch, bounds, config)
        row = {"day": day.strftime("%m-%d"), "records": len(batch), "passed": all(e.passed for e in results)}
        row.update({e.name: round(e.observed, 3) for e in results})
        row["failed_checks"] = "; ".join(e.name for e in results if not e.passed)
        rows.append(row)
    return pd.DataFrame(rows)
