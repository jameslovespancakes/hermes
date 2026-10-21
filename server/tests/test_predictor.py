import unittest

import numpy as np
import pandas as pd

from server.quality.guard import DataGuard
from server.serving.predictor import LiveETAPredictor, known_at
from server.tests.helpers import constant_bundle, records


def predictor():
    bundle = constant_bundle(eta=25.0)
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

    def test_stale_courier_switches_to_staleness_model_and_is_flagged(self):
        recs = records(days=2, couriers=(1, 2), per_day=6)
        recs["received_at"] = recs["delivered_at"] + np.where(recs["courier_id"] == 1, pd.Timedelta(minutes=60), pd.Timedelta(0))
        mine = recs.loc[recs["courier_id"] == 1]
        at = mine["delivered_at"].iloc[8] + pd.Timedelta(minutes=61)
        out = LiveETAPredictor(constant_bundle(eta=25.0, staleness=40.0)).predict(recs, 1, at)
        self.assertGreater(len(out), 0)
        self.assertTrue((out["model_used"] == "staleness").all())
        self.assertTrue((out["minutes_remaining"] == 40.0).all())
        self.assertTrue(out["needs_review"].all())
        self.assertIn("courier feed is stale", out["review_reasons"].iloc[0])

    def test_fresh_courier_keeps_standard_model(self):
        recs = records(days=2, couriers=(1, 2), per_day=6)
        at = recs.loc[recs["courier_id"] == 1, "delivered_at"].iloc[8] + pd.Timedelta(minutes=1)
        out = LiveETAPredictor(constant_bundle(eta=25.0, staleness=40.0)).predict(recs, 1, at)
        self.assertTrue((out["model_used"] == "standard").all())
        self.assertFalse(out["needs_review"].any())

    def test_guard_drops_resent_copies_before_predicting(self):
        recs = records(days=2, couriers=(1, 2), per_day=6)
        mine = recs.loc[recs["courier_id"] == 1]
        at = mine["delivered_at"].iloc[8] + pd.Timedelta(minutes=1)
        pending = mine.loc[mine["delivered_at"] > at].iloc[:1]
        copy = pending.assign(order_id=recs["order_id"].max() + 1)
        dirty = pd.concat([recs, copy], ignore_index=True)
        unguarded = predictor().predict(dirty, 1, at)
        guarded = LiveETAPredictor(constant_bundle(eta=25.0, guard=DataGuard().fit(recs))).predict(dirty, 1, at)
        self.assertIn(copy["order_id"].iloc[0], set(unguarded["order_id"]))
        self.assertNotIn(copy["order_id"].iloc[0], set(guarded["order_id"]))
        self.assertEqual(guarded["packages_held"].iloc[0], unguarded["packages_held"].iloc[0] - 1)


if __name__ == "__main__":
    unittest.main()
