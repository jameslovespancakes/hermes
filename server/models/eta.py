"""ETA model: minutes until a pending package is delivered (average of LightGBM models, absolute-error objective)."""

from dataclasses import dataclass
from typing import Protocol

import lightgbm as lgb
import numpy as np
import pandas as pd

from server.config import EARLY_STOPPING_ROUNDS, ETA_PARAMS, SEED
from server.models.encoding import categorical_columns, encode, fit_schema
from server.models.parallel import fit_all

TARGET = "remaining_min"


class Regressor(Protocol):
    def predict(self, X) -> np.ndarray: ...


@dataclass
class EtaModel:
    models: list[Regressor]
    columns: list[str]
    schema: dict

    def predict(self, rows: pd.DataFrame) -> np.ndarray:
        X = encode(rows, self.columns, self.schema)
        return np.maximum(np.mean([m.predict(X) for m in self.models], axis=0), 0)

    def set_params(self, **params) -> "EtaModel":
        for model in self.models:
            model.set_params(**params)
        return self


def fit_eta(
    fit_rows: pd.DataFrame, stop_rows: pd.DataFrame, columns: list[str], seeds=(SEED,), target: str = TARGET, threads: int | None = None
) -> EtaModel:
    """One model per seed, early-stopped on stop_rows; seeds fit side by side unless `threads` is given."""
    schema = fit_schema(fit_rows, columns)
    X, X_stop = encode(fit_rows, columns, schema), encode(stop_rows, columns, schema)

    def one(seed: int, n_jobs: int) -> lgb.LGBMRegressor:
        model = lgb.LGBMRegressor(**ETA_PARAMS, random_state=seed, n_jobs=n_jobs, deterministic=True, force_col_wise=True, verbosity=-1)
        return model.fit(
            X,
            fit_rows[target],
            eval_set=[(X_stop, stop_rows[target])],
            eval_metric="l1",
            categorical_feature=categorical_columns(columns),
            callbacks=[lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False)],
        )

    if threads is None:
        models = fit_all([lambda n_jobs, seed=seed: one(seed, n_jobs) for seed in seeds])
    else:
        models = [one(seed, threads) for seed in seeds]
    return EtaModel(models, columns, schema)
