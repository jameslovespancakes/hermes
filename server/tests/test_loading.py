import unittest

import pandas as pd

from server.data.loading import clean_records, parse_time
from server.tests.helpers import raw_log


class LoadingTests(unittest.TestCase):
    def test_parse_time_uses_anchor_year_and_flags_bad_values(self):
        out = parse_time(pd.Series(["06-18 16:21:00", "not a time"]))
        self.assertEqual(out.iloc[0], pd.Timestamp("2000-06-18 16:21:00"))
        self.assertTrue(pd.isna(out.iloc[1]))

    def test_removes_only_undefined_labels(self):
        raw = raw_log(days=1, couriers=(1,), per_day=6)
        raw.loc[0, "order_id"] = None  # missing id
        raw.loc[2, "order_id"] = raw.loc[1, "order_id"]  # duplicate id (both copies dropped)
        raw.loc[3, "delivery_time"] = "garbage"  # unparseable
        raw.loc[4, "delivery_time"] = "04-01 00:00:00"  # negative duration
        raw.loc[5, "delivery_time"] = "05-09 08:00:00"  # very long (kept)
        frame, exclusions = clean_records(raw)
        self.assertEqual(
            exclusions,
            {"missing_order_id": 1, "duplicate_order_id_all_occurrences": 2, "unparseable_accept_or_delivery_time": 1, "negative_duration": 1},
        )
        self.assertEqual(len(frame), 1)
        self.assertGreater(frame["duration_minutes"].iloc[0], 7 * 24 * 60)

    def test_sorted_by_acceptance(self):
        frame, _ = clean_records(raw_log(days=3).sample(frac=1, random_state=1))
        self.assertTrue(frame["accepted_at"].is_monotonic_increasing)


if __name__ == "__main__":
    unittest.main()
