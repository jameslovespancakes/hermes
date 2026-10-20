"""Small synthetic delivery logs in the raw LaDe-D format, for fast deterministic tests."""

import numpy as np
import pandas as pd

from server.data.loading import clean_records


def raw_log(days: int = 4, couriers=(1, 2), per_day: int = 6, seed: int = 0) -> pd.DataFrame:
    """Each courier accepts a morning batch, then delivers one package every ~12-20 minutes."""
    rng = np.random.default_rng(seed)
    rows, order_id = [], 0
    for day in range(days):
        date = pd.Timestamp("2000-05-01") + pd.Timedelta(days=day)
        for courier in couriers:
            accept = date + pd.Timedelta(hours=8, minutes=int(rng.integers(0, 20)))
            delivered = accept
            for k in range(per_day):
                delivered = delivered + pd.Timedelta(minutes=int(rng.integers(12, 21)))
                area = int(rng.integers(1, 4))
                rows.append({"order_id": order_id, "region_id": 10, "courier_id": courier, "aoi_id": area, "aoi_type": area % 2,
                             "lng": 121.0 + 0.002 * area + 0.0005 * k, "lat": 37.0 + 0.001 * area,
                             "accept_time": accept.strftime("%m-%d %H:%M:%S"), "accept_gps_time": accept.strftime("%m-%d %H:%M:%S"),
                             "accept_gps_lng": 121.0, "accept_gps_lat": 37.0, "delivery_time": delivered.strftime("%m-%d %H:%M:%S")})
                order_id += 1
    return pd.DataFrame(rows)


def records(**kwargs) -> pd.DataFrame:
    frame, _ = clean_records(raw_log(**kwargs))
    return frame
