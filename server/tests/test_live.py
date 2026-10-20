import unittest

import numpy as np
import pandas as pd

from server.config import LIVE_COLS
from server.features.live import build_live_queries
from server.pipeline.features import package_table
from server.tests.helpers import records


def live_for(recs, events=None):
    return build_live_queries(package_table(recs, "yt"), events)


class LiveQueryTests(unittest.TestCase):
    def test_pending_set_definition(self):
        recs = records(days=1, couriers=(1,), per_day=5)
        live = live_for(recs)
        delivered = recs["delivered_at"].to_numpy()
        for s, group in live.groupby("s"):
            expected = set(np.flatnonzero((recs["accepted_at"].to_numpy() <= s) & (delivered > s)))
            self.assertEqual(set(group["row"]), expected)
            self.assertTrue((group["remaining_min"] > 0).all())

    def test_future_delivery_times_do_not_change_features(self):
        recs = records(days=1, couriers=(1,), per_day=6)
        s = recs["delivered_at"].iloc[1]
        later = recs["delivered_at"] > s
        changed = recs.copy()
        changed.loc[later, "delivered_at"] = changed.loc[later, "delivered_at"] + pd.Timedelta(hours=2)
        changed["duration_minutes"] = (changed["delivered_at"] - changed["accepted_at"]).dt.total_seconds() / 60
        events = pd.DataFrame({"courier_id": ["yt:1"], "s": [s]})
        a, b = live_for(recs, events), live_for(changed, events)
        pd.testing.assert_frame_equal(a[["row", *LIVE_COLS]], b[["row", *LIVE_COLS]])

    def test_unknown_delivery_counts_as_pending(self):
        recs = records(days=1, couriers=(1,), per_day=4)
        s = recs["delivered_at"].iloc[0]
        hidden = recs.copy()
        hidden.loc[1:, ["delivered_at", "duration_minutes"]] = [pd.NaT, np.nan]
        live = live_for(hidden, pd.DataFrame({"courier_id": ["yt:1"], "s": [s]}))
        self.assertEqual(sorted(live["row"]), [1, 2, 3])
        self.assertTrue(live["remaining_min"].isna().all())

    def test_courier_location_is_last_delivery(self):
        recs = records(days=1, couriers=(1,), per_day=4)
        s = recs["delivered_at"].iloc[1]
        live = live_for(recs, pd.DataFrame({"courier_id": ["yt:1"], "s": [s + pd.Timedelta(minutes=3)]}))
        self.assertTrue((live["cur_row"] == 1).all())


if __name__ == "__main__":
    unittest.main()
