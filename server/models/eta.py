"""ETA model: minutes until a pending package is delivered (LightGBM, absolute-error objective)."""

import lightgbm as lgb
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from server.config import EARLY_STOPPING_ROUNDS, ETA_PARAMS, SEED, THREADS
from server.models.encoding import categorical_columns, encode, fit_schema

TARGET = "remaining_min"


def fit_eta(fit_rows: pd.DataFrame, stop_rows: pd.DataFrame, columns: list[str]) -> tuple[lgb.LGBMRegressor, dict]:
    """Fit on fit_rows; early-stop on stop_rows. Category vocabulary comes from fit_rows only."""
    schema = fit_schema(fit_rows, columns)
    model = lgb.LGBMRegressor(**ETA_PARAMS, random_state=SEED, n_jobs=THREADS, deterministic=True, force_col_wise=True, verbosity=-1)
    with threadpool_limits(limits=THREADS):
        model.fit(
            encode(fit_rows, columns, schema),
            fit_rows[TARGET],
            eval_set=[(encode(stop_rows, columns, schema), stop_rows[TARGET])],
            eval_metric="l1",
            categorical_feature=categorical_columns(columns),
            callbacks=[lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False)],
        )
    return model, schema


def predict_eta(model, schema: dict, rows: pd.DataFrame, columns: list[str]) -> np.ndarray:
    with threadpool_limits(limits=THREADS):
        return np.maximum(model.predict(encode(rows, columns, schema)), 0)
