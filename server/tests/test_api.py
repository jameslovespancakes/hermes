import unittest

import pandas as pd
from fastapi.testclient import TestClient

from server.api.app import create_app
from server.pipeline.features import live_table, package_table
from server.quality.monitor import fit_baseline
from server.serving.predictor import LiveETAPredictor
from server.tests.helpers import constant_bundle, records


def client():
    bundle = constant_bundle(eta=30.0)
    return TestClient(create_app(predictor=LiveETAPredictor(bundle), records=records(days=2, couriers=(1, 2), per_day=6)))


class ApiTests(unittest.TestCase):
    def test_health(self):
        with client() as c:
            body = c.get("/health").json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["city"], "yt")
        self.assertEqual(body["records"], 24)

    def test_predict_returns_held_packages(self):
        recs = records(days=2, couriers=(1, 2), per_day=6)
        at = recs.loc[recs["courier_id"] == 1, "delivered_at"].iloc[8] + pd.Timedelta(minutes=1)
        with client() as c:
            response = c.post("/predict", json={"courier_id": 1, "at": at.strftime("%m-%d %H:%M:%S")})
        self.assertEqual(response.status_code, 200)
        packages = response.json()["packages"]
        self.assertGreater(len(packages), 0)
        self.assertTrue(all(p["minutes_remaining"] == 30.0 for p in packages))
        self.assertEqual([p["predicted_position"] for p in packages], sorted(p["predicted_position"] for p in packages))

    def test_predict_reports_model_used_and_review_flags(self):
        recs = records(days=2, couriers=(1, 2), per_day=6)
        at = recs.loc[recs["courier_id"] == 1, "delivered_at"].iloc[8] + pd.Timedelta(minutes=1)
        with client() as c:
            package = c.post("/predict", json={"courier_id": 1, "at": at.strftime("%m-%d %H:%M:%S")}).json()["packages"][0]
        self.assertEqual(package["model_used"], "standard")
        self.assertFalse(package["needs_review"])
        self.assertEqual(package["review_reasons"], [])

    def test_data_health_needs_a_monitoring_baseline(self):
        with client() as c:
            self.assertEqual(c.get("/data-health", params={"at": "05-02 12:00:00"}).status_code, 409)

    def test_data_health_reports_contract_and_drift(self):
        recs = records(days=4, couriers=(1, 2, 3), per_day=8)
        packages = package_table(recs, "yt")
        live = live_table(packages, pd.Timestamp("2000-05-03"))
        bundle = constant_bundle(eta=30.0, monitor=fit_baseline(live, recs, pd.Timestamp("2000-05-03")))
        with TestClient(create_app(predictor=LiveETAPredictor(bundle), records=recs)) as c:
            body = c.get("/data-health", params={"at": "05-04 10:00:00"}).json()
        self.assertTrue(body["contract_passed"])
        self.assertGreater(body["records_checked"], 0)
        self.assertIn(body["status"], {"ok", "watch", "act"})
        self.assertIn("feed_age_min", body["drift_psi"])

    def test_courier_with_nothing_held_returns_empty_list(self):
        with client() as c:
            response = c.post("/predict", json={"courier_id": 99, "at": "05-01 12:00:00"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["packages"], [])

    def test_couriers_endpoint_lists_loads(self):
        with client() as c:
            loads = c.get("/couriers", params={"at": "05-01 08:30:00"}).json()
        self.assertTrue(all(row["packages_held"] > 0 for row in loads))

    def test_bad_time_is_rejected(self):
        with client() as c:
            self.assertEqual(c.post("/predict", json={"courier_id": 1, "at": "2026-09-20"}).status_code, 422)
            self.assertEqual(c.post("/predict", json={"courier_id": 1, "at": "02-30 10:00:00"}).status_code, 422)


if __name__ == "__main__":
    unittest.main()
