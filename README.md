<p align="center">
  <img src=".github/readme/logo.svg" alt="Hermes" width="64" />
</p>

<h1 align="center">Hermes</h1>

<p align="center">
  Route-first delivery ETA prediction on LaDe-D courier logs.
  <br />
  <a href="https://tryhermes.org">Website</a> ·
  <a href="https://tryhermes.org/benchmarks">Benchmarks</a> ·
  <a href="https://tryhermes.org/methodology">Methodology</a>
</p>

<p align="center">
  <img src=".github/readme/hero.jpg" alt="Hermes homepage" width="100%" />
</p>

## ETA accuracy

Predict minutes remaining for each pending package after every courier delivery. A stop-order model feeds a LightGBM ETA ensemble; a today-or-later classifier and a next-day model handle parcels likely to be held.

**Evaluation:** one model per city; fit on everything before September 1, early stopping on September 1 to 15, test once on September 16 to 30. October is never used. Metrics are per prediction, not per unique package; MAE means mean absolute error.

| City | Test predictions | Packages | MAE (min) | Median error (min) | Within 30 min | Next 3 stops in top 3 |
|---|---:|---:|---:|---:|---:|---:|
| Yantai | 155,296 | 14,234 | **55.9** | 26.9 | 53.6% | 70.9% |
| Jilin | 37,291 | 3,372 | **44.5** | 24.8 | 57.2% | 72.5% |
| Shanghai | 912,572 | 135,903 | **157.7** | 19.8 | 59.8% | 71.5% |
| Chongqing | 518,288 | 64,238 | **409.9** | 57.0 | 33.5% | 64.6% |
| Hangzhou | 1,640,476 | 155,776 | **605.2** | 26.2 | 54.3% | 66.6% |

The large city MAEs come from parcels held for days: LaDe-D has no order time, planned route or traffic, so multi-day holds stay hard to predict. Median errors stay between 20 and 57 minutes. Customers see an arrival window set on September 1 to 15; on September 16 to 30, **80.0%** of arrivals fall inside it (78.0% to 81.9% by city).

Source: [`server/model_store/<city>/metrics.json`](server/model_store); Yantai copy in [`evidence/model/results/metrics.json`](evidence/model/results/metrics.json).

## Data degradation and recovery

Simulated defects on real Yantai and Jilin records, averaged over 3 seeds per city. **Low quality:** a cheap scanner app spreads to 60% of couriers from July to September, bulk-syncing timestamps to the hour, adding ~1 km GPS jitter and re-sending half its records. **Stale:** 60-minute upload delays spread to 60% of couriers over September 16 to 30. Every condition is scored on the same predictions against the original delivery times.

| Condition | No safeguards: MAE (min) | With safeguards: MAE (min) | Damage recovered |
|---|---:|---:|---:|
| Clean | 50.4 | 50.2 | no cost |
| Delayed uploads | 62.2 | 53.4 | **74%** |
| Low-quality records | 71.6 | 60.7 | **51%** |
| Both | 81.1 | 61.0 | **66%** |
| Three monthly retrains on bad records | 73.2 | 65.4 | |
| Unseen fault (timestamps off by up to 30 min) | 61.9 | 55.8 | |
| Lost scans (30% never arrive) | 64.3 | 63.6 | flagged, not repaired |
| Never retrained vs monthly | 56.7 | 50.4 | |

Recovery = `(degraded MAE - repaired MAE) / (degraded MAE - clean MAE)`, calculated before rounding.

- **Validate:** the daily data contract flagged 175 of 184 bad days and 4 of 184 clean days.
- **Clean:** 100% of injected duplicates removed; zero real packages removed.
- **Weigh:** bad-feed records train with a mean weight of 0.11, good records 1.0; nothing is deleted.
- **Correct:** a 20-minute fast device clock is corrected to 2.6 minutes of error.
- **Flag:** 13% of lost-scan predictions are flagged on the day of the miss; 1.7% of genuinely pending parcels are flagged.
- **Monitor:** the drift alarm fired on 94 of 94 bad days; it also fires on clean Jilin days as the city grows.
- **Mechanism:** about 90% of the remaining low-quality damage comes through live inputs, not training. Random training weights do worse than the learned ones.

Source: [`evidence/baddata/results/`](evidence/baddata/results), `results*.json` per city and seed; graphs at [tryhermes.org/results](https://tryhermes.org/results).

## Benchmark audit

M2G4RTP on Yantai, using the LaDe authors' code:

| Evaluation | MAE (min) |
|---|---:|
| Paper-reported | 17.21 |
| Our rerun, authors' scoring | 12.47 |
| Same predictions, matched to each package | 22.19 |

The authors' scoring only covers parcels due within two hours (a filter that needs the future) and matches times by queue position, not by package.

**Fair rerun:** M2G4RTP retrained with the leaks removed, then both models scored on the same 115,983 Yantai predictions (13,701 packages), September 16 to 30.

| Model | MAE per prediction (min) | MAE per package (min) |
|---|---:|---:|
| M2G4RTP, leak-free | 61.7 | 57.7 |
| Hermes | **46.8** | **47.2** |

Hermes has 24% lower error per prediction. Source: [`fair_yt.json`](evidence/leaks/results/fair_yt.json), [`rescore.json`](evidence/leaks/results/rescore.json); checks: [`check.py`](evidence/leaks/check.py).

## Interface

| Benchmarks | Methodology | Data cleaning |
|:---:|:---:|:---:|
| ![Benchmark page](.github/readme/benchmarks.jpg) | ![Methodology page](.github/readme/methodology.jpg) | ![Data cleaning page](.github/readme/data-quality.jpg) |

Screenshots from the deployed website; linked JSON artifacts are the sources for the results above.

## Limits

- Bad-data tests cover Yantai and Jilin only; the fair benchmark rerun covers Yantai only.
- October delivery data is held back and has not been evaluated.
- Repeated predictions for the same package are not independent observations.
- Corruption is simulated; recovery is not a measured production outcome.
- Lost scans are flagged, not repaired.
- Delivery timestamps are courier records, not customer-confirmed arrival times.

## Run locally

Requires Python 3.10+, [uv](https://docs.astral.sh/uv/) and Bun 1.4.2.

```sh
uv sync
uv run python -m server.cli download
uv run python -m server.cli train
(cd app && bun install --frozen-lockfile && bun run build)
uv run uvicorn server.api.app:create_app --factory
# http://localhost:8000 · API docs: /docs
```

```sh
# Checks
uv run ruff check server evidence
uv run python -m unittest discover -s server/tests -t .
(cd app && bun run lint && bun run typecheck && bun test tests)

# Reproduce audit and degradation experiments
uv run python -m evidence.leaks.setup
uv run python -m evidence.leaks.check
uv run python -m evidence.baddata.run
uv run python -m evidence.baddata.report
```

[`server/`](server): models/API · [`app/`](app): React frontend · [`evidence/`](evidence): experiments · [`research.md`](research.md): findings and limits.

**Data:** [LaDe](https://huggingface.co/datasets/Cainiao-AI/LaDe), Cainiao (Wu et al., arXiv:2306.10675). Attribution and non-commercial use apply; raw data is not included.
