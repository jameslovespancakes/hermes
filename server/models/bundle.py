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
from server.models.zone import add_zone_outputs, predict_zone
from server.quality.guard import DataGuard
from server.quality.monitor import MonitorBaseline


@dataclass
class ModelBundle:
    city: str
    route_model: Regressor
    eta: EtaModel
    habit_columns: list[str]
    trained_through: str
    zones: Zones | None = None
    zone_model: Regressor | None = None
    later: LaterDay | None = None
    risk: RiskModel | None = None
    staleness: EtaModel | None = None
    guard: DataGuard | None = None
    monitor: MonitorBaseline | None = None
    info: dict = field(default_factory=dict)

    def prepare(self, live: pd.DataFrame, packages: pd.DataFrame) -> pd.DataFrame:
        """Zone inputs, next-zone probability, and route order for live rows."""
        if self.zones is not None:
            live = pd.concat([live, zone_features(live, packages, self.zones)], axis=1)
        if self.zone_model is not None:
            live = add_zone_outputs(live, predict_zone(self.zone_model, live))
        return add_route_outputs(live, predict_route(self.route_model, live))

    def minutes(self, live: pd.DataFrame) -> np.ndarray:
        minutes = self.eta.predict(live)
        return self.later.blend(live, minutes) if self.later is not None else minutes

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
