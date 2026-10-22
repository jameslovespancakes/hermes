"""Feature assembly shared by training and serving."""

import pandas as pd

from server.config import (
    AREA_COLS,
    COURIER_RECENT_COLS,
    DEPOT_COLS,
    GPS_COLS,
    LIVE_COLS,
    PACKAGE_COLS,
    ROUTE_OUTPUT_COLS,
    TRANSITION_COLS,
    ZONE_COLS,
    ZONE_MODEL_COLS,
)
from server.features.context import context_features
from server.features.habits import habit_features
from server.features.live import annotate_events, build_live_queries
from server.features.package import package_features
from server.features.transitions import add_transitions


def package_table(records: pd.DataFrame, city: str) -> pd.DataFrame:
    """Package inputs plus previous-day habits, one row per package."""
    packages = package_features(records, city)
    return pd.concat([packages, habit_features(packages)], axis=1)


def habit_columns(packages: pd.DataFrame) -> list[str]:
    return [c for c in packages.columns if c.startswith("hab_")]


def live_table(packages: pd.DataFrame, transition_cutoff: pd.Timestamp, events: pd.DataFrame | None = None) -> pd.DataFrame:
    """Live rows: package, habit, transition and context inputs (zones and model outputs come from the bundle)."""
    live = build_live_queries(packages, events)
    if live.empty:
        return live
    live = annotate_events(live, packages, PACKAGE_COLS + habit_columns(packages))
    live = add_transitions(live, packages, transition_cutoff)
    return pd.concat([live, context_features(live, packages)], axis=1)


def eta_columns(habit_cols: list[str]) -> list[str]:
    context = AREA_COLS + COURIER_RECENT_COLS + GPS_COLS + DEPOT_COLS + ZONE_COLS + ZONE_MODEL_COLS
    return PACKAGE_COLS + habit_cols + LIVE_COLS + TRANSITION_COLS + context + ROUTE_OUTPUT_COLS


def checkpoints(records: pd.DataFrame, city: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Every recorded courier delivery moment in [start, end): when the live system re-predicts."""
    sel = records.loc[(records["delivered_at"] >= start) & (records["delivered_at"] < end)]
    return pd.DataFrame({"courier_id": f"{city}:" + sel["courier_id"].astype(str), "s": sel["delivered_at"]}).drop_duplicates()
