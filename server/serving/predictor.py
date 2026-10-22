"""Live ETA prediction: the one path used by the API, training evaluation, and experiments."""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from server.config import MODEL_STORE
from server.models.bundle import ModelBundle
from server.pipeline.features import checkpoints, live_table, package_table
from server.quality.config import QUALITY, CleanMode, QualityConfig
from server.quality.guard import feed_is_stale, review_flags
from server.quality.monitor import DRIFT_FEATURES, data_health

OUTPUT_COLUMNS = [
    "order_id",
    "minutes_remaining",
    "predicted_delivery_at",
    "predicted_position",
    "packages_held",
    "minutes_since_accepted",
    "feed_age_min",
    "upload_lag_min",
    "model_used",
    "needs_review",
    "review_reasons",
    "risk_min",
    "uncertain",
]
HEALTH_EVENTS = 2000
DIAGNOSTIC_COLUMNS = ["s", "courier", "n_pending", "dist_from_courier_km", "pace_today_min", "route_ahead"]


def known_at(records: pd.DataFrame, at: pd.Timestamp) -> pd.DataFrame:
    """The log as it looked at time `at`: later acceptances dropped, deliveries not yet received hidden."""
    known = records.loc[records["accepted_at"] <= at].copy()
    arrived = known["received_at"] if "received_at" in known else known["delivered_at"]
    future = arrived > at
    known.loc[future, "delivered_at"] = pd.NaT
    known.loc[future, "duration_minutes"] = np.nan
    if "received_at" in known:
        known.loc[future, "received_at"] = pd.NaT
    return known.reset_index(drop=True)


def couriers_holding(records: pd.DataFrame, at: pd.Timestamp) -> pd.Series:
    """Number of packages each courier (raw id) holds at `at`, largest first."""
    arrived = records["received_at"] if "received_at" in records else records["delivered_at"]
    held = records.loc[(records["accepted_at"] <= at) & ~(arrived <= at)]
    return held.groupby("courier_id").size().sort_values(ascending=False)


def courier_positions(records: pd.DataFrame, at: pd.Timestamp) -> pd.DataFrame:
    """Last known position of each courier at `at` (raw ids)."""
    known = known_at(records, at)
    today = at.normalize()
    delivered = known.loc[known["delivered_at"].between(today, at)].sort_values("delivered_at")
    last_drop = delivered.groupby("courier_id")[["lat", "lng"]].last()
    accepted = known.loc[known["accepted_at"].between(today, at)].sort_values("accepted_at")
    last_accept = accepted.groupby("courier_id")[["accept_gps_lat", "accept_gps_lng"]].last()
    last_accept.columns = ["lat", "lng"]
    return last_drop.combine_first(last_accept).dropna()


def _reasons(flags: pd.DataFrame) -> list[list[str]]:
    names = {"flag_stale_feed": "courier feed is stale", "flag_bulk_scan": "delivery times are bulk-synced"}
    return [[names[c] for c in names if row[c]] for _, row in flags.iterrows()]


