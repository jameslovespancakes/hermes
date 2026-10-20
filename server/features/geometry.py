"""Distance and ordering helpers (straight-line; coordinates in LaDe are privacy-perturbed)."""

import numpy as np

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance in km; broadcasts over numpy arrays."""
    lat1, lng1, lat2, lng2 = map(np.radians, (lat1, lng1, lat2, lng2))
    h = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lng2 - lng1) / 2) ** 2
    return EARTH_RADIUS_KM * 2 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))


def greedy_tour(start_lat, start_lng, lat, lng):
    """Nearest-neighbour visiting order from a start point.

    Returns (position of each point in the tour, cumulative km travelled to reach it).
    """
    n = len(lat)
    order, cumulative = np.empty(n, dtype=int), np.empty(n)
    remaining = np.ones(n, dtype=bool)
    cur_lat, cur_lng, total = start_lat, start_lng, 0.0
    for step in range(n):
        d = haversine_km(cur_lat, cur_lng, lat, lng)
        d[~remaining] = np.inf
        j = int(np.argmin(d))
        total += d[j]
        order[j], cumulative[j] = step, total
        remaining[j] = False
        cur_lat, cur_lng = lat[j], lng[j]
    return order, cumulative


def rank_fraction(values):
    """Rank of each finite value scaled to [0, 1] (stable ties); NaN stays NaN."""
    x = np.asarray(values, dtype=float)
    out = np.full(len(x), np.nan)
    ok = np.isfinite(x)
    if ok.any():
        out[ok] = x[ok].argsort(kind="stable").argsort(kind="stable") / max(ok.sum() - 1, 1)
    return out
