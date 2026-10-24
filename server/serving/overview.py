"""The whole city at one moment, for the dispatcher map.

Every pending parcel gets its current ETA and the ETA the model gave an hour earlier ("before" and "after"), plus
at most one issue for a dispatcher:

- parcel issues: moved/resent/missed (from the guard), suspect (inputs passed every guard but the picture is
  implausible), late (the estimate slipped far in the last hour)
- device issues: lagging/silent/bulk/clock, shown once, on the courier

Both moments are replayed from the log as it was known then, so neither estimate uses later information.
Coordinates are returned in WGS-84 for web maps.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from server.features.context import visible_at
from server.features.geometry import gcj02_to_wgs84
from server.quality.guard import COURIER_ISSUES
from server.serving.predictor import DIAGNOSTIC_COLUMNS, OUTPUT_COLUMNS, LiveETAPredictor, courier_positions


@dataclass(frozen=True)
class IssueRules:
    """Thresholds, set from clean held-out days (Sept 18, 20, 25 at 10:30, 14:00 and 17:00 in Yantai)."""

    lookback_min: float = 60.0
    late_slip_min: float = 90.0
    early_jump_min: float = 60.0
    far_from_courier_km: float = 15.0


RULES = IssueRules()


def city_predictions(predictor: LiveETAPredictor, day_table: pd.DataFrame, moments: list[pd.Timestamp]) -> pd.DataFrame:
    """ETAs with diagnostics for every package held at each moment (one batch; column `s` is the moment)."""
    seen = visible_at(day_table)
    held = [day_table.loc[(day_table["_accepted_at"] <= m) & ~(seen <= m), ["courier_id"]].drop_duplicates().assign(s=m) for m in moments]
    events = pd.concat(held)
    if events.empty:
        return pd.DataFrame(columns=[*OUTPUT_COLUMNS, "s", "courier", *DIAGNOSTIC_COLUMNS, "lat", "lng", "courier_id"])
    events["courier_id"] = events["courier_id"].astype(str)
    out = predictor.predict_day(day_table, events, moments[0].normalize())
    where = day_table.set_index("_order_id")[["lat", "lng"]]
    out = out.join(where, on="order_id")
    out["courier_id"] = out["courier"].str.split(":", n=1).str[1]
    return out


def _split(kinds: list[str], whys: list[str]) -> tuple[str | None, str | None, list[tuple[str, str]]]:
    """A parcel's first device-feed issue and its reason, and the parcel's own issues with their reasons."""
    pairs = list(zip(kinds, whys, strict=True))
    feed_kind, feed_why = next(((kind, why) for kind, why in pairs if kind in COURIER_ISSUES), (None, None))
    return feed_kind, feed_why, [(kind, why) for kind, why in pairs if kind not in COURIER_ISSUES]


def _review(row, i: int, checks: dict) -> tuple[str | None, list[str]]:
    """The first review issue whose checks hit row `i`, with what they found."""
    for name, rules in checks.items():
        hits = [describe(row) for mask, describe in rules if mask[i]]
        if hits:
            return name, hits
    return None, []


def classify(now: pd.DataFrame, before: pd.DataFrame, rules: IssueRules = RULES) -> pd.DataFrame:
    """Adds baseline_eta, slip_min (minutes the ETA moved since the baseline), issue, reasons, feed_issue and feed_reason."""
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
    issues, reasons, feed_issues, feed_reasons = [], [], [], []
    for i, row in enumerate(out.itertuples(index=False)):
        feed_kind, feed_why, own = _split(row.data_issues, row.review_reasons)
        feed_issues.append(feed_kind)
        feed_reasons.append(feed_why)
        kind, why = (own[0][0], [w for _, w in own]) if own else _review(row, i, checks)
        issues.append(kind)
        reasons.append(why)
    out["issue"], out["reasons"], out["feed_issue"], out["feed_reason"] = issues, reasons, feed_issues, feed_reasons
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
    per_courier = parcels.groupby("courier_id").agg(
        packages_held=("order_id", "size"),
        feed_age_min=("feed_age_min", "first"),
        model_used=("model_used", "first"),
        issue=("feed_issue", "first"),
        reason=("feed_reason", "first"),
    )
    couriers = per_courier.join(positions.set_axis(positions.index.astype(str)), how="inner").reset_index()
    return {"baseline_at": baseline_at, "couriers": _on_map(couriers), "parcels": _on_map(parcels)}


def _on_map(frame: pd.DataFrame) -> pd.DataFrame:
    """LaDe coordinates are GCJ-02; web maps use WGS-84."""
    frame = frame.copy()
    frame["lat"], frame["lng"] = gcj02_to_wgs84(frame["lat"], frame["lng"])
    return frame
