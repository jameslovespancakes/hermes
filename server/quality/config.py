"""Every data-quality threshold in one place."""

from dataclasses import dataclass
from enum import Enum


class CleanMode(str, Enum):
    TRAIN = "train"
    SERVE = "serve"


@dataclass(frozen=True)
class QualityConfig:
    max_area_offset_km: float = 1.5
    bulk_scan_share: float = 0.3
    stale_feed_minutes: float = 45.0
    fresh_max_feed_age_min: float = 20.0
    fresh_max_upload_lag_min: float = 10.0
    max_duplicate_order_id_pct: float = 0.1
    max_delivered_before_accepted_pct: float = 0.0
    max_outside_city_pct: float = 0.5
    max_shared_timestamp_pct: float = 1.0
    max_on_the_hour_pct: float = 5.0
    max_resent_record_pct: float = 0.5
    drift_watch: float = 0.10
    drift_act: float = 0.25
    drift_margin: float = 2.0
    audit_rate: float = 0.10
    min_audited_predictions: int = 500
    min_improvement_min: float = 0.0
    augment_share: float = 0.5
    augment_min_lag_min: float = 15.0
    augment_max_lag_min: float = 180.0
    augment_sample: int = 400_000


QUALITY = QualityConfig()
