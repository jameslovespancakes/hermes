import unittest

import pandas as pd

from server.pipeline.staleness import delayed_uploads
from server.tests.helpers import records


class StalenessDataTests(unittest.TestCase):
    def test_delays_whole_courier_days_and_keeps_event_times(self):
        recs = records(days=4, couriers=(1, 2, 3), per_day=6)
        out = delayed_uploads(recs, share=0.5, min_lag=15, max_lag=180, seed=3)
        pd.testing.assert_series_equal(out["delivered_at"], recs["delivered_at"])
        lag = (out["received_at"] - out["delivered_at"]).dt.total_seconds() / 60
        day = out["courier_id"].astype(str) + out["delivered_at"].dt.strftime("%m-%d")
        self.assertTrue((lag.groupby(day).nunique() == 1).all())
        self.assertTrue(((lag == 0) | ((lag >= 15) & (lag <= 180))).all())
        self.assertTrue((lag > 0).any() and (lag == 0).any())

    def test_seeded(self):
        recs = records(days=3)
        pd.testing.assert_frame_equal(delayed_uploads(recs, 0.5, 15, 180), delayed_uploads(recs, 0.5, 15, 180))


if __name__ == "__main__":
    unittest.main()
