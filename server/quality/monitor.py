"""Monitoring baseline (fitted at training time) and the data-health check used while serving."""

from dataclasses import dataclass

import pandas as pd

from server.quality.config import QUALITY, QualityConfig
from server.quality.contract import city_bounds, validate
from server.quality.drift import calibrate, drift_report

DRIFT_FEATURES = ["n_pending", "dist_from_courier_km", "pace_today_min", "feed_age_min", "upload_lag_min"]
BASELINE_DAYS = 30
BASELINE_SAMPLE = 200_000


@dataclass
class MonitorBaseline:
    """Reference inputs and calibrated drift thresholds, plus city bounds for the data contract."""

    drift_reference: pd.DataFrame
    drift_thresholds: dict
    contract_bounds: tuple[float, float, float, float]


def fit_baseline(live: pd.DataFrame, records: pd.DataFrame, cutoff: pd.Timestamp, config: QualityConfig = QUALITY) -> MonitorBaseline:
    """Reference = live inputs in the 30 days before the cutoff; thresholds calibrated against the 30 days before that."""

    def window(days_back: int) -> pd.DataFrame:
        start, end = cutoff - pd.Timedelta(days=days_back + BASELINE_DAYS), cutoff - pd.Timedelta(days=days_back)
        part = live.loc[(live["s"] >= start) & (live["s"] < end), DRIFT_FEATURES]
        return part.sample(n=min(BASELINE_SAMPLE, len(part)), random_state=0).reset_index(drop=True)

    reference, earlier = window(0), window(BASELINE_DAYS)
    history = records.loc[records["accepted_at"] < cutoff]
    return MonitorBaseline(reference, calibrate(reference, earlier, DRIFT_FEATURES, config), city_bounds(history))


def data_health(baseline: MonitorBaseline, batch: pd.DataFrame, inputs: pd.DataFrame, config: QualityConfig = QUALITY) -> dict:
    """Data contract on a batch of records plus input drift of current live inputs against the baseline."""
    expectations = validate(batch, baseline.contract_bounds, config)
    drift = drift_report(baseline.drift_reference, inputs, DRIFT_FEATURES, baseline.drift_thresholds) if len(inputs) else None
    contract_ok = all(e.passed for e in expectations)
    status = "act" if (not contract_ok or (drift and drift["alert"] == "act")) else ("watch" if drift and drift["alert"] == "watch" else "ok")
    return {
        "status": status,
        "contract_passed": contract_ok,
        "contract": [{"check": e.name, "observed": e.observed, "threshold": e.threshold, "passed": e.passed} for e in expectations],
        "drift": drift,
    }
