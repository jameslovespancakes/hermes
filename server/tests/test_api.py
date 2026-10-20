import unittest

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from server.api.app import create_app
from server.models.bundle import ModelBundle
from server.serving.predictor import LiveETAPredictor
from server.tests.helpers import records


class _Constant:
    def __init__(self, value):
        self.value = value

    def predict(self, X):
        return np.full(len(X), self.value, dtype=float)


def client():
    bundle = ModelBundle(city="yt", route_model=_Constant(0.0), eta_model=_Constant(30.0), eta_columns=["n_pending"],
                         eta_schema={}, habit_columns=[], trained_through="09-01")
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
