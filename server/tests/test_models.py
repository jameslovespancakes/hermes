import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from server.config import ROUTE_INPUT_COLS
from server.models.bundle import ModelBundle
from server.models.encoding import encode, fit_schema
from server.models.eta import fit_eta, predict_eta
from server.models.route import _fit, add_route_outputs, courier_day_folds, trainable_events


class EncodingTests(unittest.TestCase):
    def test_vocabulary_from_training_rows_only(self):
        train = pd.DataFrame({"courier_id": pd.Categorical(["yt:1", "yt:2"]), "x": [1.0, 2.0]})
        later = pd.DataFrame({"courier_id": pd.Categorical(["yt:3"]), "x": [3.0]})
        schema = fit_schema(train, ["courier_id", "x"])
        self.assertEqual(schema, {"courier_id": ["yt:1", "yt:2"]})
        self.assertTrue(encode(later, ["courier_id", "x"], schema)["courier_id"].isna().all())


class RouteTests(unittest.TestCase):
    def live(self):
        return pd.DataFrame({"courier_s": ["yt:1"] * 4 + ["yt:2"] * 2, "day": ["05-01", "05-01", "05-02", "05-02", "05-01", "05-01"],
                             "event": [0, 0, 1, 1, 2, 2],
                             "s": pd.to_datetime(["2000-05-01 09:00"] * 2 + ["2000-05-02 09:00"] * 2 + ["2000-05-01 10:00"] * 2),
                             "_delivered_at": pd.to_datetime(["2000-05-01 10:00", "2000-05-01 11:00", "2000-05-03 10:00", "2000-05-02 11:00",
                                                              "2000-05-01 11:00", "2000-05-01 12:00"]),
                             "n_pending": [2.0] * 6, "pace_today_min": [10.0] * 6,
                             "hab_courier_usual_shift_hours": [8.0] * 6, "hab_courier_usual_deliveries_per_day": [40.0] * 6})

    def test_courier_day_stays_in_one_fold(self):
        live = self.live()
        folds = courier_day_folds(live)
        self.assertEqual(live.assign(f=folds).groupby(["courier_s", "day"])["f"].nunique().max(), 1)
        np.testing.assert_array_equal(folds, courier_day_folds(live))

    def test_events_with_late_outcomes_are_not_trainable(self):
        trainable = trainable_events(self.live(), pd.Timestamp("2000-05-03"))
        np.testing.assert_array_equal(trainable, [True, True, False, False, True, True])

    def test_route_outputs_rank_within_event(self):
        out = add_route_outputs(self.live(), np.array([0.9, 0.1, 0.2, 0.3, 0.5, 0.4]))
        np.testing.assert_array_equal(out["route_ahead"], [1, 0, 0, 1, 1, 0])
        np.testing.assert_allclose(out["route_ahead_x_pace"], [20, 10, 10, 20, 20, 10])


class FitTests(unittest.TestCase):
    """Real (tiny) fits: catches missing runtime dependencies of the LightGBM model interface."""

    def test_eta_model_fits_and_predicts_non_negative(self):
        rng = np.random.default_rng(0)
        rows = pd.DataFrame({"courier_id": pd.Categorical(rng.choice(["yt:1", "yt:2"], 400)), "x": rng.uniform(0, 10, 400)})
        rows["remaining_min"] = rows["x"] * 6 + rng.uniform(0, 5, 400)
        model, schema = fit_eta(rows.iloc[:300], rows.iloc[300:], ["courier_id", "x"])
        predicted = predict_eta(model, schema, rows.iloc[300:], ["courier_id", "x"])
        self.assertTrue((predicted >= 0).all())
        self.assertLess(np.abs(predicted - rows["remaining_min"].iloc[300:]).mean(), 10)

    def test_route_model_fits(self):
        rng = np.random.default_rng(1)
        rows = pd.DataFrame(rng.uniform(0, 1, (200, len(ROUTE_INPUT_COLS))), columns=ROUTE_INPUT_COLS)
        rows["true_pos"] = rows[ROUTE_INPUT_COLS[0]]
        self.assertEqual(len(_fit(rows).predict(rows[ROUTE_INPUT_COLS])), 200)


class BundleTests(unittest.TestCase):
    def test_round_trip_and_type_check(self):
        bundle = ModelBundle(city="yt", route_model=None, eta_model=None, eta_columns=["x"], eta_schema={},
                             habit_columns=[], trained_through="09-01")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.pkl"
            digest = bundle.save(path)
            self.assertEqual(len(digest), 64)
            self.assertEqual(ModelBundle.load(path).eta_columns, ["x"])
            ModelBundle(city="x", route_model=None, eta_model=None, eta_columns=[], eta_schema={}, habit_columns=[],
                        trained_through="").save(path)
            import pickle
            path.write_bytes(pickle.dumps({"not": "a bundle"}))
            with self.assertRaises(TypeError):
                ModelBundle.load(path)


if __name__ == "__main__":
    unittest.main()
