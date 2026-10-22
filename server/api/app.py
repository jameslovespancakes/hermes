"""HTTP API (under /api) and the built frontend: uvicorn server.api.app:create_app --factory."""

import os
import threading
from collections import OrderedDict
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, FastAPI, Query

from server.api.frontend import DIST, mount_frontend
from server.api.schemas import (
    CourierPosition,
    DataHealth,
    Health,
    Moment,
    Overview,
    PackageETA,
    ParcelStatus,
    PredictRequest,
    PredictResponse,
    format_moment,
    parse_moment,
)
from server.data.loading import load_city
from server.serving.overview import build_overview
from server.serving.predictor import LiveETAPredictor

CACHE_SIZE = 8
MomentQuery = Annotated[Moment, Query(examples=["09-20 10:30:00"])]


class PreparedCache:
    """Thread-safe LRU of package tables by moment (the expensive step)."""

    def __init__(self, size: int):
        self.size, self.lock = size, threading.Lock()
        self.items: OrderedDict[pd.Timestamp, pd.DataFrame] = OrderedDict()

    def get(self, at: pd.Timestamp, build: Callable[[], pd.DataFrame]) -> pd.DataFrame:
        with self.lock:
            if at in self.items:
                self.items.move_to_end(at)
                return self.items[at]
        value = build()
        with self.lock:
            self.items[at] = value
            while len(self.items) > self.size:
                self.items.popitem(last=False)
        return value


def create_app(
    predictor: LiveETAPredictor | None = None, records: pd.DataFrame | None = None, frontend: Path | None = DIST
) -> FastAPI:
    state: dict = {}

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        state["predictor"] = predictor or LiveETAPredictor.from_store(os.environ.get("ETA_CITY", "yt"))
        state["records"] = records if records is not None else load_city(state["predictor"].city)[0]
        state["cache"] = PreparedCache(CACHE_SIZE)
        yield
        state.clear()

    def prepared(at: pd.Timestamp) -> pd.DataFrame:
        return state["cache"].get(at, lambda: state["predictor"].prepare(state["records"], at))

    api = APIRouter(prefix="/api")

    @api.get("/health", response_model=Health)
    def health() -> Health:
        bundle = state["predictor"].bundle
        return Health(status="ok", city=bundle.city, trained_through=bundle.trained_through, records=len(state["records"]))

    @api.post("/predict", response_model=PredictResponse)
    def predict(request: PredictRequest) -> PredictResponse:
        at = parse_moment(request.at)
        result = state["predictor"].predict_couriers(prepared(at), [request.courier_id], at)
        packages = [
            PackageETA(
                order_id=int(r.order_id),
                minutes_remaining=round(float(r.minutes_remaining), 1),
                predicted_delivery_at=format_moment(r.predicted_delivery_at),
                predicted_position=int(r.predicted_position),
                packages_held=int(r.packages_held),
                minutes_since_accepted=float(r.minutes_since_accepted),
                feed_age_min=float(r.feed_age_min),
                upload_lag_min=float(r.upload_lag_min),
                model_used=str(r.model_used),
                needs_review=bool(r.needs_review),
                review_reasons=list(r.review_reasons),
                risk_min=round(float(r.risk_min), 1),
                uncertain=bool(r.uncertain),
            )
            for r in result.itertuples(index=False)
        ]
        return PredictResponse(city=state["predictor"].city, courier_id=request.courier_id, at=request.at, packages=packages)

    @api.get("/overview", response_model=Overview)
    def overview(at: MomentQuery) -> Overview:
        view = build_overview(state["predictor"], prepared, state["records"], parse_moment(at))
        parcels = [
            ParcelStatus(
                order_id=int(r.order_id),
                courier_id=str(r.courier_id),
                lat=float(r.lat),
                lng=float(r.lng),
                position=int(r.predicted_position),
                eta=format_moment(r.predicted_delivery_at),
                minutes_remaining=round(float(r.minutes_remaining), 1),
                baseline_eta=None if pd.isna(r.baseline_eta) else format_moment(r.baseline_eta),
                slip_min=None if pd.isna(r.slip_min) else round(float(r.slip_min), 1),
                issue=r.issue,
                reasons=list(r.reasons),
            )
            for r in view["parcels"].itertuples(index=False)
        ]
        couriers = [
            CourierPosition(
                courier_id=str(r.courier_id),
                lat=float(r.lat),
                lng=float(r.lng),
                packages_held=int(r.packages_held),
                feed_age_min=float(r.feed_age_min),
                model_used=str(r.model_used),
            )
            for r in view["couriers"].itertuples(index=False)
        ]
        return Overview(city=state["predictor"].city, at=at, baseline_at=format_moment(view["baseline_at"]), couriers=couriers, parcels=parcels)

    @api.get("/data-health", response_model=DataHealth)
    def data_health(at: MomentQuery) -> DataHealth:
        moment = parse_moment(at)
        report = state["predictor"].data_health(state["records"], prepared(moment), moment)
        drift = report["drift"]
        return DataHealth(
            at=at,
            status=report["status"],
            records_checked=report["records_checked"],
            contract_passed=report["contract_passed"],
            contract=report["contract"],
            drift_psi=drift["psi"] if drift else None,
            drift_levels=drift["levels"] if drift else None,
        )

    app = FastAPI(title="Hermes live ETA", version="1.0.0", lifespan=lifespan)
    app.include_router(api)
    if frontend is not None:
        mount_frontend(app, frontend)
    return app

