import unittest

import numpy as np
import pandas as pd

from server.pipeline.evaluate import by_time_remaining, error_summary, evaluate_predictions, route_hit_rates, route_order_agreement


class EvaluateTests(unittest.TestCase):
    def test_error_summary(self):
        out = error_summary(np.array([10.0, 50.0]), np.array([20.0, 50.0]))
        self.assertEqual(out["mae"], 5.0)
        self.assertEqual(out["within_30_pct"], 100.0)

    def test_horizon_buckets_use_actual_time(self):
        out = by_time_remaining(np.array([10.0, 45.0, 300.0]), np.array([10.0, 45.0, 0.0]))
        self.assertEqual(out["under_30_min"]["mae"], 0.0)
        self.assertEqual(out["3_to_24_hours"]["mae"], 300.0)

    def test_route_metrics_perfect_and_reversed(self):
        rows = pd.DataFrame({"event": [0, 0, 0], "n_pending": [3] * 3, "remaining_min": [10.0, 20.0, 30.0]})
        self.assertEqual(route_hit_rates(rows.assign(route_score=[1, 2, 3])), (100.0, 100.0))
        self.assertAlmostEqual(route_order_agreement(rows.assign(route_score=[3, 2, 1])), -1.0)

    def test_evaluate_predictions_reports_review_split(self):
        rows = pd.DataFrame(
            {
                "s": ["a"] * 3,
                "courier": ["1"] * 3,
                "n_pending": [3] * 3,
                "route_ahead": [0, 1, 2],
                "actual": [10.0, 20.0, 30.0],
                "minutes_remaining": [10.0, 20.0, 60.0],
                "needs_review": [False, False, True],
                "model_used": ["standard", "standard", "staleness"],
            }
        )
        out = evaluate_predictions(rows)
        self.assertEqual(out["overall"]["mae"], 10.0)
        self.assertEqual(out["route"]["next_stop_pct"], 100.0)
        self.assertEqual(out["review"]["mae_flagged"], 30.0)
        self.assertEqual(out["review"]["mae_not_flagged"], 0.0)


if __name__ == "__main__":
    unittest.main()
