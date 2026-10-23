"""Distance and ordering helpers (straight-line; coordinates in LaDe are privacy-perturbed)."""

import numpy as np

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance in km; broadcasts over numpy arrays."""
    lat1, lng1, lat2, lng2 = map(np.radians, (lat1, lng1, lat2, lng2))
    h = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lng2 - lng1) / 2) ** 2
    return EARTH_RADIUS_KM * 2 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))


def gcj02_to_wgs84(lat, lng):
    """China's GCJ-02 map datum -> WGS-84 (standard approximation, ~1-2 m error); broadcasts over numpy arrays."""
    lat, lng = np.asarray(lat, dtype=float), np.asarray(lng, dtype=float)
    a, ee = 6378245.0, 0.00669342162296594323
    x, y = lng - 105.0, lat - 35.0
    wave = (20 * np.sin(6 * x * np.pi) + 20 * np.sin(2 * x * np.pi)) * 2 / 3
    d_lat = -100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * np.sqrt(np.abs(x)) + wave
    d_lat += (20 * np.sin(y * np.pi) + 40 * np.sin(y / 3 * np.pi)) * 2 / 3 + (160 * np.sin(y / 12 * np.pi) + 320 * np.sin(y * np.pi / 30)) * 2 / 3
    d_lng = 300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * np.sqrt(np.abs(x)) + wave
    d_lng += (20 * np.sin(x * np.pi) + 40 * np.sin(x / 3 * np.pi)) * 2 / 3 + (150 * np.sin(x / 12 * np.pi) + 300 * np.sin(x / 30 * np.pi)) * 2 / 3
    rad = np.radians(lat)
    magic = 1 - ee * np.sin(rad) ** 2
    d_lat = d_lat * 180 / ((a * (1 - ee)) / (magic * np.sqrt(magic)) * np.pi)
    d_lng = d_lng * 180 / (a / np.sqrt(magic) * np.cos(rad) * np.pi)
    return lat - d_lat, lng - d_lng
