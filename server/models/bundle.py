"""The trained bundle: every model and safeguard the server needs, and the prediction chain that uses them."""

import gzip
import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from server.data.download import sha256_file
from server.features.zones import Zones, zone_features
from server.models.eta import EtaModel, Regressor
from server.models.later import LaterDay
from server.models.risk import RiskModel
from server.models.route import add_route_outputs, predict_route
from server.models.zone import Classifier, add_zone_outputs, predict_zone
from server.quality.guard import DataGuard
from server.quality.monitor import MonitorBaseline


@dataclass
class ModelBundle:
    city: str
    trained_through: str
    habit_columns: list[str]
    zones: Zones
    zone_model: Classifier
    route_model: Regressor
    eta: EtaModel
    later: LaterDay
    risk: RiskModel
    monitor: MonitorBaseline
    staleness: EtaModel | None = None
    guard: DataGuard | None = None
    info: dict = field(default_factory=dict)

    def prepare(self, live: pd.DataFrame, packages: pd.DataFrame) -> pd.DataFrame:
        """Zone inputs, next-zone probability, and route order for live rows."""
        live = pd.concat([live, zone_features(live, packages, self.zones)], axis=1)
        live = add_zone_outputs(live, predict_zone(self.zone_model, live))
        return add_route_outputs(live, predict_route(self.route_model, live))

    def minutes(self, live: pd.DataFrame) -> np.ndarray:
        return self.later.blend(live, self.eta.predict(live))

    def save(self, path: Path) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, "wb", compresslevel=6) as stream:
            pickle.dump(self, stream, protocol=pickle.HIGHEST_PROTOCOL)
        return sha256_file(path)

    @staticmethod
    def load(path: Path) -> "ModelBundle":
        """Pickle: load only bundles this project produced."""
        with gzip.open(path, "rb") as stream:
            bundle = pickle.load(stream)
        if not isinstance(bundle, ModelBundle):
            raise TypeError(f"{path} is not a ModelBundle")
        return bundle
