import unittest

import numpy as np
import pandas as pd

from server.quality.config import CleanMode
from server.quality.detectors import bulk_scanned_courier_days, duplicate_records, running_bulk_share
from server.quality.guard import DataGuard, data_issues
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
        guard = DataGuard.fit(recs)
        cleaned, report = guard.clean(recs, mode=CleanMode.TRAIN)
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
        guard = DataGuard.fit(recs)
        bad = recs.copy()
        bad.loc[0, "lat"] += 0.05  # ~5.5 km off
        cleaned, report = guard.clean(bad, mode=CleanMode.TRAIN)
        self.assertEqual(report["coordinates_repaired"], 1)
        self.assertAlmostEqual(cleaned.loc[0, "lat"], guard.reference.loc[recs.loc[0, "aoi_id"], "lat"])

    def test_bulk_scans_quarantined_in_training_flagged_in_serving(self):
        recs = bulk(records(days=2, per_day=8))
        self.assertTrue(bulk_scanned_courier_days(recs, 0.3)[recs["courier_id"] == 1].all())
        guard = DataGuard.fit(recs)
        train, report = guard.clean(recs, mode=CleanMode.TRAIN)
        self.assertFalse((train["courier_id"] == 1).any())
        serve, _ = guard.clean(recs, mode=CleanMode.SERVE)
        self.assertTrue(serve.loc[serve["courier_id"] == 1, "guard_bulk_scan"].any())
        self.assertFalse(serve.loc[serve["courier_id"] == 2, "guard_bulk_scan"].any())

    def test_serving_bulk_flag_is_causal(self):
        recs = bulk(records(days=1, per_day=8))
        share = running_bulk_share(recs)
        later = recs.copy()
        last = later["delivered_at"] == later.loc[later["courier_id"] == 1, "delivered_at"].max()
        later.loc[last, "delivered_at"] += pd.Timedelta(hours=3)  # change only the final batch
        early = (recs["delivered_at"] < recs.loc[last, "delivered_at"].min()).to_numpy()
        np.testing.assert_allclose(share[early], running_bulk_share(later)[early])

    def test_data_issues_in_priority_order_with_reasons(self):
        live = pd.DataFrame(
            {
                "feed_age_min": [10.0, 90.0, 5.0, 900.0],
                "upload_lag_min": [0.0, 0.0, 60.0, 0.0],
                "n_done_today": [3, 3, 3, 0],
                "row": [0, 1, 0, 1],
                "cur_row": [0, 1, 0, 0],
            }
        )
        packages = pd.DataFrame({"guard_bulk_scan": [False, True], "guard_moved_km": [np.nan, 2.4], "guard_resent": [False, True]})
        out = data_issues(live, packages)
        self.assertEqual(out["issues"].tolist(), [[], ["silent", "bulk", "moved", "resent"], ["lagging"], ["moved", "resent"]])
        self.assertEqual(out["reasons"][1][0], "No scans from the courier for 90 min")
        self.assertEqual(out["reasons"][3][0], "Address was 2.4 km off its area and was moved")

    def test_serving_marks_moved_addresses_and_removed_copies(self):
        recs = records(days=2)
        bad = recs.copy()
        bad.loc[0, "lat"] += 0.05
        copy = bad.iloc[[1]].assign(order_id=bad["order_id"].max() + 1)
        cleaned, _ = DataGuard.fit(recs).clean(pd.concat([bad, copy], ignore_index=True), mode=CleanMode.SERVE)
        self.assertGreater(cleaned.loc[cleaned["order_id"] == recs.loc[0, "order_id"], "guard_moved_km"].iloc[0], 5.0)
        self.assertTrue(cleaned.loc[cleaned["order_id"] == recs.loc[1, "order_id"], "guard_resent"].iloc[0])
        self.assertEqual(int(cleaned["guard_resent"].sum()), 1)


if __name__ == "__main__":
    unittest.main()
