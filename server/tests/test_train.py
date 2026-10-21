import unittest

from server.config import Split
from server.pipeline.features import checkpoints
from server.pipeline.train import score_events, train_bundle
from server.serving.predictor import LiveETAPredictor
from server.tests.helpers import records

SPLIT = Split(fit_end="05-12", stop_end="05-16", test_end="05-19")


class TrainBundleTests(unittest.TestCase):
    """End to end on a small synthetic log: train -> serve through the production predictor."""

    @classmethod
    def setUpClass(cls):
        cls.records = records(days=18, couriers=tuple(range(1, 7)), per_day=8)
        cls.truth = cls.records.set_index("order_id")["delivered_at"]
        cls.bundle = train_bundle(cls.records, "yt", SPLIT, log=lambda _: None)

    def test_bundle_carries_every_safeguard(self):
        self.assertIsNotNone(self.bundle.guard)
        self.assertIsNotNone(self.bundle.staleness)
        self.assertIsNotNone(self.bundle.monitor)
        self.assertEqual(self.bundle.staleness.columns[-2:], ["feed_age_min", "upload_lag_min"])
        self.assertEqual(self.bundle.info["guard"]["duplicates_dropped"], 0)

    def test_layers_can_be_switched_off(self):
        plain = train_bundle(self.records, "yt", SPLIT, use_guard=False, use_staleness=False, log=lambda _: None)
        self.assertIsNone(plain.guard)
        self.assertIsNone(plain.staleness)

    def test_scores_test_window_with_true_outcomes(self):
        events = checkpoints(self.records, "yt", SPLIT.stop_cutoff, SPLIT.data_cutoff)
        rows = score_events(LiveETAPredictor(self.bundle), self.records, events, SPLIT.fit_cutoff, self.truth)
        self.assertGreater(len(rows), 0)
        self.assertTrue((rows["actual"] > 0).all())
        self.assertTrue((rows["minutes_remaining"] >= 0).all())
        self.assertTrue(set(rows["model_used"]) <= {"standard", "staleness"})


if __name__ == "__main__":
    unittest.main()
