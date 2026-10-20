import unittest

import numpy as np
import pandas as pd

from server.features.habits import habit_features
from server.features.package import package_features
from server.tests.helpers import records


def habits(recs):
    return habit_features(package_features(recs, "yt"))


class HabitTests(unittest.TestCase):
    def test_first_day_has_no_history(self):
        h = habits(records(days=2))
        day0 = records(days=2)["accepted_at"].dt.normalize() == pd.Timestamp("2000-05-01")
        self.assertTrue((h.loc[day0.to_numpy(), "hab_ca_count"] == 0).all())
        self.assertTrue((h.loc[~day0.to_numpy(), "hab_ca_count"] > 0).any())

    def test_same_day_and_future_deliveries_never_change_a_query(self):
        recs = records(days=3)
        last_day = recs["accepted_at"].dt.normalize() == recs["accepted_at"].dt.normalize().max()
        changed = recs.copy()
        changed.loc[last_day, "delivered_at"] += pd.Timedelta(hours=5)   # rewrite the query day's own outcomes
        changed["duration_minutes"] = (changed["delivered_at"] - changed["accepted_at"]).dt.total_seconds() / 60
        pd.testing.assert_frame_equal(habits(recs).loc[last_day.to_numpy()], habits(changed).loc[last_day.to_numpy()])

    def test_unknown_deliveries_are_not_history(self):
        recs = records(days=3)
        hidden = recs.copy()
        day1 = hidden["accepted_at"].dt.normalize() == pd.Timestamp("2000-05-02")
        hidden.loc[day1, ["delivered_at", "duration_minutes"]] = [pd.NaT, np.nan]
        day2 = (recs["accepted_at"].dt.normalize() == pd.Timestamp("2000-05-03")).to_numpy()
        self.assertLess(habits(hidden).loc[day2, "hab_ca_count"].sum(), habits(recs).loc[day2, "hab_ca_count"].sum())


if __name__ == "__main__":
    unittest.main()
