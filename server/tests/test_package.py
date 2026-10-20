import unittest

import numpy as np
import pandas as pd

from server.config import PACKAGE_COLS
from server.features.package import package_features
from server.tests.helpers import records


class PackageFeatureTests(unittest.TestCase):
    def test_ids_are_city_scoped(self):
        a = package_features(records(days=1), "yt")
        b = package_features(records(days=1), "sh")
        self.assertTrue(str(a["courier_id"].iloc[0]).startswith("yt:"))
        self.assertNotEqual(a["courier_id"].iloc[0], b["courier_id"].iloc[0])

    def test_gps_recorded_after_acceptance_is_ignored(self):
        recs = records(days=1)
        recs.loc[0, "accept_gps_at"] = recs.loc[0, "accepted_at"] + pd.Timedelta(minutes=5)
        f = package_features(recs, "yt")
        self.assertTrue(np.isnan(f.loc[0, "straight_line_km"]))
        self.assertEqual(f.loc[0, "accept_gps_missing"], 1)

    def test_outcomes_only_as_underscore_metadata(self):
        f = package_features(records(days=1), "yt")
        for column in PACKAGE_COLS:
            self.assertFalse(column.startswith("_"))
        self.assertNotIn("delivered_at", f.columns)
        self.assertIn("_delivered_at", f.columns)

    def test_model_inputs_do_not_depend_on_delivery_time(self):
        recs = records(days=1)
        changed = recs.copy()
        changed["delivered_at"] = changed["delivered_at"] + pd.Timedelta(hours=3)
        pd.testing.assert_frame_equal(package_features(recs, "yt")[PACKAGE_COLS], package_features(changed, "yt")[PACKAGE_COLS])


if __name__ == "__main__":
    unittest.main()
