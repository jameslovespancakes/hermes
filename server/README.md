# server — live delivery ETA (LaDe-D)

Predicts **minutes until each pending package is delivered**, re-predicted after every courier delivery.
Best model from our research (see `../research.md`): a LightGBM **route-order model** feeding a LightGBM
**ETA model**, built only from information available at the moment of prediction, and protected against
stale and low-quality courier data (see "Data-quality safeguards").

| Yantai, test Sep 16-30 (October untouched) | Result |
|---|---:|
| Mean absolute error, all live predictions | **58.4 min** |
| Median absolute error | **29.0 min** |
| Packages due within 30 / 30-60 min / 1-3 h | 33.0 / 33.5 / 35.6 min |
| Route: true next stop predicted first / next-3 hit rate | 45.0% / 68.8% |

## Layout
```
server/
├── config.py            paths, dataset pin, windows, feature lists, model settings
├── cli.py               python -m server.cli {download,train,predict}
├── data/
│   ├── download.py      pinned Hugging Face download + checksum verification
│   ├── loading.py       parse + clean records (drops undefined labels only)
│   └── splits.py        chronological fit / early-stopping / test rows
├── features/
│   ├── geometry.py      haversine, nearest-stop tour, ranks
│   ├── package.py       per-package inputs known at acceptance (city-scoped IDs)
│   ├── habits.py        courier/area habits from previous days (28-day window)
│   ├── live.py          pending sets and live features at a courier event
│   └── transitions.py   area-to-area movement habits (leave-one-day-out in training)
├── models/
│   ├── encoding.py      categorical vocabularies from training rows only
│   ├── route.py         route-order model (out-of-fold by courier-day)
│   ├── eta.py           ETA model (absolute-error objective, early stopping)
│   └── bundle.py        the trained bundle: models + guard + monitoring baseline
├── pipeline/
│   ├── features.py      shared feature assembly (training and serving)
│   ├── staleness.py     training rows with simulated upload delays (staleness-aware model)
│   ├── train.py         train -> evaluate -> gate against the stored model -> store
│   └── evaluate.py      error by time remaining; route-order quality; review flags
├── quality/
│   ├── config.py        every data-quality threshold, in one place
│   ├── detectors.py     re-sent records, GPS offsets, bulk-synced timestamps
│   ├── guard.py         DataGuard (clean before training and serving) + review flags
│   ├── contract.py      daily data contract (expectations every batch must meet)
│   ├── drift.py         input drift (PSI) with thresholds calibrated on clean history
│   ├── monitor.py       monitoring baseline + data-health check
│   └── gating.py        retrained model replaces the stored one only if better on audited deliveries
├── serving/
│   └── predictor.py     LiveETAPredictor: guard -> features -> standard or staleness-aware model -> flags
├── api/
│   ├── app.py           FastAPI app: /health, /model, /couriers, /predict, /data-health
│   └── schemas.py       request/response models
├── tests/               unit tests, one file per module (synthetic data, a few seconds)
└── model_store/<city>/  model.pkl, metrics.json, manifest.json
```

## Use (from the repository root)
Dependencies are pinned in the root `pyproject.toml` / `uv.lock` and managed with uv:
```powershell
uv sync
uv run python -m server.cli download --city yt
uv run python -m unittest discover -s server/tests -t .
uv run python -m server.cli train --city yt                 # ~15 min on 16 CPU threads
uv run python -m server.cli predict --city yt --courier 2136 --at "09-20 10:30:00"
```
Add a dependency with `uv add <package>==<version>`; lint with `uv run ruff check server`.

## HTTP API and Docker
```powershell
uv run uvicorn server.api.app:app --port 8000          # local; city from $ETA_CITY (default yt)
docker build -t hermes-eta .                            # image downloads the pinned, checksum-verified data
docker run --rm -p 8000:8000 hermes-eta                 # then open http://localhost:8000/docs
```
| Endpoint | Purpose |
|---|---|
| `GET /health` | status, city, model cutoff, records loaded |
| `GET /model` | stored test metrics (overall, by time remaining, route quality) |
| `GET /couriers?at=09-20 10:30:00` | couriers holding packages at that moment, busiest first |
| `POST /predict` `{"courier_id": "2136", "at": "09-20 10:30:00"}` | ETA for each package the courier holds, in predicted route order, with `model_used` and `needs_review` |
| `GET /data-health?at=09-20 10:30:00` | data contract on the past 24 h of records + input drift vs training: `ok` / `watch` / `act` |

The first request for a new moment takes a few seconds (it rebuilds what was known then); repeat requests for
that moment are cached.

CI (`.github/workflows/ci.yml`) runs the lint and unit tests on every push.

In Python:
```python
import pandas as pd
from server.data.loading import load_city
from server.serving.predictor import LiveETAPredictor

records, _ = load_city("yt")
etas = LiveETAPredictor.from_store("yt").predict(records, courier_id=2136, at=pd.Timestamp("2000-09-20 10:30"))
```
Source timestamps have no year; `2000` is only a parsing anchor.

## Data-quality safeguards
Validated on a simulated bad-data timeline (results: `../evidence/degradation/REPORT.md`); thresholds in `quality/config.py`.

| Problem | Safeguard | Where |
|---|---|---|
| Re-sent duplicate records | dropped before features are built | `DataGuard` (training and serving) |
| Implausible GPS (far from its delivery area) | repaired to the area's usual point | `DataGuard` |
| Bulk-synced delivery times | courier-days quarantined from training; flagged when serving | `DataGuard`, review flags |
| Late uploads (stale feed) | event time drives features, receive time drives visibility; staleness-aware model takes over when feed age > 20 min or upload lag > 10 min | `features/live.py`, `LiveETAPredictor` |
| Doubtful ETAs | `needs_review` + reasons on every prediction | `/predict` |
| Bad batches / shifting inputs | daily data contract + PSI drift alerts | `/data-health` |
| Retraining on bad data | new model stored only if better on a 10% audited sample; otherwise saved under `candidate/` | `pipeline/train.py` |

## How leakage is prevented
- **Splits:** fit on events before Sep 1 whose outcomes were known before Sep 1; early-stop on Sep 1-15;
  test on Sep 16-30 with every outcome kept. October is never loaded by `train`.
- **Features:** habits use deliveries completed on previous days only; live features use only deliveries at or
  before the event; transitions exclude each training event's own courier-day; category vocabularies come
  from training rows.
- **Route model:** training-period predictions are out-of-fold by courier-day before the ETA model sees them.
- **Serving:** `known_at()` drops records accepted after the query time and hides deliveries recorded after it.
- Tests in `tests/` check each of these.

## Limits
- Trained and evaluated on one city (Yantai) and one test window; September was inspected during development.
- Recorded completion is a proxy for receipt; source timestamps appear processed (consecutive deliveries are
  never under 5 minutes apart). Coordinates are privacy-perturbed; distances are straight-line.
- Models are trained at delivery checkpoints; predictions are most representative right after a delivery.
  `predict` rebuilds features from the full history for clarity, not speed.
- `model.pkl` is a pickle: load only files this project produced.
- The safeguards recover most, not all, of the damage from bad data; GPS repair catches about a third of jittered
  coordinates, and retraining gates cannot catch a slow decline that also affects the audited sample.
- Data: provided by the case organizers (use confirmed with the case owners); raw CSVs are stored with Git LFS.
  Keep LaDe attribution and non-commercial use.
