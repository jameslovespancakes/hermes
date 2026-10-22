"""Compiled core of the live queries (Numba): per courier moment, its pending parcels and their live inputs."""

import math

import numpy as np
from numba import njit

MINUTE = 60_000_000_000
DAY = 1440 * MINUTE
RAD = math.pi / 180.0
EARTH_KM = 6371.0088
COLUMNS = (
    "feed_age_min",
    "upload_lag_min",
    "elapsed_min",
    "clock_s",
    "n_pending",
    "n_done_today",
    "n_done_last_hour",
    "pace_today_min",
    "minutes_since_first_delivery_today",
    "dist_from_courier_km",
    "dist_rank",
    "greedy_pos",
    "greedy_pos_frac",
    "greedy_km",
    "aoi_greedy_pos_frac",
    "aoi_earlier_count",
    "same_aoi_pending",
    "at_current_aoi",
    "hab_ca_rel_now",
    "hab_ca_rank_now",
    "hab_shift_end_rel_now",
    "est_stops_x_pace",
    "remaining_min",
)
(FEED, LAG, ELAPSED, CLOCK, N_PEND, N_TODAY, N_HOUR, PACE, SINCE, DIST, DIST_RANK, G_POS, G_FRAC, G_KM, A_FRAC, A_EARLIER, SAME,
 AT_CUR, CA_REL, CA_RANK, END_REL, EST, REMAINING) = range(len(COLUMNS))  # fmt: skip


@njit(cache=True, nogil=True)
def _haversine(lat1, lng1, lat2, lng2):
    p1, p2 = lat1 * RAD, lat2 * RAD
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin((lng2 * RAD - lng1 * RAD) / 2) ** 2
    return EARTH_KM * 2 * math.asin(math.sqrt(min(max(h, 0.0), 1.0)))


@njit(cache=True, nogil=True)
def _rank_fraction(x, out):
    n_ok = 0
    for v in x:
        if np.isfinite(v):
            n_ok += 1
    if n_ok == 0:
        out[:] = np.nan
        return
    keys = np.empty(n_ok)
    where = np.empty(n_ok, np.int64)
    j = 0
    for i in range(len(x)):
        if np.isfinite(x[i]):
            keys[j], where[j] = x[i], i
            j += 1
    order = np.argsort(keys, kind="mergesort")
    out[:] = np.nan
    for rank in range(n_ok):
        out[where[order[rank]]] = rank / max(n_ok - 1, 1)


@njit(cache=True, nogil=True)
def _greedy(start_lat, start_lng, lat, lng, order, cumulative):
    n = len(lat)
    remaining = np.ones(n, np.bool_)
    cur_lat, cur_lng, total = start_lat, start_lng, 0.0
    for step in range(n):
        best, j = np.inf, -1
        for k in range(n):
            if remaining[k]:
                dist = _haversine(cur_lat, cur_lng, lat[k], lng[k])
                if j < 0 or dist < best:
                    best, j = dist, k
        total += best
        order[j], cumulative[j] = step, total
        remaining[j] = False
        cur_lat, cur_lng = lat[j], lng[j]


@njit(cache=True, nogil=True)
def window_counts(row_group, row_t, starts, times, values, windows):
    """Per row: events of its group up to t, and count / mean value within each window (t - w, t]."""
    n_all = np.zeros(len(row_t))
    counts = np.zeros((len(windows), len(row_t)))
    means = np.full((len(windows), len(row_t)), np.nan)
    sums = np.zeros(len(times) + len(starts))
    for g in range(len(starts) - 1):
        total = 0.0
        base = starts[g] + g
        for i in range(starts[g], starts[g + 1]):
            total += values[i]
            sums[base + 1 + i - starts[g]] = total
    for i in range(len(row_t)):
        g = row_group[i]
        if g < 0:
            continue
        group_times = times[starts[g] : starts[g + 1]]
        base = starts[g] + g
        hi = np.searchsorted(group_times, row_t[i], side="right")
        n_all[i] = hi
        for w in range(len(windows)):
            lo = np.searchsorted(group_times, row_t[i] - windows[w] * MINUTE, side="right")
            count = hi - lo
            counts[w, i] = count
            if count > 0:
                means[w, i] = (sums[base + hi] - sums[base + lo]) / count
    return n_all, counts, means


