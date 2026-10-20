import unittest

import numpy as np
import pandas as pd

from server.models.bundle import ModelBundle
from server.serving.predictor import LiveETAPredictor, known_at
from server.tests.helpers import records


class _Constant:
    """Stand-in model: predicts a fixed value per row."""

    def __init__(self, value):
        self.value = value

    def predict(self, X):
        return np.full(len(X), self.value, dtype=float)


def predictor():
    bundle = ModelBundle(city="yt", route_model=_Constant(0.0), eta_model=_Constant(25.0), eta_columns=["n_pending"],
                         eta_schema={}, habit_columns=[], trained_through="09-01")
    return LiveETAPredictor(bundle)


class PredictorTests(unittest.TestCase):
    def test_known_at_hides_the_future(self):
        recs = records(days=2)
        at = recs["delivered_at"].iloc[3]
        known = known_at(recs, at)
        self.assertTrue((known["accepted_at"] <= at).all())
        self.assertTrue((known["delivered_at"].dropna() <= at).all())
        self.assertTrue(known["delivered_at"].isna().any())

    def test_predicts_only_packages_held_at_that_moment(self):
        recs = records(days=2, couriers=(1, 2), per_day=6)
        mine = recs.loc[recs["courier_id"] == 1]
        at = mine["delivered_at"].iloc[8] + pd.Timedelta(minutes=1)
        held = mine.loc[(mine["accepted_at"] <= at) & (mine["delivered_at"] > at), "order_id"]
        out = predictor().predict(recs, 1, at)
        self.assertEqual(set(out["order_id"]), set(held))
        self.assertTrue((out["minutes_remaining"] == 25.0).all())
        self.assertTrue((out["predicted_delivery_at"] == (at + pd.Timedelta(minutes=25)).round("min")).all())

    def test_future_records_cannot_change_predictions(self):
        recs = records(days=2)
        at = recs["delivered_at"].iloc[2]
        changed = recs.copy()
        later = changed["accepted_at"] > at
        changed.loc[later, "lng"] += 1.0
        a, b = predictor().predict(recs, 1, at), predictor().predict(changed, 1, at)
        pd.testing.assert_frame_equal(a, b)


if __name__ == "__main__":
    unittest.main()
