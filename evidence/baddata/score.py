"""Scoring for the bad-data experiment: error summaries, the damage mechanism, detection quality, and monitoring."""

import numpy as np
import pandas as pd

from server.config import ts
from server.features.live import build_live_queries
from server.models.bundle import ModelBundle
from server.pipeline.features import package_table
from server.pipeline.train import score_events
from server.quality.detectors import duplicate_records
from server.quality.drift import drift_report
from server.quality.guard import DataGuard
from server.quality.monitor import DRIFT_FEATURES, MonitorBaseline
from server.quality.trust import record_weights, suspicious
from server.serving.predictor import LiveETAPredictor

MECHANISM_INPUTS = ("n_pending", "dist_from_courier_km", "pace_today_min", "route_ahead", "feed_age_min")


def evaluate(bundle: ModelBundle, view: pd.DataFrame, truth: pd.Series, events: pd.DataFrame, predictor=LiveETAPredictor) -> pd.DataFrame:
    """Predictions from the production predictor, scored against TRUE delivery times (real packages only) and
    tagged with the simulated feed flags."""
    rows = score_events(predictor(bundle), view, events, ts(bundle.trained_through), truth)
    meta = view.drop_duplicates("order_id").set_index("order_id")
    for column in ("lq_feed", "stale_feed", "lost_scan"):
        flags = meta[column] if column in meta else pd.Series(False, index=meta.index)
        rows[column] = rows["order_id"].map(flags).fillna(False).astype(bool).to_numpy()
    return rows


def _errors(rows: pd.DataFrame) -> np.ndarray:
    return np.abs(rows["minutes_remaining"].to_numpy() - rows["actual"].to_numpy())


def _rate(mask: np.ndarray, of: np.ndarray) -> float | None:
    return float(mask[of].mean() * 100) if of.any() else None


def summary(rows: pd.DataFrame) -> dict:
    err = _errors(rows)
    flagged = rows["needs_review"].to_numpy(dtype=bool)
    out = {
        "n": int(len(rows)),
        "mae": float(err.mean()),
        "median_ae": float(np.median(err)),
        "within_30_pct": float((err <= 30).mean() * 100),
        "staleness_model_pct": float((rows["model_used"] == "staleness").mean() * 100),
        "flagged_for_review_pct": float(flagged.mean() * 100),
        "mae_flagged": float(err[flagged].mean()) if flagged.any() else None,
        "mae_not_flagged": float(err[~flagged].mean()) if (~flagged).any() else None,
    }
    affected = (rows["lq_feed"] | rows["stale_feed"]).to_numpy()
    if affected.any() and (~affected).any():
        out["mae_affected_couriers"], out["mae_unaffected_couriers"] = float(err[affected].mean()), float(err[~affected].mean())
        out["affected_share_pct"] = float(affected.mean() * 100)
    return out


def daily(rows: pd.DataFrame, label: str) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "day": pd.to_datetime(rows["s"]).dt.strftime("%m-%d"),
            "err": _errors(rows),
            "age": rows["feed_age_min"],
            "lag": rows["upload_lag_min"],
            "affected": rows["lq_feed"] | rows["stale_feed"],
            "flagged": rows["needs_review"].astype(bool),
        }
    )
    out = frame.groupby("day").agg(
        mae=("err", "mean"),
        median_feed_age_min=("age", "median"),
        median_upload_lag_min=("lag", "median"),
        affected_pct=("affected", "mean"),
        flagged_pct=("flagged", "mean"),
        n=("err", "size"),
    )
    out[["affected_pct", "flagged_pct"]] *= 100
    return out.reset_index().assign(system=label)


def mechanism(reference: pd.DataFrame, degraded: pd.DataFrame) -> dict:
    """What moved between clean and degraded inputs for the same real package at the same moment."""
    joined = reference.merge(degraded, on=["s", "order_id"], suffixes=("_ref", "_bad"))
    out = {
        "matched_predictions": int(len(joined)),
        "mae_reference": float(np.abs(joined["minutes_remaining_ref"] - joined["actual_ref"]).mean()),
        "mae_degraded": float(np.abs(joined["minutes_remaining_bad"] - joined["actual_bad"]).mean()),
    }
    for column in MECHANISM_INPUTS:
        out[f"mean_abs_change_{column}"] = float((joined[f"{column}_bad"] - joined[f"{column}_ref"]).abs().mean())
    out["route_position_changed_pct"] = float((joined["route_ahead_bad"] != joined["route_ahead_ref"]).mean() * 100)
    return out


