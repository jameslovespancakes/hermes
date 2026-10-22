"""ETA model: minutes until a pending package is delivered (average of LightGBM models, absolute-error objective)."""

from dataclasses import dataclass
from typing import Protocol

import lightgbm as lgb
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from server.config import EARLY_STOPPING_ROUNDS, ETA_PARAMS, SEED, THREADS
from server.models.encoding import categorical_columns, encode, fit_schema

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
        with threadpool_limits(limits=THREADS):
            return np.maximum(np.mean([m.predict(X) for m in self.models], axis=0), 0)


def fit_eta(fit_rows: pd.DataFrame, stop_rows: pd.DataFrame, columns: list[str], seeds=(SEED,), target: str = TARGET) -> EtaModel:
    schema = fit_schema(fit_rows, columns)
    X, X_stop = encode(fit_rows, columns, schema), encode(stop_rows, columns, schema)
    models = []
    for seed in seeds:
        model = lgb.LGBMRegressor(**ETA_PARAMS, random_state=seed, n_jobs=THREADS, deterministic=True, force_col_wise=True, verbosity=-1)
        with threadpool_limits(limits=THREADS):
            model.fit(
                X,
                fit_rows[target],
                eval_set=[(X_stop, stop_rows[target])],
                eval_metric="l1",
                categorical_feature=categorical_columns(columns),
                callbacks=[lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False)],
            )
        models.append(model)
    return EtaModel(models, columns, schema)
