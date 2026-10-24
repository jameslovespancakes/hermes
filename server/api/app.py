"""HTTP API (under /api) and the built frontend: uvicorn server.api.app:create_app --factory."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, FastAPI, HTTPException, Query

from server.api.frontend import DIST, mount_frontend
from server.api.schemas import (
    City,
    CourierPosition,
    DataHealth,
    Health,
    Moment,
    Overview,
    PackageETA,
    ParcelStatus,
    PredictRequest,
    PredictResponse,
    Route,
    RouteRequest,
    format_moment,
    parse_moment,
)
from server.config import CITIES
from server.serving.city import Cities, CityService, bounds

MomentQuery = Annotated[Moment, Query(examples=["09-20 10:30:00"])]
CityQuery = Annotated[str, Query(alias="city", examples=["yt"])]


def create_app(services: dict[str, CityService] | None = None, frontend: Path | None = DIST) -> FastAPI:
    state: dict = {}

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        state["cities"] = Cities(services)
        if services is None:
            state["cities"].warm()
        yield
        state.clear()

    def city(name: str) -> CityService:
        if name not in state["cities"]:
            raise HTTPException(status_code=404, detail=f"no model for city '{name}'")
        return state["cities"][name]

    api = APIRouter(prefix="/api")

    @api.get("/health", response_model=Health)
    def health() -> Health:
        return Health(status="ok", cities=sorted(state["cities"].predictors))

    @api.get("/cities", response_model=list[City])
    def cities() -> list[City]:
        return [City(id=c, name=CITIES[c], bounds=bounds(p)) for c, p in state["cities"].predictors.items()]

    @api.post("/predict", response_model=PredictResponse)
    def predict(request: PredictRequest) -> PredictResponse:
        service, at = city(request.city), parse_moment(request.at)
        result = service.predictor.predict_couriers(service.prepared(at), [request.courier_id], at)
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
        return PredictResponse(city=request.city, courier_id=request.courier_id, at=request.at, packages=packages)

    @api.get("/overview", response_model=Overview)
    def overview(city_id: CityQuery, at: MomentQuery) -> Overview:
        moment = parse_moment(at)
        view = city(city_id).overview(moment)
        parcels = [
            ParcelStatus(
                city=city_id,
                order_id=int(r.order_id),
                courier_id=str(r.courier_id),
                lat=float(r.lat),
                lng=float(r.lng),
                position=int(r.predicted_position),
                accepted_at=format_moment(moment - pd.Timedelta(minutes=float(r.minutes_since_accepted))),
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
                city=city_id,
                courier_id=str(r.courier_id),
                lat=float(r.lat),
                lng=float(r.lng),
                packages_held=int(r.packages_held),
                feed_age_min=float(r.feed_age_min),
                model_used=str(r.model_used),
                issue=None if pd.isna(r.issue) else str(r.issue),
                reason=None if pd.isna(r.reason) else str(r.reason),
            )
            for r in view["couriers"].itertuples(index=False)
        ]
        return Overview(city=city_id, at=at, baseline_at=format_moment(view["baseline_at"]), couriers=couriers, parcels=parcels)

    @api.get("/data-health", response_model=DataHealth)
    def data_health(city_id: CityQuery, at: MomentQuery) -> DataHealth:
        service, moment = city(city_id), parse_moment(at)
        report = service.health(moment)
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

    @api.post("/route", response_model=Route)
    def route(request: RouteRequest) -> Route:
        return Route(coordinates=city(request.city).roads.path(request.points))

    app = FastAPI(title="Hermes live ETA", version="1.0.0", lifespan=lifespan)
    app.include_router(api)
    if frontend is not None:
        mount_frontend(app, frontend)
    return app
