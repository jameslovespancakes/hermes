import unittest

import pandas as pd

from evidence.baddata.corrupt import Rollout, low_quality_feed
from evidence.baddata.run import CONDITIONS, TRACKS, guard_only, staleness_always_on
from evidence.baddata.score import evaluate, summary
from server.pipeline.features import checkpoints
from server.tests.helpers import constant_bundle, records

ALWAYS = Rollout(pd.Timestamp("2000-04-01"), pd.Timestamp("2000-04-02"), 1.0)


class RunTests(unittest.TestCase):
    def test_conditions_use_known_tracks(self):
        self.assertEqual([c.name for c in CONDITIONS], ["reference", "stale_only", "low_quality_only", "combined"])
        self.assertTrue(all(c.naive in TRACKS and c.protected in TRACKS for c in CONDITIONS))

    def test_ablations_remove_or_force_the_staleness_model(self):
        bundle = constant_bundle(eta=25.0, staleness=40.0)
        self.assertIsNone(guard_only(bundle).staleness)
        forced = staleness_always_on(bundle)
        self.assertIsNone(forced.staleness)
        self.assertIs(forced.eta, bundle.staleness)

    def test_scores_only_real_packages_and_tags_bad_feed(self):
        clean = records(days=2, couriers=(1, 2), per_day=6)
        truth = clean.set_index("order_id")["delivered_at"]
        events = checkpoints(clean, "yt", clean["delivered_at"].min(), clean["delivered_at"].max() + pd.Timedelta(minutes=1))
        rows = evaluate(constant_bundle(eta=25.0), low_quality_feed(clean, ALWAYS), truth, events)
        self.assertGreater(len(rows), 0)
        self.assertTrue(rows["order_id"].isin(truth.index).all())
        self.assertTrue(rows["lq_feed"].all())
        self.assertEqual(summary(rows)["n"], len(rows))


if __name__ == "__main__":
    unittest.main()
