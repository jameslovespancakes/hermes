import unittest

import numpy as np
import pandas as pd

from server.quality.config import CleanMode
from server.quality.detectors import clock_offset_min, duplicate_records, record_weights, running_bulk_share, suspicious
from server.quality.guard import DataGuard, data_issues, minutes_since_area_visit
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
        self.assertEqual(report["clock_corrected_rows"], 0)
        self.assertEqual(report["mean_weight"], 1.0)
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

    def test_bulk_scans_count_less_in_training_and_are_flagged_in_serving(self):
        recs = bulk(records(days=2, per_day=8))
        guard = DataGuard.fit(recs)
        train, report = guard.clean(recs, mode=CleanMode.TRAIN)
        self.assertEqual(len(train), len(recs))
        self.assertLess(train.loc[train["courier_id"] == 1, "weight"].max(), train.loc[train["courier_id"] == 2, "weight"].min())
        serve, _ = guard.clean(recs, mode=CleanMode.SERVE)
        self.assertTrue(serve.loc[serve["courier_id"] == 1, "guard_bulk_scan"].any())
        self.assertFalse(serve.loc[serve["courier_id"] == 2, "guard_bulk_scan"].any())

    def test_clean_records_keep_full_weight(self):
        recs = records(days=3)
        self.assertFalse(suspicious(recs).any())
        self.assertTrue((record_weights(recs) == 1.0).all())

    def test_impossible_travel_is_suspicious(self):
        recs = records(days=1, couriers=(1,), per_day=4)
        recs.loc[recs.index[2], "lat"] += 0.2  # ~22 km away, minutes after the previous drop-off
        self.assertTrue(suspicious(recs).iloc[[2, 3]].all())

    def test_fast_device_clock_is_corrected_from_earlier_uploads_only(self):
        recs = records(days=1, couriers=(1,), per_day=8)
        fast = recs.assign(received_at=recs["delivered_at"] + pd.Timedelta(minutes=1))
        fast[["accepted_at", "delivered_at"]] += pd.Timedelta(minutes=20)
        accept, delivery = clock_offset_min(fast)
        np.testing.assert_allclose(delivery[3:], -19.0)
        self.assertTrue((delivery[:3] == 0).all())  # not judged before three uploads have arrived
        self.assertTrue((clock_offset_min(recs)[1] == 0).all())

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
                "at_current_aoi": [1, 1, 1, 1],
                "s": pd.Timestamp("2000-05-01 12:00"),
            }
        )
        packages = pd.DataFrame(
            {
                "guard_bulk_scan": [False, True],
                "guard_moved_km": [np.nan, 2.4],
                "guard_resent": [False, True],
                "guard_clock_min": [np.nan, 15.0],
                "courier_id": ["yt:1", "yt:1"],
                "aoi_id": ["yt:1", "yt:2"],
                "_accepted_at": pd.Timestamp("2000-05-01 08:00"),
                "_delivered_at": pd.NaT,
            }
        )
        guard = DataGuard(pd.DataFrame(columns=["lat", "lng"]), missed_after_min=60.0)
        out = data_issues(live, packages, guard)
        self.assertEqual(out["data_issues"].tolist(), [[], ["silent", "bulk", "clock", "moved", "resent"], ["lagging"], ["clock", "moved", "resent"]])
        self.assertEqual(out["review_reasons"][1][0], "No scans from the courier for 90 min")
        self.assertEqual(out["review_reasons"][3][1], "Address was 2.4 km off its area and was moved")
        self.assertEqual(data_issues(live, packages, None)["data_issues"].tolist()[1], ["silent"])

    def test_parcel_left_behind_in_a_visited_area_is_missed(self):
        packages = pd.DataFrame(
            {
                "courier_id": ["yt:1", "yt:1"],
                "aoi_id": ["yt:5", "yt:5"],
                "_accepted_at": pd.to_datetime(["2000-05-01 08:00", "2000-05-01 08:00"]),
                "_delivered_at": pd.to_datetime(["2000-05-01 09:00", pd.NaT]),
            }
        )
        live = pd.DataFrame({"row": [1, 1, 1], "s": pd.to_datetime(["2000-05-01 08:30", "2000-05-01 10:30", "2000-05-02 10:30"])})
        since = minutes_since_area_visit(live, packages)
        self.assertTrue(np.isnan(since[0]))  # not visited yet
        self.assertEqual(since[1], 90.0)
        self.assertTrue(np.isnan(since[2]))  # the visit was yesterday

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
