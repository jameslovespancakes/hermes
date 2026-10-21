"""Controlled, documented stand-ins for accidental data degradation (SIMULATED; applied to cleaned records).

Every corrupted frame keeps `true_delivered_at` (ground truth, used only for scoring) and `is_real`
(False for injected duplicate records). Adoption is per courier and monotone: once a courier's device is
on the bad feed it stays on it, and the adopted share follows a linear rollout over time.
"""

from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Rollout:
    start: pd.Timestamp
    end: pd.Timestamp
    max_share: float

    def share(self, when: pd.Series) -> np.ndarray:
        progress = (when - self.start) / (self.end - self.start)
        return np.clip(progress.to_numpy(dtype=float), 0, 1) * self.max_share


class TimestampFault(str, Enum):
    BULK_SYNC = "bulk_sync"    # delivery times pushed to the next sync boundary (what the guard is built for)
    NOISE = "noise"            # delivery times randomly off by up to +/-30 min (not designed for)


def _courier_draw(couriers: pd.Series, seed: int) -> np.ndarray:
    """A fixed uniform number per courier (stable across calls with the same seed)."""
    ids = couriers.astype(str)
    unique = np.sort(ids.unique())
    draws = dict(zip(unique, np.random.default_rng(seed).uniform(size=len(unique)), strict=True))
    return ids.map(draws).to_numpy()


def _with_truth(records: pd.DataFrame) -> pd.DataFrame:
    out = records.copy()
    if "true_delivered_at" not in out:
        out["true_delivered_at"] = out["delivered_at"]
    if "is_real" not in out:
        out["is_real"] = True
    return out


def _finish(out: pd.DataFrame) -> pd.DataFrame:
    out["duration_minutes"] = (out["delivered_at"] - out["accepted_at"]).dt.total_seconds() / 60
    return out.sort_values(["accepted_at", "order_id"]).reset_index(drop=True)


def low_quality_feed(records: pd.DataFrame, rollout: Rollout, seed: int = 11, fault: TimestampFault = TimestampFault.BULK_SYNC,
                     batch_minutes: int = 60, jitter_deg: float = 0.01, duplicate_rate: float = 0.5) -> pd.DataFrame:
    """A fast, cheap scanner app on a growing share of couriers.

    BULK_SYNC: delivery times are bulk-synced up to the next `batch_minutes` boundary.
    NOISE: delivery times are randomly off by up to +/-30 minutes (never before acceptance).
    Destination coordinates are jittered (~1 km at 0.01 deg) and `duplicate_rate` of affected records are
    sent twice (exact copies with new ids, is_real=False), so the bad feed contributes extra volume.
    """
    out = _with_truth(records)
    affected = _courier_draw(out["courier_id"], seed) < rollout.share(out["accepted_at"])
    rng = np.random.default_rng(seed + 1)
    if TimestampFault(fault) is TimestampFault.BULK_SYNC:
        out.loc[affected, "delivered_at"] = out.loc[affected, "delivered_at"].dt.ceil(f"{batch_minutes}min")
    else:
        shift = pd.to_timedelta(rng.uniform(-30, 30, affected.sum()), unit="m")
        out.loc[affected, "delivered_at"] = np.maximum(out.loc[affected, "delivered_at"] + shift, out.loc[affected, "accepted_at"])
    out.loc[affected, ["lat", "lng"]] += rng.normal(0, jitter_deg, (affected.sum(), 2))
    out["lq_feed"] = affected
    copies = out.loc[affected].sample(frac=duplicate_rate, random_state=seed).copy()
    copies["order_id"] = out["order_id"].max() + 1 + np.arange(len(copies))
    copies["is_real"] = False
    return _finish(pd.concat([out, copies], ignore_index=True))


def _apply_lag(out: pd.DataFrame, lag: pd.Series, event_time: bool) -> pd.DataFrame:
    """Processing-time view: the arrival time replaces the event time (what a naive pipeline stores).
    Event-time view: the scanner's timestamp stays in `delivered_at`; arrival goes to `received_at`."""
    if event_time:
        base = out["received_at"] if "received_at" in out else out["delivered_at"]
        out["received_at"] = base + lag
    else:
        out["delivered_at"] = out["delivered_at"] + lag
    return out


def sync_delay(records: pd.DataFrame, rollout: Rollout, lag_minutes: float = 60.0, seed: int = 23,
               event_time: bool = False) -> pd.DataFrame:
    """Stale feed: a growing share of courier devices upload delivery events `lag_minutes` late."""
    out = _with_truth(records)
    affected = _courier_draw(out["courier_id"], seed) < rollout.share(out["true_delivered_at"])
    lag = pd.Series(np.where(affected, lag_minutes, 0.0), index=out.index)
    out = _apply_lag(out, pd.to_timedelta(lag, unit="m"), event_time)
    out["stale_feed"] = affected
    return _finish(out)

