"""The whole city at one moment, for the dispatcher map.

Every pending parcel gets its current ETA and the ETA the model gave an hour earlier ("before" and "after"), plus
at most one issue for a dispatcher; problems with a courier's device feed (lagging, silent, bulk, clock) go on the
courier instead, once:

- data:    the data guards flagged the inputs (stale courier feed, bulk-synced scans)
- suspect: the inputs passed every guard but the picture is implausible
- late:    the estimate slipped far in the last hour

Both moments are replayed from the log as it was known then, so neither estimate uses later information.
Coordinates are returned in WGS-84 for web maps.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from server.features.geometry import gcj02_to_wgs84
from server.quality.guard import COURIER_ISSUES
from server.serving.predictor import OUTPUT_COLUMNS, LiveETAPredictor, courier_positions


@dataclass(frozen=True)
class IssueRules:
    """Thresholds, set from clean held-out days (Sept 18, 20, 25 at 10:30, 14:00 and 17:00 in Yantai)."""

    lookback_min: float = 60.0  # the "before" estimate is the one made this long ago
    late_slip_min: float = 90.0  # median hourly slip is +14..55 min; >= 90 min hits ~5-10% of parcels
    early_jump_min: float = 60.0  # an estimate rarely moves an hour earlier when nothing was flagged
    far_from_courier_km: float = 15.0  # ~1% of parcels sit this far from their courier's last position


RULES = IssueRules()


def city_predictions(predictor: LiveETAPredictor, day_table: pd.DataFrame, moments: list[pd.Timestamp]) -> pd.DataFrame:
    """ETAs with diagnostics for every package held at each moment (one batch; column `s` is the moment)."""
    seen = day_table["_received_at"] if "_received_at" in day_table else day_table["_delivered_at"]
    held = [day_table.loc[(day_table["_accepted_at"] <= m) & ~(seen <= m), ["courier_id"]].drop_duplicates().assign(s=m) for m in moments]
    events = pd.concat(held)
    if events.empty:
        return pd.DataFrame(columns=[*OUTPUT_COLUMNS, "s", "courier", "lat", "lng", "courier_id"])
    events["courier_id"] = events["courier_id"].astype(str)
    out = predictor.score_events(day_table, events, moments[0].normalize())
    where = day_table.set_index("_order_id")[["lat", "lng"]]
    out = out.join(where, on="order_id")
    out["courier_id"] = out["courier"].str.split(":", n=1).str[1]
    return out


def classify(now: pd.DataFrame, before: pd.DataFrame, rules: IssueRules = RULES) -> pd.DataFrame:
    """Adds baseline_eta, slip_min (minutes the ETA moved since the baseline), issue and reasons to `now`."""
    out = now.merge(
        before[["order_id", "predicted_delivery_at"]].rename(columns={"predicted_delivery_at": "baseline_eta"}),
        on="order_id",
        how="left",
    )
    out["baseline_eta"] = pd.to_datetime(out["baseline_eta"])  # all-missing when nothing was held at the baseline
    out["slip_min"] = (pd.to_datetime(out["predicted_delivery_at"]) - out["baseline_eta"]).dt.total_seconds() / 60
    slip = np.nan_to_num(out["slip_min"].to_numpy(dtype=float))
    far = out["dist_from_courier_km"].to_numpy(dtype=float)
    checks = {
        "suspect": [
            (slip <= -rules.early_jump_min, lambda r: f"ETA jumped {-r.slip_min:.0f} min earlier in the last hour"),
            (far >= rules.far_from_courier_km, lambda r: f"Parcel is {r.dist_from_courier_km:.0f} km from the courier"),
        ],
        "late": [(slip >= rules.late_slip_min, lambda r: f"ETA slipped {r.slip_min:.0f} min in the last hour")],
    }
    issues, reasons = [], []
    for i, row in enumerate(out.itertuples(index=False)):
        own = [(kind, why) for kind, why in zip(row.data_issues, row.review_reasons, strict=True) if kind not in COURIER_ISSUES]
        if own:
            issues.append(own[0][0])
            reasons.append([why for _, why in own])
            continue
        kind, why = None, []
        for name in ("suspect", "late"):
            hits = [describe(row) for mask, describe in checks[name] if mask[i]]
            if hits:
                kind, why = name, hits
                break
        issues.append(kind)
        reasons.append(why)
    out["issue"], out["reasons"] = issues, reasons
    return out


def build_overview(city: Callable[[pd.Timestamp], pd.DataFrame], records: pd.DataFrame, at: pd.Timestamp, rules: IssueRules = RULES) -> dict:
    """Couriers and parcels at `at`, each parcel's ETA now vs an hour earlier, and its issue.

    `city(moment)` returns `city_predictions` at that moment (cached by the caller)."""
    baseline_at = at - pd.Timedelta(minutes=rules.lookback_min)
    now = city(at)
    if now.empty:
        return {"baseline_at": baseline_at, "couriers": pd.DataFrame(), "parcels": now}
    parcels = classify(now, city(baseline_at), rules)

    positions = courier_positions(records, at)
    feed = [
        next(((kind, why) for kind, why in zip(kinds, whys, strict=True) if kind in COURIER_ISSUES), (None, None))
        for kinds, whys in zip(parcels["data_issues"], parcels["review_reasons"], strict=True)
    ]
    per_courier = (
        parcels.assign(feed_issue=[k for k, _ in feed], feed_reason=[w for _, w in feed])
        .groupby("courier_id")
        .agg(
            packages_held=("order_id", "size"),
            feed_age_min=("feed_age_min", "first"),
            model_used=("model_used", "first"),
            issue=("feed_issue", "first"),
            reason=("feed_reason", "first"),
        )
    )
    couriers = per_courier.join(positions.set_axis(positions.index.astype(str)), how="inner").reset_index()
    return {"baseline_at": baseline_at, "couriers": _on_map(couriers), "parcels": _on_map(parcels)}


def _on_map(frame: pd.DataFrame) -> pd.DataFrame:
    """LaDe coordinates are GCJ-02; web maps use WGS-84."""
    frame = frame.copy()
    frame["lat"], frame["lng"] = gcj02_to_wgs84(frame["lat"], frame["lng"])
    return frame