@njit(cache=True, nogil=True)
def expanding_median(values, starts):
    """Running median within each group (groups are consecutive slices `starts[g]:starts[g + 1]`)."""
    out = np.empty(len(values))
    for g in range(len(starts) - 1):
        seen = np.empty(starts[g + 1] - starts[g])
        for i in range(starts[g], starts[g + 1]):
            n = i - starts[g]
            k = n
            while k > 0 and seen[k - 1] > values[i]:
                seen[k] = seen[k - 1]
                k -= 1
            seen[k] = values[i]
            out[i] = seen[n // 2] if n % 2 == 0 else (seen[n // 2] + seen[n // 2 + 1]) / 2
    return out


@njit(cache=True, nogil=True)
def _block_sum(a, start, n):
    """numpy's pairwise-summation leaf (n <= 128): eight running sums, combined in pairs."""
    total = np.zeros(1, a.dtype)[0]
    if n < 8:
        for i in range(start, start + n):
            total += a[i]
        return total
    r = a[start : start + 8].copy()
    stop = start + n - n % 8
    for i in range(start + 8, stop, 8):
        for k in range(8):
            r[k] += a[i + k]
    total = ((r[0] + r[1]) + (r[2] + r[3])) + ((r[4] + r[5]) + (r[6] + r[7]))
    for i in range(stop, start + n):
        total += a[i]
    return total


@njit(cache=True, nogil=True)
def _pairwise_sum(a, start, n):
    """numpy's pairwise summation (so results match np.sum bit for bit), without recursion."""
    if n <= 128:
        return _block_sum(a, start, n)
    # Visit the halving tree, then add children before parents, exactly as numpy's recursion does.
    order = []
    nodes = [(start, n)]
    while nodes:
        s0, n0 = nodes.pop()
        order.append((s0, n0))
        if n0 > 128:
            half = n0 // 2
            half -= half % 8
            nodes.append((s0, half))
            nodes.append((s0 + half, n0 - half))
    sums = {}
    for i in range(len(order) - 1, -1, -1):
        s0, n0 = order[i]
        if n0 <= 128:
            sums[(s0, n0)] = _block_sum(a, s0, n0)
        else:
            half = n0 // 2
            half -= half % 8
            sums[(s0, n0)] = sums[(s0, half)] + sums[(s0 + half, n0 - half)]
    return sums[(start, n)]


@njit(cache=True, nogil=True)
def _nanmean(values):
    """np.nanmean in the array's own precision: NaN replaced by 0, pairwise sum, divided by the non-NaN count."""
    filled = np.where(np.isnan(values), np.zeros(1, values.dtype)[0], values)
    count = 0
    for v in values:
        if not np.isnan(v):
            count += 1
    if count == 0:
        return np.nan
    return values.dtype.type(_pairwise_sum(filled, 0, len(filled)) / count)


@njit(cache=True, nogil=True)
def _moment(s, idx, a, d, d_ok, r, r_ok, known_all, event_time, lat, lng, aoi, usual_ca, usual_end, usual_pace, out, rows, cur, offset):
    """Fill rows for one courier moment starting at `offset`; returns the number of pending parcels."""
    m = len(idx)
    received = np.zeros(m, np.bool_)
    pending = np.zeros(m, np.int64)
    n = 0
    for i in range(m):
        p = idx[i]
        received[i] = r_ok[p] and r[p] <= s
        if a[p] <= s and not received[i]:
            pending[n] = i
            n += 1
    if n == 0 or out is None:
        return n
    if event_time:
        count = 0
        for i in range(m):
            if received[i] and d_ok[idx[i]]:
                count += 1
        known = np.empty(count, np.int64)
        j = 0
        for i in range(m):
            if received[i] and d_ok[idx[i]]:
                known[j] = d[idx[i]]
                j += 1
        known.sort()
    else:
        known = known_all
    k1 = np.searchsorted(known, s, side="right")
    has_last = k1 > 0
    last = known[k1 - 1] if has_last else 0
    done = np.empty(m, np.int64)
    n_done = 0
    if has_last:
        for i in range(m):
            p = idx[i]
            if received[i] and d_ok[p] and d[p] == last:
                done[n_done] = p
                n_done += 1
    lag = (r[done[0]] - last) / MINUTE if n_done else np.nan
    clat = _nanmean(lat[done[:n_done]]) if n_done else np.nan
    clng = _nanmean(lng[done[:n_done]]) if n_done else np.nan
    day = s - s % DAY
    k0 = np.searchsorted(known, day, side="left")
    n_today = k1 - k0
    since = (s - known[k0]) / MINUTE if n_today > 0 else np.nan
    pace = since / (n_today - 1) if n_today >= 2 else np.nan
    clock = (s - day) / MINUTE
    feed = (s - last) / MINUTE if has_last else np.nan
    n_hour = k1 - np.searchsorted(known, s - 60 * MINUTE, side="right")

    pend = idx[pending[:n]]
    plat, plng = lat[pend], lng[pend]
    block = out[offset : offset + n]
    rows[offset : offset + n] = pend
    cur[offset : offset + n] = done[0] if n_done else -1
    for j in range(n):
        p = pend[j]
        block[j, FEED], block[j, LAG], block[j, CLOCK] = feed, lag, clock
        block[j, ELAPSED] = (s - a[p]) / MINUTE
        block[j, N_PEND], block[j, N_TODAY], block[j, N_HOUR] = n, n_today, n_hour
        block[j, PACE], block[j, SINCE] = pace, since
        block[j, DIST] = _haversine(clat, clng, plat[j], plng[j])
        block[j, CA_REL] = usual_ca[p] - clock
        block[j, END_REL] = usual_end[p] - clock
        block[j, REMAINING] = (d[p] - s) / MINUTE if d_ok[p] else np.nan
    _rank_fraction(block[:, DIST].copy(), block[:, DIST_RANK])
    _rank_fraction(block[:, CA_REL].copy(), block[:, CA_RANK])

    codes = np.unique(aoi[pend])
    inv = np.searchsorted(codes, aoi[pend])
    sizes = np.zeros(len(codes))
    for j in range(n):
        sizes[inv[j]] += 1
    for j in range(n):
        block[j, SAME] = sizes[inv[j]]
        hit = 0.0
        for k in range(n_done):
            if aoi[done[k]] == aoi[pend[j]]:
                hit = 1.0
        block[j, AT_CUR] = hit
    finite = np.isfinite(clat)
    for j in range(n):
        finite = finite and np.isfinite(plat[j]) and np.isfinite(plng[j])
    if finite:
        order, cumulative = np.empty(n, np.int64), np.empty(n)
        _greedy(clat, clng, plat, plng, order, cumulative)
        c_lat, c_lng = np.zeros(len(codes)), np.zeros(len(codes))
        for j in range(n):
            c_lat[inv[j]] += plat[j]
            c_lng[inv[j]] += plng[j]
        area_order, area_km = np.empty(len(codes), np.int64), np.empty(len(codes))
        _greedy(clat, clng, c_lat / sizes, c_lng / sizes, area_order, area_km)
        earlier = np.zeros(len(codes))
        for k in range(len(codes)):
            for q in range(len(codes)):
                if area_order[q] < area_order[k]:
                    earlier[k] += sizes[q]
        for j in range(n):
            block[j, G_POS] = order[j]
            block[j, G_FRAC] = order[j] / max(n - 1, 1)
            block[j, G_KM] = cumulative[j]
            block[j, A_FRAC] = area_order[inv[j]] / max(len(codes) - 1, 1)
            block[j, A_EARLIER] = earlier[inv[j]]
    else:
        block[:, G_POS] = np.nan
        block[:, G_FRAC] = np.nan
        block[:, G_KM] = np.nan
        block[:, A_FRAC] = np.nan
        block[:, A_EARLIER] = np.nan
    pace_used = pace if np.isfinite(pace) else _nanmean(usual_pace[pend])
    for j in range(n):
        block[j, EST] = (block[j, G_POS] + 1) * pace_used
    return n


@njit(cache=True, nogil=True)
def live_rows(groups, starts, times, t_starts, a, d, d_ok, r, r_ok, event_time, lat, lng, aoi, usual_ca, usual_end, usual_pace):
    """All live rows: (package row, moment, current row, inputs) for every courier group and its moments."""
    known_by_group = []
    counts = np.zeros(len(times), np.int64)
    empty = np.empty((0, len(COLUMNS)))
    for g in range(len(starts) - 1):
        idx = groups[starts[g] : starts[g + 1]]
        known = np.sort(d[idx][d_ok[idx]])
        known_by_group.append(known)
        for e in range(t_starts[g], t_starts[g + 1]):
            counts[e] = _moment(
                times[e], idx, a, d, d_ok, r, r_ok, known, event_time, lat, lng, aoi, usual_ca, usual_end, usual_pace, None, None, None, 0
            )
    total = counts.sum()
    out = np.empty((total, len(COLUMNS)))
    rows, cur, moments = np.empty(total, np.int64), np.empty(total, np.int64), np.empty(total, np.int64)
    offset = 0
    for g in range(len(starts) - 1):
        idx = groups[starts[g] : starts[g + 1]]
        for e in range(t_starts[g], t_starts[g + 1]):
            if counts[e]:
                _moment(
                    times[e],
                    idx,
                    a,
                    d,
                    d_ok,
                    r,
                    r_ok,
                    known_by_group[g],
                    event_time,
                    lat,
                    lng,
                    aoi,
                    usual_ca,
                    usual_end,
                    usual_pace,
                    out,
                    rows,
                    cur,
                    offset,
                )
                moments[offset : offset + counts[e]] = times[e]
                offset += counts[e]
    return rows, moments, cur, out if total else empty
