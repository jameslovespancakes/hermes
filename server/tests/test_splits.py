import unittest

import pandas as pd

from server.config import Split
from server.data.splits import fit_rows, stop_rows, test_rows

SPLIT = Split(start="05-01", fit_end="05-03", stop_end="05-04", test_end="05-05")


def frame():
    s = pd.date_range("2000-05-01", "2000-05-04 23:00", freq="6h")
    return pd.DataFrame({"s": s, "_delivered_at": s + pd.Timedelta(hours=20)})


class SplitTests(unittest.TestCase):
    def test_fit_rows_need_outcomes_known_by_cutoff(self):
        rows = fit_rows(frame(), SPLIT, sample=None)
        self.assertTrue((rows["s"] < SPLIT.fit_cutoff).all())
        self.assertTrue((rows["_delivered_at"] < SPLIT.fit_cutoff).all())

    def test_windows_are_disjoint_and_ordered(self):
        f = frame()
        fit, stop, test = fit_rows(f, SPLIT, sample=None), stop_rows(f, SPLIT), test_rows(f, SPLIT)
        self.assertTrue(fit["s"].max() < stop["s"].min() <= stop["s"].max() < test["s"].min())
        self.assertTrue((stop["_delivered_at"] < SPLIT.stop_cutoff).all())

    def test_test_window_keeps_late_outcomes(self):
        test = test_rows(frame(), SPLIT)
        self.assertTrue((test["_delivered_at"] >= SPLIT.data_cutoff).any())


if __name__ == "__main__":
    unittest.main()
