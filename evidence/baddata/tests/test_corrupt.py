import unittest

import numpy as np
import pandas as pd

from evidence.baddata.corrupt import Rollout, TimestampFault, low_quality_feed, sync_delay
from server.tests.helpers import records

ALWAYS = Rollout(pd.Timestamp("2000-04-01"), pd.Timestamp("2000-04-02"), 1.0)  # everyone adopted from the start
NEVER = Rollout(pd.Timestamp("2000-04-01"), pd.Timestamp("2000-04-02"), 0.0)


class CorruptionTests(unittest.TestCase):
    def test_rollout_share_ramps_and_clips(self):
        r = Rollout(pd.Timestamp("2000-07-01"), pd.Timestamp("2000-07-11"), 0.6)
        out = r.share(pd.Series(pd.to_datetime(["2000-06-01", "2000-07-06", "2000-08-01"])))
        np.testing.assert_allclose(out, [0.0, 0.3, 0.6])

    def test_low_quality_feed_keeps_truth_and_marks_copies(self):
        recs = records(days=2)
        bad = low_quality_feed(recs, ALWAYS, duplicate_rate=0.5)
        real = bad.loc[bad["is_real"]]
        self.assertEqual(len(real), len(recs))
        self.assertEqual(len(bad) - len(real), round(len(recs) * 0.5))
        self.assertTrue((real["delivered_at"] >= real["true_delivered_at"]).all())  # bulk sync is never early
        self.assertTrue((real["delivered_at"].dt.minute == 0).all())
        merged = real.merge(recs[["order_id", "lat"]], on="order_id", suffixes=("", "_clean"))
        self.assertGreater((merged["lat"] - merged["lat_clean"]).abs().mean(), 0.003)  # GPS jittered

    def test_no_adoption_changes_nothing(self):
        recs = records(days=2)
        bad = low_quality_feed(recs, NEVER)
        self.assertTrue(bad["is_real"].all())
        pd.testing.assert_series_equal(bad["delivered_at"], bad["true_delivered_at"], check_names=False)

    def test_noise_mode_never_delivers_before_acceptance(self):
        bad = low_quality_feed(records(days=2), ALWAYS, fault=TimestampFault.NOISE)
        self.assertTrue((bad["delivered_at"] >= bad["accepted_at"]).all())

    def test_sync_delay_shifts_visible_time_only(self):
        recs = records(days=1)
        stale = sync_delay(recs, ALWAYS, lag_minutes=60)
        np.testing.assert_array_equal((stale["delivered_at"] - stale["true_delivered_at"]).dt.total_seconds().unique(), [3600.0])
        self.assertTrue(stale["stale_feed"].all())

    def test_event_time_view_keeps_scanner_time(self):
        recs = records(days=1)
        stale = sync_delay(recs, ALWAYS, lag_minutes=60, event_time=True)
        pd.testing.assert_series_equal(stale["delivered_at"], stale["true_delivered_at"], check_names=False)
        np.testing.assert_array_equal((stale["received_at"] - stale["delivered_at"]).dt.total_seconds().unique(), [3600.0])

    def test_adoption_is_per_courier_and_deterministic(self):
        half = Rollout(pd.Timestamp("2000-04-01"), pd.Timestamp("2000-04-02"), 0.5)
        recs = records(days=2, couriers=tuple(range(1, 21)))
        a, b = sync_delay(recs, half), sync_delay(recs, half)
        pd.testing.assert_frame_equal(a, b)
        self.assertEqual(a.groupby("courier_id")["stale_feed"].nunique().max(), 1)


if __name__ == "__main__":
    unittest.main()
