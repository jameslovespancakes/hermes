"""Central configuration: paths, dataset pin, evaluation windows, feature lists, and model settings."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

SERVER_DIR = Path(__file__).resolve().parent
ROOT = SERVER_DIR.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
MODEL_STORE = SERVER_DIR / "model_store"

HF_REPO = "Cainiao-AI/LaDe"
HF_REVISION = "be2cec02775cafc8d52230303f32134382bcc50b"
CITIES = {"yt": "Yantai", "jl": "Jilin", "cq": "Chongqing", "hz": "Hangzhou", "sh": "Shanghai"}
ROAD_CITY = {"yt": "烟台市", "jl": "吉林市", "cq": "重庆市", "hz": "杭州市", "sh": "上海市"}
RIGHTS = (
    "Provided by the W&M AI Case-a-thon organizers for this exercise; use confirmed with the case owners. "
    "Public metadata differs (Hugging Face: Apache-2.0; LaDe paper: CC BY-NC 4.0), so keep attribution and "
    "non-commercial use. No attempt to reidentify anonymized couriers or locations."
)

PARSE_YEAR = 2000
RAW_COLUMNS = [
    "order_id",
    "region_id",
    "courier_id",
    "aoi_id",
    "aoi_type",
    "lng",
    "lat",
    "accept_time",
    "accept_gps_time",
    "accept_gps_lng",
    "accept_gps_lat",
    "delivery_time",
    "delivery_gps_lng",
    "delivery_gps_lat",
]
CATEGORICAL = ["region_id", "courier_id", "aoi_id", "aoi_type"]
CATS = CATEGORICAL + ["city"]


def ts(month_day: str) -> pd.Timestamp:
    """'MM-DD' -> Timestamp in the parsing-anchor year."""
    return pd.Timestamp(f"{PARSE_YEAR}-{month_day}")


@dataclass(frozen=True)
class Split:
    """Chronological windows. Fit rows need outcomes known by fit_end; October is never loaded by default."""

    start: str = "05-01"
    fit_end: str = "09-01"
    stop_end: str = "09-16"
    test_end: str = "10-01"

    @property
    def fit_cutoff(self) -> pd.Timestamp:
        return ts(self.fit_end)

    @property
    def stop_cutoff(self) -> pd.Timestamp:
        return ts(self.stop_end)

    @property
    def data_cutoff(self) -> pd.Timestamp:
        return ts(self.test_end)


DEFAULT_SPLIT = Split()

SEED = 42
FIT_SAMPLE = 800_000
HABIT_WINDOW_DAYS = 28
ROUTE_FOLDS = 5

PACKAGE_COLS = ["region_id", "aoi_id", "aoi_type", "courier_id", "lng", "lat", "accept_hour", "straight_line_km"]
LIVE_COLS = [
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
]
TRANSITION_COLS = ["p_courier_next_area", "p_all_next_area", "courier_transition_support", "p_courier_next_area_rank", "p_all_next_area_rank"]
AREA_COLS = [
    f"{level}_{name}" for level in ("aoi", "region", "city") for name in ("deliveries_60m", "recent_duration_180m", "accepted_60m", "pending_now")
] + ["aoi_recent_vs_usual"]
COURIER_RECENT_COLS = ["courier_3d_deliveries", "courier_3d_pace_min", "courier_3d_package_min", "pace_vs_3d"]
GPS_COLS = ["last_confirm_km_from_address", "dist_from_courier_gps_km", "dist_rank_gps", "far_confirm_share_today"]
DEPOT_COLS = ["dist_from_depot_km", "dist_rank_depot", "dist_from_position_or_depot_km", "dist_rank_position_or_depot"]
ZONE_COLS = [
    "zone_is_current",
    "zone_pending",
    "p_zone_next_all",
    "p_zone_next_courier",
    "zone_usual_clock_rel_now",
    "p_zone_next_all_rank",
    "p_zone_next_courier_rank",
    "zone_usual_rank_now",
]
ZONE_MODEL_COLS = ["p_zone_model", "p_zone_model_rank"]
ROUTE_INPUT_COLS = (
    [c for c in LIVE_COLS if c != "est_stops_x_pace"]
    + ["hab_ca_count", "hab_ca_typical_duration", "hab_cab_minutes_until_usual_delivery", "hab_a_minutes_until_usual_delivery", "elapsed_rank"]
    + TRANSITION_COLS
    + GPS_COLS
    + DEPOT_COLS
    + ZONE_COLS
    + ZONE_MODEL_COLS
)
ROUTE_OUTPUT_COLS = ["route_score", "route_ahead", "route_ahead_x_pace"]

ROUTE_PARAMS: dict[str, Any] = {
    "objective": "regression",
    "n_estimators": 500,
    "learning_rate": 0.05,
    "num_leaves": 255,
    "min_child_samples": 50,
    "colsample_bytree": 0.8,
    "subsample": 0.8,
    "subsample_freq": 1,
}
ETA_PARAMS: dict[str, Any] = {
    "objective": "regression_l1",
    "n_estimators": 3000,
    "learning_rate": 0.05,
    "num_leaves": 255,
    "min_child_samples": 50,
    "reg_lambda": 5.0,
    "colsample_bytree": 0.45,
    "subsample": 0.8,
    "subsample_freq": 1,
}
ENSEMBLE_SEEDS = (42, 1, 2)
ZONE_SIZE = 10
EARLY_STOPPING_ROUNDS = 80
THREADS = 16

HORIZONS = [
    ("under_30_min", 0, 30),
    ("30_to_60_min", 30, 60),
    ("1_to_3_hours", 60, 180),
    ("3_to_24_hours", 180, 1440),
    ("over_24_hours", 1440, float("inf")),
]
