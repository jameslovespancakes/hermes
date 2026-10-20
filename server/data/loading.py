"""Load a verified city delivery file and clean it into one row per package (no model features here)."""

import json

import pandas as pd

from server.config import CATEGORICAL, DATA_DIR, PARSE_YEAR, RAW_COLUMNS, ROOT
from server.data.download import sha256_file


def parse_time(values: pd.Series) -> pd.Series:
    """'MM-DD HH:MM:SS' strings -> timestamps in the anchor year; unparseable -> NaT."""
    return pd.to_datetime(f"{PARSE_YEAR}-" + values.astype("string"), format="%Y-%m-%d %H:%M:%S", errors="coerce")


def clean_records(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Drop records with undefined labels (not merely unusual ones); sort chronologically.

    Removed, in order: missing order id, duplicated order ids (all copies), unparseable times, negative
    durations. Long and zero durations are kept.
    """
    frame = raw.rename(columns={"package_id": "order_id"}) if "order_id" not in raw and "package_id" in raw else raw.copy()
    missing = set(CATEGORICAL + ["order_id", "accept_time", "delivery_time", "accept_gps_time",
                                 "lng", "lat", "accept_gps_lng", "accept_gps_lat"]) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required fields: {sorted(missing)}")
    frame["accepted_at"] = parse_time(frame["accept_time"])
    frame["delivered_at"] = parse_time(frame["delivery_time"])
    frame["accept_gps_at"] = parse_time(frame["accept_gps_time"])
    frame["duration_minutes"] = (frame["delivered_at"] - frame["accepted_at"]).dt.total_seconds() / 60
    exclusions = {}
    for reason, rule in [("missing_order_id", lambda f: f["order_id"].isna()),
                         ("duplicate_order_id_all_occurrences", lambda f: f["order_id"].duplicated(keep=False)),
                         ("unparseable_accept_or_delivery_time", lambda f: f["accepted_at"].isna() | f["delivered_at"].isna()),
                         ("negative_duration", lambda f: f["duration_minutes"] < 0)]:
        mask = rule(frame)
        exclusions[reason] = int(mask.sum())
        frame = frame.loc[~mask].copy()
    frame = frame.sort_values(["accepted_at", "order_id"]).reset_index(drop=True)
    if frame.empty:
        raise ValueError("No usable labeled deliveries")
    return frame, exclusions


def load_city(city: str, accepted_before: pd.Timestamp | None = None) -> tuple[pd.DataFrame, dict]:
    """Read data/raw/delivery_<city>.csv after checking it against its manifest checksum."""
    manifest = json.loads((DATA_DIR / f"manifest_{city}.json").read_text(encoding="utf-8"))
    path = ROOT / manifest["local_file"]
    if sha256_file(path) != manifest["sha256"]:
        raise ValueError(f"{city}: checksum mismatch against manifest")
    frame, exclusions = clean_records(pd.read_csv(path, usecols=RAW_COLUMNS))
    if accepted_before is not None:
        frame = frame.loc[frame["accepted_at"] < accepted_before].reset_index(drop=True)
    return frame, exclusions
