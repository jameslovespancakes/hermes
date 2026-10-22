import unittest

import numpy as np

from server.features.geometry import haversine_km
from server.serving.roads import mercator_to_wgs84, parse_lines
from server.tests.helpers import street_grid


class RoadTests(unittest.TestCase):
    def test_path_follows_streets_between_corners(self):
        grid = street_grid()
        path = np.array(grid.path([(121.0, 37.0), (121.008, 37.008)]))
        self.assertEqual(tuple(path[0]), (121.0, 37.0))
        self.assertEqual(tuple(path[-1]), (121.008, 37.008))
        steps = np.abs(np.diff(path, axis=0))
        self.assertTrue(((steps[:, 0] < 1e-9) | (steps[:, 1] < 1e-9)).all())

    def test_path_visits_stops_in_order(self):
        stops = [(121.0, 37.0), (121.008, 37.0), (121.0, 37.004)]
        path = street_grid().path(stops)
        positions = [path.index(stop) for stop in stops]
        self.assertEqual(positions, sorted(positions))

    def test_off_road_points_join_the_nearest_street(self):
        path = np.array(street_grid().path([(121.0011, 37.0003), (121.0071, 37.0059)]))
        legs = haversine_km(path[:-1, 1], path[:-1, 0], path[1:, 1], path[1:, 0])
        self.assertLess(legs[0], 0.1)

    def test_parses_multilinestrings_in_web_mercator(self):
        lines = parse_lines("MULTILINESTRING ((0 0, 1 1), (2 2, 3 3, 4 4))")
        self.assertEqual([len(line) for line in lines], [2, 3])
        lng, lat = mercator_to_wgs84(np.array([13513000.0]), np.array([4510000.0]))
        self.assertAlmostEqual(float(lng[0]), 121.39, places=2)
        self.assertAlmostEqual(float(lat[0]), 37.53, places=1)


if __name__ == "__main__":
    unittest.main()
