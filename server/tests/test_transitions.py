import unittest

import numpy as np
import pandas as pd

from server.config import PACKAGE_COLS
from server.features.live import annotate_events, build_live_queries
from server.features.transitions import add_transitions
from server.pipeline.features import habit_columns, package_table
from server.tests.helpers import records


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.packages = package_table(records(days=4, couriers=(1,), per_day=8), "yt")
        live = build_live_queries(self.packages)
        self.live = annotate_events(live, self.packages, PACKAGE_COLS + habit_columns(self.packages))

    def test_training_events_exclude_their_own_day(self):
        cutoff = pd.Timestamp("2000-05-03")
        one_day = self.packages.loc[self.packages["_accepted_at"] < pd.Timestamp("2000-05-02")]
        live_one = self.live.loc[self.live["s"] < pd.Timestamp("2000-05-02")]
        with_own_day = add_transitions(live_one, one_day, cutoff)     # history = only that same day
        self.assertTrue(np.all(with_own_day["courier_transition_support"] == 0))

    def test_outcomes_after_cutoff_are_unused(self):
        cutoff = pd.Timestamp("2000-05-03")
        base = add_transitions(self.live, self.packages, cutoff)
        changed = self.packages.copy()
        late = changed["_delivered_at"] >= cutoff
        changed.loc[late, "aoi_id"] = changed.loc[late, "aoi_id"].iloc[0]
        after = add_transitions(self.live, changed, cutoff)
        early = (self.live["s"] < cutoff).to_numpy()
        np.testing.assert_array_equal(base.loc[early, "courier_transition_support"], after.loc[early, "courier_transition_support"])


if __name__ == "__main__":
    unittest.main()
