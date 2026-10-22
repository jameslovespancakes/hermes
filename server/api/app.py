"""HTTP API for the live ETA model (FastAPI).

Run: uvicorn server.api.app:app --host 0.0.0.0 --port 8000   (city from $ETA_CITY, default 'yt')
At startup it loads the trained bundle from server/model_store/<city>/ and that city's delivery log; every
request replays the log as it was at the requested moment, so no answer can use later information.
Records are cleaned by the bundle's DataGuard, stale couriers get the staleness-aware model, doubtful ETAs are
flagged for review, and /data-health reports the data contract and input drift for the past day.
"""

import json
import os
import threading
from collections import OrderedDict
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

from server.api.frontend import mount_frontend
from server.api.schemas import (
    TIME_PATTERN,
    CourierLoad,
    CourierPosition,
    DataHealth,
    Health,
    Overview,
    PackageETA,
    ParcelStatus,
    PredictRequest,
    PredictResponse,
    format_moment,
    parse_moment,
)
from server.config import MODEL_STORE
from server.data.loading import load_city
from server.serving.overview import build_overview
from server.serving.predictor import LiveETAPredictor, couriers_holding

PREPARED_CACHE_SIZE = 8  # package tables kept for recently requested moments (overview uses two per request)


class _PreparedCache:
    """Small thread-safe LRU of package tables keyed by request moment (the expensive step)."""

    def __init__(self, size: int):
        self.size, self.lock = size, threading.Lock()
        self.items: OrderedDict[pd.Timestamp, pd.DataFrame] = OrderedDict()

    def get(self, at: pd.Timestamp, build):
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


def create_app(predictor: LiveETAPredictor | None = None, records: pd.DataFrame | None = None, city: str | None = None) -> FastAPI:
    """App factory. Pass `predictor`/`records` to inject them (tests); otherwise loaded at startup."""
    city = city or os.environ.get("ETA_CITY", "yt")
    state: dict = {}

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        state["predictor"] = predictor or LiveETAPredictor.from_store(city)
        state["records"] = records if records is not None else load_city(state["predictor"].city)[0]
        state["cache"] = _PreparedCache(PREPARED_CACHE_SIZE)
        yield
        state.clear()

    app = FastAPI(
        title="Live delivery ETA",
        version="1.0.0",
        lifespan=lifespan,
        description="Minutes until each pending package is delivered, from LaDe-D courier logs.",
    )

    @app.get("/health", response_model=Health)
    def health() -> Health:
        bundle = state["predictor"].bundle
        return Health(status="ok", city=bundle.city, trained_through=bundle.trained_through, records=len(state["records"]))

    @app.get("/model")
    def model_info() -> dict:
        bundle = state["predictor"].bundle
        metrics_path = MODEL_STORE / bundle.city / "metrics.json"
        metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else bundle.info
        return {
            "city": bundle.city,
            "trained_through": bundle.trained_through,
            "eta_features": len(bundle.eta.columns),
            "safeguards": {
                "data_guard": bundle.guard is not None,
                "staleness_model": bundle.staleness is not None,
                "monitoring": bundle.monitor is not None,
            },
            "test_overall": metrics.get("overall", metrics.get("metrics_overall")),
            "test_by_time_remaining": metrics.get("by_time_remaining"),
            "route": metrics.get("route"),
        }

    @app.get("/couriers", response_model=list[CourierLoad])
    def couriers(at: str = Query(pattern=TIME_PATTERN, examples=["09-20 10:30:00"]), limit: int = Query(20, ge=1, le=500)):
        """Couriers holding packages at a moment (busiest first) - handy for choosing a courier to query."""
        loads = couriers_holding(state["records"], _moment(at)).head(limit)
        return [CourierLoad(courier_id=str(c), packages_held=int(n)) for c, n in loads.items()]

    @app.post("/predict", response_model=PredictResponse)
    def predict(request: PredictRequest) -> PredictResponse:
        at = _moment(request.at)
        predictor_ = state["predictor"]
        packages = state["cache"].get(at, lambda: predictor_.prepare(state["records"], at))
        result = predictor_.predict_prepared(packages, request.courier_id, at)
        rows = [
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
                risk_min=None if pd.isna(r.risk_min) else round(float(r.risk_min), 1),
                uncertain=bool(r.uncertain),
            )
            for r in result.itertuples(index=False)
        ]
        return PredictResponse(city=predictor_.city, courier_id=request.courier_id, at=request.at, packages=rows)

    @app.get("/overview", response_model=Overview)
    def overview(at: str = Query(pattern=TIME_PATTERN, examples=["09-20 10:30:00"])) -> Overview:
        """Every pending parcel in the city: ETA now vs an hour earlier, and the ones a dispatcher should look at."""
        moment = _moment(at)
        predictor_ = state["predictor"]

        def prepared(m: pd.Timestamp) -> pd.DataFrame:
            return state["cache"].get(m, lambda: predictor_.prepare(state["records"], m))

        view = build_overview(predictor_, prepared, state["records"], moment)
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
        return Overview(city=predictor_.city, at=at, baseline_at=format_moment(view["baseline_at"]), couriers=couriers, parcels=parcels)

    @app.get("/data-health", response_model=DataHealth)
    def data_health(at: str = Query(pattern=TIME_PATTERN, examples=["09-20 10:30:00"])) -> DataHealth:
        """Data contract on records delivered in the 24 h before `at`, and drift of current live inputs vs training."""
        moment = _moment(at)
        predictor_ = state["predictor"]
        if predictor_.bundle.monitor is None:
            raise HTTPException(status_code=409, detail="this model bundle has no monitoring baseline; retrain it")
        packages = state["cache"].get(moment, lambda: predictor_.prepare(state["records"], moment))
        report = predictor_.data_health(state["records"], packages, moment)
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

    mount_frontend(app)
    return app


def _moment(text: str) -> pd.Timestamp:
    try:
        return parse_moment(text)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=f"not a valid date/time: {text}") from error


app = create_app()