@dataclass
class LiveETAPredictor:
    bundle: ModelBundle
    config: QualityConfig = field(default_factory=lambda: QUALITY)

    @classmethod
    def from_store(cls, city: str) -> "LiveETAPredictor":
        return cls(ModelBundle.load(MODEL_STORE / city / "model.pkl"))

    @property
    def city(self) -> str:
        return self.bundle.city

    def clean(self, records: pd.DataFrame) -> pd.DataFrame:
        if self.bundle.guard is None:
            return records
        cleaned, _ = self.bundle.guard.clean(records, CleanMode.SERVE)
        return cleaned

    def score(self, live: pd.DataFrame, packages: pd.DataFrame, diagnostics: bool = False) -> pd.DataFrame:
        """Predictions for live rows: zones and route -> ETA (staleness-aware when the feed is stale) -> flags."""
        live = self.bundle.prepare(live, packages)
        minutes = self.bundle.minutes(live)
        model_used = np.full(len(live), "standard", dtype=object)
        if self.bundle.staleness is not None:
            stale = feed_is_stale(live, self.config.fresh_max_feed_age_min, self.config.fresh_max_upload_lag_min)
            if stale.any():
                minutes = np.where(stale, self.bundle.staleness.predict(live), minutes)
                model_used[stale] = "staleness"
        flags = review_flags(live, packages, self.config)
        risk = self.bundle.risk.predict(live, minutes)
        out = pd.DataFrame(
            {
                "order_id": live["_order_id"].to_numpy(),
                "minutes_remaining": minutes,
                "predicted_delivery_at": (pd.to_datetime(live["s"]) + pd.to_timedelta(minutes, unit="m")).dt.round("min").to_numpy(),
                "predicted_position": (live["route_ahead"] + 1).astype(int).to_numpy(),
                "packages_held": live["n_pending"].astype(int).to_numpy(),
                "minutes_since_accepted": live["elapsed_min"].to_numpy(),
                "feed_age_min": live["feed_age_min"].to_numpy(),
                "upload_lag_min": live["upload_lag_min"].to_numpy(),
                "model_used": model_used,
                "needs_review": flags["needs_review"].to_numpy(),
                "review_reasons": _reasons(flags),
                "risk_min": risk,
                "uncertain": risk > self.bundle.risk.threshold,
            }
        )
        if diagnostics:
            out["s"], out["courier"] = live["s"].to_numpy(), live["courier_s"].to_numpy()
            for column in DIAGNOSTIC_COLUMNS[2:]:
                out[column] = live[column].to_numpy()
        return out

    def predict_events(self, records: pd.DataFrame, events: pd.DataFrame, transition_cutoff: pd.Timestamp, diagnostics: bool = False) -> pd.DataFrame:
        """Batch predictions at many (courier_id 'city:id', s) events; every feature is causal per event."""
        packages = package_table(self.clean(records), self.city)
        live = live_table(packages, transition_cutoff, events)
        if live.empty:
            return pd.DataFrame(columns=OUTPUT_COLUMNS)
        return self.score(live, packages, diagnostics)

    def prepare(self, records: pd.DataFrame, at: pd.Timestamp) -> pd.DataFrame:
        """Package table as known at `at` (the expensive, cacheable step)."""
        return package_table(self.clean(known_at(records, at)), self.city)

    def predict_couriers(self, packages: pd.DataFrame, courier_ids, at: pd.Timestamp, diagnostics: bool = False) -> pd.DataFrame:
        """ETAs for every package the given couriers (raw ids) hold at `at`, in predicted stop order."""
        events = pd.DataFrame({"courier_id": [f"{self.city}:{c}" for c in courier_ids], "s": at})
        live = live_table(packages, at.normalize(), events)
        if live.empty:
            return pd.DataFrame(columns=OUTPUT_COLUMNS)
        return self.score(live, packages, diagnostics).sort_values("predicted_position", kind="stable").reset_index(drop=True)

    def predict(self, records: pd.DataFrame, courier_id, at: pd.Timestamp) -> pd.DataFrame:
        """ETAs for every package `courier_id` (raw id) holds at time `at`."""
        return self.predict_couriers(self.prepare(records, at), [courier_id], at)

    def data_health(self, records: pd.DataFrame, packages: pd.DataFrame, at: pd.Timestamp) -> dict:
        """Data contract and input drift over the 24 h before `at`."""
        batch = known_at(records, at)
        batch = batch.loc[batch["delivered_at"] > at - pd.Timedelta(days=1)]
        events = checkpoints(batch, self.city, at - pd.Timedelta(days=1), at)
        events = events.sample(n=min(HEALTH_EVENTS, len(events)), random_state=0)
        live = live_table(packages, at.normalize(), events)
        report = data_health(self.bundle.monitor, batch, live[DRIFT_FEATURES], self.config)
        report["records_checked"] = len(batch)
        return report
