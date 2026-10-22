"""Later-day specialist: blends in a model trained on packages that slipped to a later day, by its probability."""

from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from server.config import SEED, THREADS
from server.models.encoding import categorical_columns, encode, fit_schema
from server.models.eta import EtaModel, fit_eta

PARAMS = {"n_estimators": 500, "learning_rate": 0.05, "num_leaves": 127, "colsample_bytree": 0.6}


def later_day(rows: pd.DataFrame) -> pd.Series:
    return (pd.to_datetime(rows["_delivered_at"]).dt.normalize() != pd.to_datetime(rows["s"]).dt.normalize()).astype(int)


@dataclass
class LaterDay:
    classifier: lgb.LGBMClassifier
    schema: dict
    specialist: EtaModel

    def probability(self, rows: pd.DataFrame) -> np.ndarray:
        with threadpool_limits(limits=THREADS):
            return self.classifier.predict_proba(encode(rows, self.specialist.columns, self.schema))[:, 1]

    def blend(self, rows: pd.DataFrame, minutes: np.ndarray) -> np.ndarray:
        p = self.probability(rows)
        return (1 - p) * minutes + p * self.specialist.predict(rows)


def fit_later_day(fit_rows: pd.DataFrame, stop_rows: pd.DataFrame, columns: list[str]) -> LaterDay | None:
    fit_late, stop_late = fit_rows.loc[later_day(fit_rows) == 1], stop_rows.loc[later_day(stop_rows) == 1]
    if len(fit_late) < 200 or len(stop_late) < 50:
        return None
    schema = fit_schema(fit_rows, columns)
    classifier = lgb.LGBMClassifier(**PARAMS, random_state=SEED, n_jobs=THREADS, verbosity=-1)
    with threadpool_limits(limits=THREADS):
        classifier.fit(encode(fit_rows, columns, schema), later_day(fit_rows), categorical_feature=categorical_columns(columns))
    return LaterDay(classifier, schema, fit_eta(fit_late, stop_late, columns))
