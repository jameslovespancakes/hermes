"""Zones of ~10 nearby buildings, and zone habits learned from previous days only."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from server.config import SEED, ZONE_SIZE
from server.features.context import rank_in_event, visible_at

LAT_SCALE = np.array([1.0, 0.8])


@dataclass
class Zones:
    centers: np.ndarray
    aoi_zone: dict

    @classmethod
    def fit(cls, packages: pd.DataFrame, cutoff: pd.Timestamp, size: int = ZONE_SIZE) -> "Zones":
        from sklearn.cluster import MiniBatchKMeans

        train = packages["_accepted_at"] < cutoff
        centres = pd.DataFrame({"aoi": packages["aoi_id"].astype(str), "lat": packages["lat"], "lng": packages["lng"]})[train]
        centres = centres.dropna().groupby("aoi")[["lat", "lng"]].median()
        kmeans = MiniBatchKMeans(n_clusters=max(2, len(centres) // size), random_state=SEED, n_init=3).fit(centres.to_numpy() * LAT_SCALE)
        return cls(kmeans.cluster_centers_, dict(zip(centres.index, kmeans.labels_.tolist(), strict=True)))

    def assign(self, packages: pd.DataFrame) -> np.ndarray:
        zone = packages["aoi_id"].astype(str).map(self.aoi_zone).to_numpy(dtype=float)
        unknown = np.flatnonzero(np.isnan(zone))
        if len(unknown):
            points = packages[["lat", "lng"]].astype(float).fillna(packages[["lat", "lng"]].median()).to_numpy()[unknown] * LAT_SCALE
            chunks = np.array_split(points, len(points) // 50_000 + 1)
            zone[unknown] = np.concatenate([((c[:, None, :] - self.centers[None, :, :]) ** 2).sum(-1).argmin(1) for c in chunks])
        return zone.astype(int)


def zone_features(live: pd.DataFrame, packages: pd.DataFrame, zones: Zones) -> pd.DataFrame:
    zone = zones.assign(packages)
    n_zones = len(zones.centers)
    rows, cur = live["row"].to_numpy(), live["cur_row"].to_numpy()
    pz = zone[rows]
    cz = np.where(cur >= 0, zone[np.maximum(cur, 0)], -1)
    out = pd.DataFrame(index=live.index)
    out["zone_id"] = pz
    out["zone_is_current"] = (pz == cz).astype("float32")
    out["zone_pending"] = pd.Series(pz, index=live.index).groupby([live["event"], pz]).transform("size").astype("float32")

    courier = pd.factorize(packages["courier_id"].astype(str))[0]
    seen = pd.to_datetime(visible_at(packages))
    visits = pd.DataFrame({"c": courier, "t": seen, "z": zone}).dropna(subset=["t"]).sort_values(["c", "t"])
    visits["day"] = visits["t"].dt.normalize()
    visits["prev"] = visits.groupby(["c", "day"])["z"].shift()
    visits["clock"] = (visits["t"] - visits["day"]).dt.total_seconds() / 60
    moves = visits.dropna(subset=["prev"]).astype({"prev": int})

    row_courier = courier[rows].astype(np.int64)
    day = pd.to_datetime(live["s"]).dt.normalize().to_numpy()
    clock_now = live["clock_s"].to_numpy()
    p_all, p_courier, usual = (np.full(len(live), np.nan) for _ in range(3))
    moves["pair"] = moves["prev"].to_numpy(np.int64) * n_zones + moves["z"].to_numpy()
    moves["cpair"] = moves["c"].to_numpy(np.int64) * n_zones * n_zones + moves["pair"]
    moves["cfrom"] = moves["c"].to_numpy(np.int64) * n_zones + moves["prev"].to_numpy(np.int64)
    visits["cz"] = visits["c"].to_numpy(np.int64) * n_zones + visits["z"].to_numpy()
    for d in np.unique(day):
        idx = np.flatnonzero(day == d)
        past, seen_before = moves.loc[moves["day"] < d], visits.loc[visits["day"] < d]
        if past.empty:
            continue
        j = idx[cz[idx] >= 0]
        pair = cz[j].astype(np.int64) * n_zones + pz[j]
        p_all[j] = past["pair"].value_counts().reindex(pair).to_numpy() / past["prev"].value_counts().reindex(cz[j]).to_numpy()
        p_courier[j] = (
            past["cpair"].value_counts().reindex(row_courier[j] * n_zones * n_zones + pair).to_numpy()
            / past["cfrom"].value_counts().reindex(row_courier[j] * n_zones + cz[j]).to_numpy()
        )
        clock = seen_before.groupby("cz")["clock"].mean()
        usual[idx] = clock.reindex(row_courier[idx] * n_zones + pz[idx]).to_numpy() - clock_now[idx]

    out["p_zone_next_all"] = p_all.astype("float32")
    out["p_zone_next_courier"] = p_courier.astype("float32")
    out["zone_usual_clock_rel_now"] = usual.astype("float32")
    for c in ("p_zone_next_all", "p_zone_next_courier"):
        out[f"{c}_rank"] = rank_in_event(live, -np.nan_to_num(out[c].to_numpy(), nan=-1))
    out["zone_usual_rank_now"] = rank_in_event(live, np.abs(np.nan_to_num(usual, nan=1e5)))
    return out
