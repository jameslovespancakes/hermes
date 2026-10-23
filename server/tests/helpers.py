"""Small synthetic delivery logs in the raw LaDe-D format, for fast deterministic tests."""

import numpy as np
import pandas as pd

from server.data.loading import clean_records


def raw_log(days: int = 4, couriers=(1, 2), per_day: int = 6, seed: int = 0) -> pd.DataFrame:
    """Each courier accepts a morning batch and delivers one package every ~12-20 minutes; every fourth day the
    last package waits until early the next morning."""
    rng = np.random.default_rng(seed)
    rows, order_id = [], 0
    for day in range(days):
        date = pd.Timestamp("2000-05-01") + pd.Timedelta(days=day)
        for courier in couriers:
            accept = date + pd.Timedelta(hours=8, minutes=int(rng.integers(0, 20)))
            delivered = accept
            for k in range(per_day):
                delivered = delivered + pd.Timedelta(minutes=int(rng.integers(12, 21)))
                if day % 4 == 3 and k == per_day - 1:
                    delivered = date + pd.Timedelta(days=1, hours=7, minutes=50)
                area = int(rng.integers(1, 4))
                rows.append(
                    {
                        "order_id": order_id,
                        "region_id": 10,
                        "courier_id": courier,
                        "aoi_id": area,
                        "aoi_type": area % 2,
                        "lng": 121.0 + 0.002 * area + 0.0005 * k,
                        "lat": 37.0 + 0.001 * area,
                        "accept_time": accept.strftime("%m-%d %H:%M:%S"),
                        "accept_gps_time": accept.strftime("%m-%d %H:%M:%S"),
                        "accept_gps_lng": 121.0,
                        "accept_gps_lat": 37.0,
                        "delivery_time": delivered.strftime("%m-%d %H:%M:%S"),
                        "delivery_gps_lng": 121.0 + 0.002 * area + 0.0005 * k + 0.0001,
                        "delivery_gps_lat": 37.0 + 0.001 * area,
                    }
                )
                order_id += 1
    return pd.DataFrame(rows)


def records(**kwargs) -> pd.DataFrame:
    frame, _ = clean_records(raw_log(**kwargs))
    return frame


class Constant:
    """Stand-in model: predicts a fixed value per row."""

    def __init__(self, value: float):
        self.value = value

    def predict(self, rows) -> np.ndarray:
        return np.full(len(rows), self.value, dtype=float)

    def predict_proba(self, rows) -> np.ndarray:
        return np.tile([1 - self.value, self.value], (len(rows), 1))


class Unchanged:
    """Stand-in later-day model: keeps the ETA."""

    def minutes(self, rows, minutes):
        return minutes


class NoRisk:
    """Stand-in risk model: no estimate is uncertain."""

    threshold = np.inf

    def predict(self, rows, minutes):
        return np.zeros(len(rows))


def constant_bundle(eta: float = 25.0, staleness: float | None = None, **extra):
    """A ModelBundle with one zone, no route preference, and constant ETAs."""
    from server.features.zones import Zones
    from server.models.bundle import ModelBundle
    from server.models.eta import EtaModel
    from server.quality.monitor import DRIFT_FEATURES, MonitorBaseline

    parts = {
        "zones": Zones(np.array([[37.0, 121.0 * 0.8]]), {}),
        "zone_model": Constant(0.5),
        "later": Unchanged(),
        "risk": NoRisk(),
        "monitor": MonitorBaseline(pd.DataFrame(columns=DRIFT_FEATURES), {}, (-90.0, 90.0, -180.0, 180.0)),
        "staleness": EtaModel([Constant(staleness)], ["n_pending"], {}) if staleness is not None else None,
    }
    return ModelBundle(
        city="yt",
        trained_through="09-01",
        habit_columns=[],
        route_model=Constant(0.0),
        eta=EtaModel([Constant(eta)], ["n_pending"], {}),
        **{**parts, **extra},
    )


def street_grid(n: int = 5, step: float = 0.002):
    """A RoadGraph of n x n streets around the synthetic log's coordinates."""
    from server.serving.roads import RoadGraph

    ticks = np.arange(n) * step
    lines = [np.c_[121.0 + ticks, np.full(n, 37.0 + t)] for t in ticks] + [np.c_[np.full(n, 121.0 + t), 37.0 + ticks] for t in ticks]
    return RoadGraph.from_lines(lines)


def app_client(bundle=None, recs=None):
    """A TestClient for the API serving one synthetic city ('yt')."""
    from fastapi.testclient import TestClient

    from server.api.app import create_app
    from server.serving.city import CityService
    from server.serving.predictor import LiveETAPredictor

    service = CityService(
        LiveETAPredictor(bundle or constant_bundle(eta=30.0)),
        recs if recs is not None else records(days=2, couriers=(1, 2), per_day=6),
        street_grid(),
    )
    return TestClient(create_app(services={"yt": service}, frontend=None))
