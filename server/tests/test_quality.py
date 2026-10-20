import unittest

import numpy as np
import pandas as pd

from server.quality.detectors import bulk_scanned_courier_days, duplicate_records, running_bulk_share
from server.quality.guard import DataGuard, oversight_flags
from server.tests.helpers import records


def bulk(recs: pd.DataFrame, courier=1) -> pd.DataFrame:
    """Record courier's deliveries on the hour, as a bulk-syncing scanner app would."""
    out = recs.copy()
    mine = out["courier_id"] == courier
    out.loc[mine, "delivered_at"] = out.loc[mine, "delivered_at"].dt.ceil("60min")
    return out


class QualityTests(unittest.TestCase):
    def test_clean_data_triggers_nothing(self):
        recs = records(days=3)
        guard = DataGuard().fit(recs)
        cleaned, report = guard.clean(recs, mode="train")
        self.assertEqual(report["duplicates_dropped"], 0)
        self.assertEqual(report["coordinates_repaired"], 0)
        self.assertEqual(report["bulk_scanned_rows"], 0)
        self.assertEqual(len(cleaned), len(recs))

    def test_exact_copies_are_removed(self):
        recs = records(days=1)
        copies = recs.iloc[:3].assign(order_id=recs["order_id"].max() + 1 + np.arange(3))
        self.assertEqual(int(duplicate_records(pd.concat([recs, copies], ignore_index=True)).sum()), 3)

    def test_far_coordinates_repaired_to_area_point(self):
        recs = records(days=2)
        guard = DataGuard().fit(recs)
        bad = recs.copy()
        bad.loc[0, "lat"] += 0.05                                     # ~5.5 km off
        cleaned, report = guard.clean(bad, mode="train")
        self.assertEqual(report["coordinates_repaired"], 1)
        self.assertAlmostEqual(cleaned.loc[0, "lat"], guard.reference.loc[recs.loc[0, "aoi_id"], "lat"])

    def test_bulk_scans_quarantined_in_training_flagged_in_serving(self):
        recs = bulk(records(days=2, per_day=8))
        self.assertTrue(bulk_scanned_courier_days(recs, 0.3)[recs["courier_id"] == 1].all())
        guard = DataGuard().fit(recs)
        train, report = guard.clean(recs, mode="train")
        self.assertFalse((train["courier_id"] == 1).any())
        serve, _ = guard.clean(recs, mode="serve")
        self.assertTrue(serve.loc[serve["courier_id"] == 1, "guard_bulk_scan"].any())
        self.assertFalse(serve.loc[serve["courier_id"] == 2, "guard_bulk_scan"].any())

    def test_serving_bulk_flag_is_causal(self):
        recs = bulk(records(days=1, per_day=8))
        share = running_bulk_share(recs)
        later = recs.copy()
        last = later["delivered_at"] == later.loc[later["courier_id"] == 1, "delivered_at"].max()
        later.loc[last, "delivered_at"] += pd.Timedelta(hours=3)        # change only the final batch
        early = (recs["delivered_at"] < recs.loc[last, "delivered_at"].min()).to_numpy()
        np.testing.assert_allclose(share[early], running_bulk_share(later)[early])

    def test_oversight_flags(self):
        live = pd.DataFrame({"feed_age_min": [10.0, 90.0], "cur_row": [0, 1]})
        packages = pd.DataFrame({"guard_bulk_scan": [False, True]})
        flags = oversight_flags(live, packages)
        self.assertEqual(flags["flag_review"].tolist(), [False, True])
        self.assertEqual(flags["flag_stale_feed"].tolist(), [False, True])


if __name__ == "__main__":
    unittest.main()
