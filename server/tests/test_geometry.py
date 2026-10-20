import unittest

import numpy as np

from server.features.geometry import greedy_tour, haversine_km, rank_fraction


class GeometryTests(unittest.TestCase):
    def test_haversine_one_degree_latitude(self):
        self.assertAlmostEqual(float(haversine_km(0.0, 0.0, 1.0, 0.0)), 111.19, delta=0.05)
        self.assertEqual(float(haversine_km(37.0, 121.0, 37.0, 121.0)), 0.0)

    def test_greedy_tour_visits_nearest_first(self):
        lat = np.array([0.0, 0.0, 0.0])
        lng = np.array([0.03, 0.01, 0.02])
        order, cumulative = greedy_tour(0.0, 0.0, lat, lng)
        np.testing.assert_array_equal(order, [2, 0, 1])
        self.assertTrue(np.all(np.diff(cumulative[np.argsort(order)]) > 0))

    def test_rank_fraction_keeps_nan(self):
        out = rank_fraction([3.0, np.nan, 1.0, 2.0])
        np.testing.assert_allclose(out[[0, 2, 3]], [1.0, 0.0, 0.5])
        self.assertTrue(np.isnan(out[1]))


if __name__ == "__main__":
    unittest.main()
