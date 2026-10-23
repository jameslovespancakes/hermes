"""Today or a later day: a calibrated classifier decides, and parcels it sends to a later day get the next-day model
(the time of day they arrive, counted from the next midnight) instead of the same-day minutes ETA."""

from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from server.config import FIT_SAMPLE, SEED, Split
from server.models.encoding import categorical_columns, encode, fit_schema
from server.models.eta import EtaModel, fit_eta
from server.models.parallel import fit_all
from server.models.route import courier_day_folds

PARAMS = {"n_estimators": 500, "learning_rate": 0.05, "num_leaves": 127, "colsample_bytree": 0.6}
CUTS = np.round(np.arange(0.05, 1.0, 0.05), 2)
DAY = pd.Timedelta(days=1)


def later_day(rows: pd.DataFrame) -> pd.Series:
    return (pd.to_datetime(rows["_delivered_at"]).dt.normalize() != pd.to_datetime(rows["s"]).dt.normalize()).astype(int)


def settled_by(rows: pd.DataFrame, cutoff: pd.Timestamp) -> np.ndarray:
    """Whether 'same day or not' is known by `cutoff`: delivered before it, or the moment's day already over."""
    s = pd.to_datetime(rows["s"])
    return ((s.dt.normalize() + DAY <= cutoff) | (pd.to_datetime(rows["_delivered_at"]) < cutoff)).to_numpy()


def to_midnight(rows: pd.DataFrame) -> np.ndarray:
    s = pd.to_datetime(rows["s"])
    return ((s.dt.normalize() + DAY - s).dt.total_seconds() / 60).to_numpy()


@dataclass
class LaterDay:
    classifier: lgb.LGBMClassifier
    schema: dict
    calibration: IsotonicRegression
    cut: float
    next_day: EtaModel

    def probability(self, rows: pd.DataFrame) -> np.ndarray:
        raw = self.classifier.predict_proba(encode(rows, self.next_day.columns, self.schema))[:, 1]
        return self.calibration.predict(raw)

    def minutes(self, rows: pd.DataFrame, same_day: np.ndarray) -> np.ndarray:
        """The same-day ETA, or for parcels likely to arrive on a later day: minutes to midnight plus the next-day model."""
        later = self.probability(rows) >= self.cut
        return np.where(later, to_midnight(rows) + self.next_day.predict(rows), same_day)


def fit_later_day(live: pd.DataFrame, split: Split, columns: list[str], eta: EtaModel) -> LaterDay:
    """Classifier on moments settled before fit_end (slips still pending then included), calibrated on fit_end..stop_end;
    next-day model on delivered slips (minutes after the next midnight); the cut that minimises error on fit_end..stop_end."""
    s = pd.to_datetime(live["s"])
    train = live.loc[(s < split.fit_cutoff).to_numpy() & settled_by(live, split.fit_cutoff)]
    train = train.sample(n=min(FIT_SAMPLE, len(train)), random_state=SEED)
    check = live.loc[((s >= split.fit_cutoff) & (s < split.stop_cutoff)).to_numpy() & settled_by(live, split.stop_cutoff)]
    schema = fit_schema(train, columns)
    late = train.loc[(later_day(train) == 1).to_numpy() & (pd.to_datetime(train["_delivered_at"]) < split.fit_cutoff).to_numpy()]
    late = late.assign(
        after_midnight=(pd.to_datetime(late["_delivered_at"]) - pd.to_datetime(late["s"]).dt.normalize() - DAY).dt.total_seconds() / 60
    )
    held = courier_day_folds(late) == 0

    def classifier(threads: int) -> lgb.LGBMClassifier:
        model = lgb.LGBMClassifier(**PARAMS, random_state=SEED, n_jobs=threads, force_col_wise=True, verbosity=-1)
        return model.fit(encode(train, columns, schema), later_day(train), categorical_feature=categorical_columns(columns))

    fitted, next_day = fit_all(
        [classifier, lambda threads: fit_eta(late.loc[~held], late.loc[held], columns, target="after_midnight", threads=threads)]
    )
    raw = fitted.predict_proba(encode(check, columns, schema))[:, 1]
    calibration = IsotonicRegression(out_of_bounds="clip").fit(raw, later_day(check))
    known = check.loc[pd.to_datetime(check["_delivered_at"]) < split.stop_cutoff]
    p = calibration.predict(fitted.predict_proba(encode(known, columns, schema))[:, 1])
    actual = known["remaining_min"].to_numpy()
    same_day, other_day = eta.predict(known), to_midnight(known) + next_day.predict(known)
    errors = [np.abs(np.where(p >= cut, other_day, same_day) - actual).mean() for cut in CUTS]
    return LaterDay(fitted, schema, calibration, float(CUTS[int(np.argmin(errors))]), next_day)
