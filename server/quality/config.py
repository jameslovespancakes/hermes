"""Every data-quality threshold in one place, with where each value comes from.

Values were set from clean LaDe-D history and validated in experiments/degradation (see its REPORT.md).
"""

from dataclasses import dataclass
from enum import Enum


class CleanMode(str, Enum):
    TRAIN = "train"  # offline: may use whole days; quarantines bulk-synced courier-days
    SERVE = "serve"  # online: only data recorded so far; keeps records but flags them


@dataclass(frozen=True)
class QualityConfig:
    # DataGuard
    max_area_offset_km: float = 1.5  # clean: 0.3% of destinations are farther from their area's median point
    bulk_scan_share: float = 0.3  # clean: no courier-day ever repeats a delivery timestamp
    # Review flags shown to a dispatcher
    stale_feed_minutes: float = 45.0
    # Staleness switch: the staleness-aware model takes over above either limit
    fresh_max_feed_age_min: float = 20.0
    fresh_max_upload_lag_min: float = 10.0
    # Data contract (percent of a daily batch)
    max_duplicate_order_id_pct: float = 0.1
    max_delivered_before_accepted_pct: float = 0.0
    max_outside_city_pct: float = 0.5
    max_shared_timestamp_pct: float = 1.0  # clean: 0.0
    max_on_the_hour_pct: float = 5.0  # clean: ~1.7 (uniform)
    max_resent_record_pct: float = 0.5  # clean: 0.0
    # Drift (PSI): conventional levels, raised per input by `drift_margin` x its natural clean drift
    drift_watch: float = 0.10
    drift_act: float = 0.25
    drift_margin: float = 2.0
    # Gated retraining
    audit_rate: float = 0.10
    min_audited_predictions: int = 500
    min_improvement_min: float = 0.0
    # Staleness-model training augmentation (simulated upload delays)
    augment_share: float = 0.5
    augment_min_lag_min: float = 15.0
    augment_max_lag_min: float = 180.0
    augment_sample: int = 400_000


QUALITY = QualityConfig()
