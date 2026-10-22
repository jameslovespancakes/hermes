"""Road routing on LaDe's OpenStreetMap road network (couriers ride e-bikes: no motorways, every road both ways)."""

import re
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree

from server.config import RAW_DIR
from server.features.geometry import haversine_km

EARTH_M = 6378137.0
EXCLUDED = {"motorway", "motorway_link"}


def mercator_to_wgs84(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    lng = np.degrees(x / EARTH_M)
    lat = np.degrees(2 * np.arctan(np.exp(y / EARTH_M)) - np.pi / 2)
    return lng, lat


def parse_lines(text: str) -> list[np.ndarray]:
    """Every polyline in a WKT LINESTRING or MULTILINESTRING, as (x, y) arrays."""
    return [np.array([pair.split() for pair in part.split(",")], dtype=float) for part in re.findall(r"\(([^()]+)\)", text)]


@dataclass
class RoadGraph:
    lng: np.ndarray
    lat: np.ndarray
    graph: csr_matrix
    tree: cKDTree
    nodes: np.ndarray

    @classmethod
    def from_lines(cls, lines: list[np.ndarray]) -> "RoadGraph":
        """Graph from road polylines given as (lng, lat) arrays; shared vertices join roads."""
        points = np.concatenate(lines)
        node, index = np.unique(np.round(points, 7), axis=0, return_inverse=True)
        index = index.ravel()
        ends = np.cumsum([len(line) for line in lines])
        start = np.delete(np.arange(len(points) - 1), ends[:-1] - 1)
        a, b = index[start], index[start + 1]
        keep = a != b
        a, b = a[keep], b[keep]
        metres = haversine_km(node[a, 1], node[a, 0], node[b, 1], node[b, 0]) * 1000
        graph = csr_matrix((metres, (a, b)), shape=(len(node), len(node)))
        _, component = connected_components(graph, directed=False)
        largest = np.flatnonzero(component == np.bincount(component).argmax())
        scale = np.cos(np.radians(node[:, 1].mean()))
        return cls(node[:, 0], node[:, 1], graph, cKDTree(np.c_[node[largest, 0] * scale, node[largest, 1]]), largest)

    @classmethod
    def load(cls, city: str) -> "RoadGraph":
        roads = pd.read_csv(RAW_DIR / f"roads_{city}.csv")
        roads = roads.loc[~roads["fclass"].isin(EXCLUDED)]
        lines = []
        for text in roads["geometry"]:
            for xy in parse_lines(text):
                lng, lat = mercator_to_wgs84(xy[:, 0], xy[:, 1])
                lines.append(np.c_[lng, lat])
        return cls.from_lines(lines)

    def snap(self, points: np.ndarray) -> np.ndarray:
        scale = np.cos(np.radians(self.lat.mean()))
        _, nearest = self.tree.query(np.c_[points[:, 0] * scale, points[:, 1]])
        return self.nodes[nearest]

    def leg(self, source: int, target: int) -> list[int]:
        """Shortest road path between two nodes; the search grows from a radius around the straight line."""
        straight = haversine_km(self.lat[source], self.lng[source], self.lat[target], self.lng[target]) * 1000
        limit = 3 * straight + 2000
        while True:
            _, previous = dijkstra(self.graph, directed=False, indices=source, limit=limit, return_predecessors=True)
            if previous[target] >= 0 or source == target:
                break
            limit *= 4
        nodes = [target]
        while nodes[-1] != source:
            nodes.append(previous[nodes[-1]])
        return nodes[::-1]

    def path(self, points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        """Road path through (lng, lat) points in order, from each point to its nearest road and back."""
        waypoints = np.asarray(points, dtype=float)
        snapped = self.snap(waypoints)
        out = [tuple(waypoints[0])]
        for leg, (source, target) in enumerate(zip(snapped[:-1], snapped[1:], strict=True)):
            out += [(self.lng[n], self.lat[n]) for n in self.leg(source, target)]
            out.append(tuple(waypoints[leg + 1]))
        return [(float(lng), float(lat)) for lng, lat in out]
