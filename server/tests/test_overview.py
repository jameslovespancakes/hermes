import unittest

import pandas as pd

from server.serving.overview import IssueRules, classify
from server.serving.predictor import courier_positions
from server.tests.helpers import app_client, records

AT = pd.Timestamp("2000-05-02 10:00")


def frame(**columns) -> pd.DataFrame:
    """One prediction row per parcel with neutral defaults; override any column per test."""
    n = len(next(iter(columns.values())))
    base = {
        "order_id": list(range(n)),
        "predicted_delivery_at": [AT + pd.Timedelta(minutes=30)] * n,
        "minutes_remaining": [30.0] * n,
        "data_issues": [[] for _ in range(n)],
        "review_reasons": [[] for _ in range(n)],
        "dist_from_courier_km": [1.0] * n,
    }
    base.update(columns)
    return pd.DataFrame(base)


def before(etas) -> pd.DataFrame:
    return pd.DataFrame({"order_id": range(len(etas)), "predicted_delivery_at": etas})


class ClassifyTests(unittest.TestCase):
    rules = IssueRules(late_slip_min=90, early_jump_min=60, far_from_courier_km=15)

    def test_steady_estimates_raise_nothing(self):
        out = classify(frame(order_id=[0]), before([AT + pd.Timedelta(minutes=25)]), self.rules)
        self.assertEqual(out["slip_min"].tolist(), [5.0])
        self.assertIsNone(out["issue"][0])
        self.assertEqual(out["reasons"][0], [])

    def test_large_slip_is_late(self):
        out = classify(frame(order_id=[0]), before([AT - pd.Timedelta(minutes=70)]), self.rules)
        self.assertEqual(out["issue"][0], "late")
        self.assertEqual(out["reasons"][0], ["ETA slipped 100 min in the last hour"])

    def test_implausible_inputs_are_suspect(self):
        out = classify(
            frame(order_id=[0, 1], dist_from_courier_km=[20.0, 1.0]),
            before([AT + pd.Timedelta(minutes=30), AT + pd.Timedelta(minutes=100)]),
            self.rules,
        )
        self.assertEqual(out["issue"].tolist(), ["suspect", "suspect"])
        self.assertEqual(out["reasons"][0], ["Parcel is 20 km from the courier"])
        self.assertEqual(out["reasons"][1], ["ETA jumped 70 min earlier in the last hour"])

    def test_parcel_guard_flags_win_and_courier_feed_flags_stay_off_the_parcel(self):
        out = classify(
            frame(
                order_id=[0],
                data_issues=[["silent", "moved"]],
                review_reasons=[["No scans from the courier for 70 min", "Address was 2.0 km off its area and was moved"]],
                dist_from_courier_km=[20.0],
            ),
            before([AT - pd.Timedelta(minutes=90)]),
            self.rules,
        )
        self.assertEqual(out["issue"][0], "moved")
        self.assertEqual(out["reasons"][0], ["Address was 2.0 km off its area and was moved"])

    def test_parcels_new_since_the_baseline_have_no_slip(self):
        out = classify(frame(order_id=[0]), before([]), self.rules)
        self.assertTrue(pd.isna(out["slip_min"][0]))
        self.assertIsNone(out["issue"][0])


class PositionTests(unittest.TestCase):
    def test_last_drop_today_else_last_acceptance(self):
        recs = records(days=2, couriers=(1, 2), per_day=6)
        first = recs.loc[(recs["courier_id"] == 1) & (recs["delivered_at"].dt.day == 2)].sort_values("delivered_at").iloc[0]
        at = first["delivered_at"] + pd.Timedelta(minutes=1)
        where = courier_positions(recs, at)
        self.assertAlmostEqual(where.loc[1, "lat"], first["lat"])
        self.assertAlmostEqual(where.loc[1, "lng"], first["lng"])
        early = first["accepted_at"] + pd.Timedelta(minutes=1)
        self.assertAlmostEqual(courier_positions(recs, early).loc[1, "lat"], 37.0)


class OverviewApiTests(unittest.TestCase):
    def test_overview_lists_couriers_and_parcels(self):
        recs = records(days=2, couriers=(1, 2), per_day=6)
        at = recs.loc[recs["courier_id"] == 1, "delivered_at"].iloc[8] + pd.Timedelta(minutes=1)
        with app_client(recs=recs) as c:
            body = c.get("/api/overview", params={"city": "yt", "at": at.strftime("%m-%d %H:%M:%S")}).json()
        self.assertEqual(body["baseline_at"], (at - pd.Timedelta(hours=1)).strftime("%m-%d %H:%M:%S"))
        self.assertGreater(len(body["parcels"]), 0)
        self.assertEqual({c["courier_id"] for c in body["couriers"]}, {p["courier_id"] for p in body["parcels"]})
        parcel = body["parcels"][0]
        self.assertEqual(
            set(parcel),
            {
                "city",
                "order_id",
                "courier_id",
                "lat",
                "lng",
                "position",
                "accepted_at",
                "eta",
                "minutes_remaining",
                "baseline_eta",
                "slip_min",
                "issue",
                "reasons",
            },
        )
        self.assertIn(parcel["issue"], {None, "lagging", "silent", "bulk", "moved", "resent", "suspect", "late"})


if __name__ == "__main__":
    unittest.main()
