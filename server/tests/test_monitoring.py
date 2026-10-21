import unittest

import numpy as np
import pandas as pd

from server.quality.contract import city_bounds, daily_report, validate
from server.quality.drift import calibrate, drift_report, level, psi
from server.quality.gating import audit_sample, audited_gate, gate
from server.tests.helpers import records


class ContractTests(unittest.TestCase):
    def test_clean_batch_passes_every_expectation(self):
        recs = records(days=2)
        results = validate(recs, city_bounds(recs))
        self.assertTrue(results and all(e.passed for e in results), [e for e in results if not e.passed])

    def test_bulk_synced_and_resent_batch_fails(self):
        recs = records(days=1, per_day=8)
        bad = recs.assign(delivered_at=recs["delivered_at"].dt.ceil("60min"))
        bad = pd.concat([bad, bad.iloc[:4].assign(order_id=bad["order_id"].max() + 1 + np.arange(4))], ignore_index=True)
        failed = {e.name for e in validate(bad, city_bounds(recs)) if not e.passed}
        self.assertIn("courier timestamps not repeated", failed)
        self.assertIn("delivery times not bunched on the hour", failed)
        self.assertIn("no re-sent records", failed)

    def test_missing_columns_fail_fast(self):
        out = validate(records(days=1).drop(columns=["aoi_id"]), (0, 90, 0, 180))
        self.assertFalse(out[0].passed)

    def test_daily_report_has_one_row_per_day(self):
        recs = records(days=3)
        self.assertEqual(len(daily_report(recs, city_bounds(recs))), 3)


class DriftTests(unittest.TestCase):
    def test_same_distribution_is_stable_and_shift_alerts(self):
        rng = np.random.default_rng(0)
        reference = rng.normal(0, 1, 5000)
        self.assertLess(psi(reference, rng.normal(0, 1, 5000)), 0.02)
        self.assertGreater(psi(reference, rng.normal(1.0, 1, 5000)), 0.25)
        self.assertEqual([level(0.05), level(0.2), level(0.4)], ["stable", "watch", "act"])

    def test_missing_values_count_as_drift(self):
        reference = np.arange(1000, dtype=float)
        current = np.where(np.arange(1000) % 2 == 0, np.nan, reference)
        self.assertGreater(psi(reference, current), 0.25)

    def test_shift_away_from_a_constant_reference_is_detected(self):
        reference = np.zeros(1000)  # e.g. feed age on a healthy feed
        self.assertGreater(psi(reference, np.r_[np.zeros(600), np.full(400, 45.0)]), 0.25)
        self.assertLess(psi(reference, np.zeros(1000)), 0.01)

    def test_calibration_raises_thresholds_for_naturally_drifting_inputs(self):
        rng = np.random.default_rng(1)
        june = pd.DataFrame({"steady": rng.normal(0, 1, 5000), "seasonal": rng.normal(0, 1, 5000)})
        may = pd.DataFrame({"steady": rng.normal(0, 1, 5000), "seasonal": rng.normal(0.8, 1, 5000)})
        limits = calibrate(june, may, ["steady", "seasonal"])
        self.assertEqual(limits["steady"]["act"], 0.25)
        self.assertGreater(limits["seasonal"]["act"], 0.25)
        july = pd.DataFrame({"steady": rng.normal(0, 1, 5000), "seasonal": rng.normal(0.8, 1, 5000)})
        self.assertEqual(drift_report(june, july, ["steady", "seasonal"], limits)["alert"], "stable")

    def test_report_names_worst_feature(self):
        ref = pd.DataFrame({"a": np.arange(1000.0), "b": np.arange(1000.0)})
        cur = pd.DataFrame({"a": np.arange(1000.0), "b": np.arange(1000.0) + 500})
        out = drift_report(ref, cur, ["a", "b"])
        self.assertEqual(out["worst_feature"], "b")
        self.assertEqual(out["alert"], "act")


class GatingTests(unittest.TestCase):
    def test_promotes_only_a_better_challenger(self):
        self.assertTrue(gate(np.full(600, 60.0), np.full(600, 55.0)).promote)
        decision = gate(np.full(600, 60.0), np.full(600, 70.0))
        self.assertFalse(decision.promote)
        self.assertIn("keep champion", decision.reason)

    def test_requires_enough_audited_and_paired_predictions(self):
        self.assertFalse(gate(np.full(10, 60.0), np.full(10, 1.0)).promote)
        with self.assertRaises(ValueError):
            gate(np.ones(600), np.ones(599))

    def test_audit_sample_is_deterministic_per_package(self):
        ids = pd.Series(np.repeat(np.arange(2000), 3))
        a, b = audit_sample(ids, 0.1), audit_sample(ids, 0.1)
        pd.testing.assert_series_equal(a, b)
        self.assertEqual(pd.DataFrame({"id": ids, "a": a}).groupby("id")["a"].nunique().max(), 1)
        self.assertAlmostEqual(a.mean(), 0.1, delta=0.03)

    def test_audited_gate_uses_only_audited_packages_with_known_outcomes(self):
        n = 20_000
        rows = pd.DataFrame({"s": pd.Timestamp("2000-09-01"), "order_id": np.arange(n), "actual": 30.0})
        truth = pd.Series(pd.Timestamp("2000-09-01 10:00"), index=np.arange(n))
        champion, challenger = rows.assign(minutes_remaining=40.0), rows.assign(minutes_remaining=35.0)
        decision = audited_gate(champion, challenger, truth, pd.Timestamp("2000-09-02"))
        self.assertTrue(decision.promote)
        self.assertAlmostEqual(decision.audited_predictions / n, 0.1, delta=0.02)
        self.assertEqual(audited_gate(champion, challenger, truth, pd.Timestamp("2000-09-01")).audited_predictions, 0)


if __name__ == "__main__":
    unittest.main()
