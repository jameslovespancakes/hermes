"""Request/response models for the HTTP API. Times use the source format 'MM-DD HH:MM:SS' (no year)."""

from typing import Annotated, Literal

import pandas as pd
from pydantic import AfterValidator, BaseModel, BeforeValidator, Field, StringConstraints

from server.config import PARSE_YEAR

TIME_PATTERN = r"^\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"


def parse_moment(text: str) -> pd.Timestamp:
    return pd.Timestamp(f"{PARSE_YEAR}-{text}")


def format_moment(moment: pd.Timestamp) -> str:
    return moment.strftime("%m-%d %H:%M:%S")


def _valid(text: str) -> str:
    parse_moment(text)
    return text


Moment = Annotated[str, StringConstraints(pattern=TIME_PATTERN), AfterValidator(_valid)]


class PredictRequest(BaseModel):
    city: str = Field(examples=["yt"])
    courier_id: Annotated[str, BeforeValidator(str)] = Field(examples=["2136"])
    at: Moment = Field(examples=["09-20 10:30:00"])


class PackageETA(BaseModel):
    order_id: int
    minutes_remaining: float
    predicted_delivery_at: str
    predicted_position: int
    packages_held: int
    minutes_since_accepted: float
    feed_age_min: float = Field(description="Minutes since the courier's last recorded event")
    upload_lag_min: float = Field(description="How far the courier's feed runs behind (receive time - event time)")
    model_used: str = Field(description="'standard', or 'staleness' when the courier's feed is stale")
    needs_review: bool = Field(description="True when a dispatcher should check this ETA")
    review_reasons: list[str]
    risk_min: float = Field(description="Expected size of this ETA's error, in minutes")
    uncertain: bool = Field(description="True for the riskiest 10% of estimates")


class PredictResponse(BaseModel):
    city: str
    courier_id: str
    at: str
    packages: list[PackageETA]


class ContractCheck(BaseModel):
    check: str
    observed: float
    threshold: float
    passed: bool


class DataHealth(BaseModel):
    at: str
    status: str = Field(description="'ok', 'watch' (inputs drifting), or 'act' (contract failed or strong drift)")
    records_checked: int
    contract_passed: bool
    contract: list[ContractCheck]
    drift_psi: dict[str, float] | None
    drift_levels: dict[str, str] | None


class CourierPosition(BaseModel):
    city: str
    courier_id: str
    lat: float
    lng: float
    packages_held: int
    feed_age_min: float
    model_used: str
    issue: Literal["lagging", "silent", "bulk", "clock"] | None = Field(description="A problem with the courier's device feed")
    reason: str | None


class ParcelStatus(BaseModel):
    city: str
    order_id: int
    courier_id: str
    lat: float
    lng: float
    position: int = Field(description="Predicted stop number on the courier's route (1 = next)")
    accepted_at: str = Field(description="When the courier accepted the parcel")
    eta: str
    minutes_remaining: float
    baseline_eta: str | None = Field(description="The ETA the model gave at `baseline_at` (none if not yet held then)")
    slip_min: float | None = Field(description="Minutes the ETA moved since `baseline_at` (positive = later)")
    issue: Literal["moved", "resent", "missed", "suspect", "late"] | None
    reasons: list[str]


class Overview(BaseModel):
    city: str
    at: str
    baseline_at: str
    couriers: list[CourierPosition]
    parcels: list[ParcelStatus]


class RouteRequest(BaseModel):
    city: str = Field(examples=["yt"])
    points: list[tuple[float, float]] = Field(min_length=2, description="(lng, lat) stops in visiting order")


class Route(BaseModel):
    coordinates: list[tuple[float, float]] = Field(description="(lng, lat) road path through the stops")


class City(BaseModel):
    id: str
    name: str
    bounds: tuple[tuple[float, float], tuple[float, float]] = Field(description="South-west and north-east (lng, lat) corners")


class Health(BaseModel):
    status: str
    cities: list[str]
