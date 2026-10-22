"""One city's live service: model, delivery log, road network, and the caches the dashboard relies on."""

import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from server.config import CITIES, MODEL_STORE
from server.data.loading import load_city
from server.features.geometry import gcj02_to_wgs84
from server.serving.overview import build_overview, city_predictions
from server.serving.predictor import LiveETAPredictor, at_moment
from server.serving.roads import RoadGraph

GRID = {pd.Timedelta(minutes=m) for m in range(6 * 60, 21 * 60 + 1, 15)}


class LruCache:
    """Thread-safe least-recently-used cache."""

    def __init__(self, size: int):
        self.size, self.lock = size, threading.Lock()
        self.items: OrderedDict = OrderedDict()

    def get(self, key, build: Callable):
        with self.lock:
            if key in self.items:
                self.items.move_to_end(key)
                return self.items[key]
        value = build()
        with self.lock:
            self.items[key] = value
            while len(self.items) > self.size:
                self.items.popitem(last=False)
        return value


@dataclass
class CityService:
    predictor: LiveETAPredictor
    records: pd.DataFrame
    roads: RoadGraph
    days: LruCache = field(default_factory=lambda: LruCache(2))
    grids: LruCache = field(default_factory=lambda: LruCache(2))
    moments: LruCache = field(default_factory=lambda: LruCache(24))

    @classmethod
    def load(cls, predictor: LiveETAPredictor) -> "CityService":
        return cls(predictor, load_city(predictor.city)[0], RoadGraph.load(predictor.city))

    def day_table(self, day: pd.Timestamp) -> pd.DataFrame:
        return self.days.get(day, lambda: self.predictor.prepare_day(self.records, day))

    def prepared(self, at: pd.Timestamp) -> pd.DataFrame:
        return at_moment(self.day_table(at.normalize()), at)

    def predictions(self, at: pd.Timestamp) -> pd.DataFrame:
        """City predictions at `at`; the dashboard's 15-minute grid is computed for the whole day in one batch."""
        day = at.normalize()
        if at - day in GRID:
            grid = self.grids.get(day, lambda: city_predictions(self.predictor, self.day_table(day), [day + g for g in sorted(GRID)]))
            return grid.loc[grid["s"] == at]
        return self.moments.get(at, lambda: city_predictions(self.predictor, self.day_table(day), [at]))

    def overview(self, at: pd.Timestamp) -> dict:
        return build_overview(self.predictions, self.records, at)


def bounds(predictor: LiveETAPredictor) -> tuple[tuple[float, float], tuple[float, float]]:
    """South-west and north-east map corners (WGS-84) from the city's data-contract bounding box."""
    lat_lo, lat_hi, lng_lo, lng_hi = predictor.bundle.monitor.contract_bounds
    lat, lng = gcj02_to_wgs84(np.array([lat_lo, lat_hi]), np.array([lng_lo, lng_hi]))
    return (float(lng[0]), float(lat[0])), (float(lng[1]), float(lat[1]))


class Cities:
    """Every city with a trained model: models load at startup, logs and roads on first use."""

    def __init__(self, services: dict[str, CityService] | None = None):
        if services is None:
            self.predictors = {c: LiveETAPredictor.from_store(c) for c in CITIES if (MODEL_STORE / c / "model.pkl").exists()}
            self.services: dict[str, CityService] = {}
        else:
            self.predictors = {c: s.predictor for c, s in services.items()}
            self.services = dict(services)
        self.locks = {c: threading.Lock() for c in self.predictors}

    def __contains__(self, city: str) -> bool:
        return city in self.predictors

    def __getitem__(self, city: str) -> CityService:
        with self.locks[city]:
            if city not in self.services:
                self.services[city] = CityService.load(self.predictors[city])
            return self.services[city]
