"""Risk model: expected size of the ETA error, used to flag uncertain estimates (not to change them)."""

from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import pandas as pd

from server.config import SEED, THREADS
from server.models.encoding import categorical_columns, encode, fit_schema
from server.models.eta import TARGET, fit_eta
from server.models.parallel import fit_all
from server.models.route import courier_day_folds

PARAMS = {
    "objective": "regression_l1",
    "n_estimators": 600,
    "learning_rate": 0.05,
    "num_leaves": 127,
    "min_child_samples": 100,
    "colsample_bytree": 0.6,
}
FLAG_SHARE = 0.10


@dataclass
class RiskModel:
    model: lgb.LGBMRegressor
    columns: list[str]
    schema: dict
    threshold: float

    def predict(self, rows: pd.DataFrame, minutes: np.ndarray) -> np.ndarray:
        X = encode(rows.assign(predicted_min=minutes), self.columns, self.schema)
        return np.maximum(self.model.predict(X), 0)


def fit_risk(fit_rows: pd.DataFrame, stop_rows: pd.DataFrame, columns: list[str]) -> RiskModel:
    """Learns |error| from out-of-fold ETA predictions (2 folds by courier-day); flags the riskiest 10%."""
    fold = courier_day_folds(fit_rows) % 2
    halves = fit_all([lambda threads, k=k: fit_eta(fit_rows.loc[fold != k], stop_rows, columns, threads=threads) for k in (0, 1)])
    predicted = np.zeros(len(fit_rows))
    for k, model in enumerate(halves):
        predicted[fold == k] = model.predict(fit_rows.loc[fold == k])
    rows = fit_rows.assign(predicted_min=predicted)
    risk_columns = columns + ["predicted_min"]
    schema = fit_schema(rows, risk_columns)
    model = lgb.LGBMRegressor(**PARAMS, random_state=SEED, n_jobs=THREADS, force_col_wise=True, verbosity=-1)
    model.fit(encode(rows, risk_columns, schema), np.abs(predicted - rows[TARGET]), categorical_feature=categorical_columns(risk_columns))
    risk = RiskModel(model, risk_columns, schema, 0.0)
    risk.threshold = float(np.quantile(risk.predict(rows, predicted), 1 - FLAG_SHARE))
    return risk
