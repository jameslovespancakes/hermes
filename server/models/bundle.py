"""The trained model bundle: everything the server needs to predict and to protect itself from bad data."""

import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np
import pandas as pd

from server.data.download import sha256_file
from server.models.eta import predict_eta
from server.quality.guard import DataGuard
from server.quality.monitor import MonitorBaseline


class Regressor(Protocol):
    """What serving needs from a fitted model (LightGBM in production, stand-ins in tests)."""

    def predict(self, X) -> np.ndarray: ...


@dataclass
class EtaModel:
    """A fitted ETA model with its input columns and categorical vocabulary."""

    model: Regressor
    columns: list[str]
    schema: dict

    def predict(self, rows: pd.DataFrame) -> np.ndarray:
        return predict_eta(self.model, self.schema, rows, self.columns)


@dataclass
class ModelBundle:
    city: str
    route_model: Regressor
    eta: EtaModel
    habit_columns: list[str]
    trained_through: str  # fit cutoff 'MM-DD': outcomes after it were not used
    staleness: EtaModel | None = None  # used when a courier's feed is stale
    guard: DataGuard | None = None  # cleans records before features are built
    monitor: MonitorBaseline | None = None
    info: dict = field(default_factory=dict)

    def save(self, path: Path) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as stream:
            pickle.dump(self, stream, protocol=pickle.HIGHEST_PROTOCOL)
        return sha256_file(path)

    @staticmethod
    def load(path: Path) -> "ModelBundle":
        """Load a bundle this project produced. Pickle is only safe for trusted local files."""
        with path.open("rb") as stream:
            bundle = pickle.load(stream)
        if not isinstance(bundle, ModelBundle):
            raise TypeError(f"{path} is not a ModelBundle")
        return bundle
