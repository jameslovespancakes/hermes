"""Save/load the trained model bundle (route model + ETA model + column lists + category schema)."""

import pickle
from dataclasses import dataclass, field
from pathlib import Path

import lightgbm as lgb

from server.data.download import sha256_file


@dataclass
class ModelBundle:
    city: str
    route_model: lgb.LGBMRegressor
    eta_model: lgb.LGBMRegressor
    eta_columns: list[str]
    eta_schema: dict
    habit_columns: list[str]
    trained_through: str               # last date whose outcomes the models could use (exclusive cutoff)
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
