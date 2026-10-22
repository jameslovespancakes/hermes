"""Later-day specialist: blends in a model trained on packages that slipped to a later day, by its probability."""

from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import pandas as pd

from server.config import SEED
from server.models.encoding import categorical_columns, encode, fit_schema
from server.models.eta import EtaModel, fit_eta
from server.models.parallel import fit_all
from server.models.route import courier_day_folds

PARAMS = {"n_estimators": 500, "learning_rate": 0.05, "num_leaves": 127, "colsample_bytree": 0.6}


def later_day(rows: pd.DataFrame) -> pd.Series:
    return (pd.to_datetime(rows["_delivered_at"]).dt.normalize() != pd.to_datetime(rows["s"]).dt.normalize()).astype(int)


@dataclass
class LaterDay:
    classifier: lgb.LGBMClassifier
    schema: dict
    specialist: EtaModel

    def probability(self, rows: pd.DataFrame) -> np.ndarray:
        return self.classifier.predict_proba(encode(rows, self.specialist.columns, self.schema))[:, 1]

    def blend(self, rows: pd.DataFrame, minutes: np.ndarray) -> np.ndarray:
        p = self.probability(rows)
        return (1 - p) * minutes + p * self.specialist.predict(rows)


def fit_later_day(fit_rows: pd.DataFrame, columns: list[str]) -> LaterDay:
    """Classifier on all fit rows; specialist on later-day fit rows, early-stopped on a held-out fifth of their courier-days."""
    schema = fit_schema(fit_rows, columns)
    late = fit_rows.loc[later_day(fit_rows) == 1]
    held = courier_day_folds(late) == 0

    def classifier(threads: int) -> lgb.LGBMClassifier:
        model = lgb.LGBMClassifier(**PARAMS, random_state=SEED, n_jobs=threads, force_col_wise=True, verbosity=-1)
        return model.fit(encode(fit_rows, columns, schema), later_day(fit_rows), categorical_feature=categorical_columns(columns))

    fitted, specialist = fit_all([classifier, lambda threads: fit_eta(late.loc[~held], late.loc[held], columns, threads=threads)])
    return LaterDay(fitted, schema, specialist)
