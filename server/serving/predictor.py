"""Serve live ETAs at an arbitrary moment using only what was known at that moment.

Given the delivery log and a query time t, records accepted after t are dropped and deliveries recorded
after t are hidden (treated as still pending) before ANY feature is built. The models were trained on
courier delivery checkpoints, so predictions are most representative right after a delivery.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from server.config import MODEL_STORE
from server.models.bundle import ModelBundle
from server.models.eta import predict_eta
from server.models.route import add_route_outputs, predict_route
from server.pipeline.features import live_table, package_table


def known_at(records: pd.DataFrame, at: pd.Timestamp) -> pd.DataFrame:
    """The log as it looked at time `at` (cleaned records from server.data.loading)."""
    known = records.loc[records["accepted_at"] <= at].copy()
    future = known["delivered_at"] > at
    known.loc[future, "delivered_at"] = pd.NaT
    known.loc[future, "duration_minutes"] = np.nan
    return known.reset_index(drop=True)


@dataclass
class LiveETAPredictor:
    bundle: ModelBundle

    @classmethod
    def from_store(cls, city: str) -> "LiveETAPredictor":
        return cls(ModelBundle.load(MODEL_STORE / city / "model.pkl"))

    def predict(self, records: pd.DataFrame, courier_id, at: pd.Timestamp) -> pd.DataFrame:
        """ETAs for every package `courier_id` holds at time `at` (raw courier id, e.g. 75)."""
        city = self.bundle.city
        packages = package_table(known_at(records, at), city)
        scoped = f"{city}:{courier_id}"
        events = pd.DataFrame({"courier_id": [scoped], "s": [at]})
        live = live_table(packages, transition_cutoff=at.normalize(), events=events)
        if live.empty:
            return pd.DataFrame(columns=["order_id", "minutes_remaining", "predicted_delivery_at", "predicted_position", "packages_held"])
        live = add_route_outputs(live, predict_route(self.bundle.route_model, live))
        minutes = predict_eta(self.bundle.eta_model, self.bundle.eta_schema, live, self.bundle.eta_columns)
        out = pd.DataFrame({"order_id": live["_order_id"].to_numpy(), "minutes_remaining": minutes.round(1),
                            "predicted_delivery_at": (at + pd.to_timedelta(minutes, unit="m")).round("min"),
                            "predicted_position": (live["route_ahead"] + 1).astype(int).to_numpy(),
                            "packages_held": live["n_pending"].astype(int).to_numpy(),
                            "minutes_since_accepted": live["elapsed_min"].to_numpy()})
        return out.sort_values("predicted_position").reset_index(drop=True)
