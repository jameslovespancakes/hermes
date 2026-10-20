"""Request/response models for the HTTP API. Times use the source format 'MM-DD HH:MM:SS' (no year)."""

import pandas as pd
from pydantic import BaseModel, Field, field_validator

from server.config import PARSE_YEAR

TIME_PATTERN = r"^\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"


def parse_moment(text: str) -> pd.Timestamp:
    return pd.Timestamp(f"{PARSE_YEAR}-{text}")


def format_moment(moment: pd.Timestamp) -> str:
    return moment.strftime("%m-%d %H:%M:%S")


class PredictRequest(BaseModel):
    courier_id: str = Field(description="Raw courier id from the source data", examples=["2136"])
    at: str = Field(pattern=TIME_PATTERN, description="Moment to predict at, 'MM-DD HH:MM:SS'", examples=["09-20 10:30:00"])

    @field_validator("courier_id", mode="before")
    @classmethod
    def _as_text(cls, value):
        return str(value)

    @field_validator("at")
    @classmethod
    def _valid_moment(cls, value: str) -> str:
        try:
            parse_moment(value)
        except ValueError as error:
            raise ValueError(f"not a valid date/time: {value}") from error
        return value


class PackageETA(BaseModel):
    order_id: int
    minutes_remaining: float
    predicted_delivery_at: str
    predicted_position: int
    packages_held: int
    minutes_since_accepted: float


class PredictResponse(BaseModel):
    city: str
    courier_id: str
    at: str
    packages: list[PackageETA]


class CourierLoad(BaseModel):
    courier_id: str
    packages_held: int


class Health(BaseModel):
    status: str
    city: str
    trained_through: str
    records: int