def guard_quality(view: pd.DataFrame, guard: DataGuard) -> dict:
    """DataGuard detection quality against the simulation's ground truth (whole timeline)."""
    duplicate = duplicate_records(view).to_numpy()
    fake = ~view["is_real"].to_numpy()
    deduped = view.loc[~duplicate]
    _, repaired = guard.misplaced(deduped)
    weight, sign = record_weights(deduped).to_numpy(), suspicious(deduped).to_numpy()
    bad, real = deduped["lq_feed"].to_numpy(), deduped["is_real"].to_numpy()
    return {
        "duplicates_found_pct_of_injected": _rate(duplicate, fake),
        "real_packages_wrongly_removed_as_duplicates": int((duplicate & ~fake).sum()),
        "bad_feed_records_flagged_pct": _rate(sign, bad & real),
        "good_records_flagged_pct": _rate(sign, ~bad),
        "bad_feed_mean_weight": float(weight[bad & real].mean()) if (bad & real).any() else None,
        "good_mean_weight": float(weight[~bad].mean()),
        "bad_feed_coordinates_repaired_pct": _rate(repaired, bad),
        "good_coordinates_repaired_pct": _rate(repaired, ~bad),
    }


def label_corruption(view: pd.DataFrame, truth: pd.Series, city: str, cutoff: pd.Timestamp) -> dict:
    """How wrong a naive pipeline's training rows are: label error on real packages, share of injected copies."""
    packages = package_table(view.loc[view["accepted_at"] < cutoff].reset_index(drop=True), city)
    live = build_live_queries(packages)
    live = live.loc[live["s"] < cutoff]
    order_ids = pd.Series(packages["_order_id"].to_numpy()[live["row"].to_numpy()], index=live.index)
    real = order_ids.isin(truth.index)
    true_remaining = (order_ids[real].map(truth) - live.loc[real, "s"]).dt.total_seconds() / 60
    return {
        "training_rows_from_fake_duplicates_pct": float((~real).mean() * 100),
        "mean_abs_label_error_min": float((live.loc[real, "remaining_min"] - true_remaining).abs().mean()),
    }


def contract_summary(report: pd.DataFrame) -> dict:
    failed = report.loc[~report["passed"]]
    return {
        "days": int(len(report)),
        "days_failed": int(len(failed)),
        "first_failed_day": failed["day"].iloc[0] if len(failed) else None,
        "most_common_failure": failed["failed_checks"].str.split("; ").explode().value_counts().index[0] if len(failed) else None,
    }


def daily_drift(baseline: MonitorBaseline, rows: pd.DataFrame, label: str) -> pd.DataFrame:
    """One row per day: PSI of each input against the training-time reference, and the alert level."""
    out = []
    for day, part in rows.groupby(pd.to_datetime(rows["s"]).dt.strftime("%m-%d")):
        report = drift_report(baseline.drift_reference, part, DRIFT_FEATURES, baseline.drift_thresholds)
        out.append(
            {
                "day": day,
                "series": label,
                "worst_feature": report["worst_feature"],
                "worst_psi": report["worst_psi"],
                "alert": report["alert"],
                **{f"psi_{k}": v for k, v in report["psi"].items()},
            }
        )
    return pd.DataFrame(out)


def drift_summary(drift: pd.DataFrame) -> dict:
    out = {}
    for series, part in drift.groupby("series"):
        alarms = part.loc[part["alert"] == "act"]
        out[series] = {
            "days": int(len(part)),
            "days_act": int(len(alarms)),
            "days_watch": int((part["alert"] == "watch").sum()),
            "first_act_day": alarms["day"].min() if len(alarms) else None,
            "most_drifted_feature": part["worst_feature"].mode().iloc[0],
            "max_psi": float(part["worst_psi"].max()),
        }
    return out


class FrozenHabits(LiveETAPredictor):
    """A predictor whose courier and area habits stopped updating at FREEZE, as if a nightly job had failed."""

    FREEZE = ts("07-01")

    def package_table(self, records: pd.DataFrame) -> pd.DataFrame:
        table = super().package_table(records)
        frozen = records.assign(delivered_at=records["delivered_at"].where(records["delivered_at"] < self.FREEZE))
        habits = super().package_table(frozen)
        table[self.bundle.habit_columns] = habits[self.bundle.habit_columns].to_numpy()
        return table


def missed_detection(bundle: ModelBundle, view: pd.DataFrame, events: pd.DataFrame) -> dict:
    """After a lost parcel's real delivery it can only look pending: how often is it flagged 'missed' then, and how
    often are genuinely pending parcels flagged."""
    rows = LiveETAPredictor(bundle).predict_events(view, events, ts(bundle.trained_through), diagnostics=True)
    meta = view.drop_duplicates("order_id").set_index("order_id")
    missed = rows["data_issues"].map(lambda issues: "missed" in issues).to_numpy()
    lost = rows["order_id"].map(meta["lost_scan"]).fillna(False).to_numpy(bool)
    after = (pd.to_datetime(rows["s"]) > rows["order_id"].map(meta["true_delivered_at"])).to_numpy()
    return {
        "lost_flagged_pct": _rate(missed, lost & after),
        "pending_flagged_pct": _rate(missed, ~lost & ~after),
        "lost_predictions": int((lost & after).sum()),
    }
