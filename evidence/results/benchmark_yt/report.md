# Ten-model acceptance-to-delivery benchmark

**Target:** minutes from courier task acceptance to recorded delivery completion. Not order-to-receipt or physical-pickup-to-delivery time.
**Scope:** Yantai LaDe-D only. All valid labeled cases retained, including zero and multi-day durations.
**Status:** exploratory October evaluation; this month had already been inspected in the original baseline.

## Chronology

| Partition | Acceptance dates | Rows | Days |
|---|---|---:|---:|
| train | 05-01 07:34:00 to 08-31 22:13:00 | 135,872 | 123 |
| tune | 09-01 07:43:00 to 09-15 20:35:00 | 18,009 | 15 |
| calibration | 09-16 07:42:00 to 09-30 23:27:00 | 15,798 | 15 |
| test | 10-01 07:54:00 to 10-31 20:19:00 | 36,695 | 31 |

May-Aug fits models and preprocessing; Sep 1-15 selects boosting rounds and the point-model winner; Sep 16-30 calibrates deadlines only. No refit after calibration.
Outcome-availability exclusions: `{"train_outcomes_unavailable_at_sep_01": 24, "validation_outcomes_unavailable_at_oct_01": 25, "outside_acceptance_window": 0, "additional_tune_outcomes_unavailable_at_sep_16": 8}`.

## All ten models / structures

Point ETA and deliver-by deadline are different outputs. A 90%-target deadline adds a fixed per-model buffer learned only from calibration residuals; it is NOT a promise of 90% coverage on future operations.

| Model | Tune MAE (min) | Oct MAE (min) | Within 30 min | By point ETA | Added buffer (min) | By deadline | Mean deadline duration (min) |
|---|---:|---:|---:|---:|---:|---:|---:|
| **lightgbm_l1** | 95.35 | 100.40 | 32.0% | 50.3% | 137.4 | 87.2% | 385.8 |
| hist_gradient_boosting | 97.84 | 102.74 | 29.7% | 49.7% | 145.6 | 86.8% | 387.3 |
| lightgbm_log_target | 98.34 | 102.22 | 30.4% | 48.3% | 156.5 | 87.2% | 393.1 |
| lightgbm_no_courier_aoi_ids | 100.90 | 103.26 | 30.5% | 49.2% | 157.1 | 87.8% | 398.1 |
| random_forest | 103.85 | 108.86 | 22.4% | 58.9% | 131.5 | 87.2% | 399.1 |
| decision_tree | 117.51 | 120.23 | 19.9% | 57.6% | 156.8 | 87.6% | 423.9 |
| extra_trees | 120.15 | 121.36 | 18.5% | 57.0% | 163.0 | 87.4% | 428.2 |
| ridge | 121.64 | 121.44 | 19.1% | 55.8% | 166.3 | 88.2% | 431.8 |
| region_hour_median | 135.27 | 131.69 | 17.5% | 49.5% | 229.0 | 88.6% | 463.9 |
| global_median | 160.73 | 159.27 | 14.3% | 50.4% | 270.0 | 88.9% | 478.0 |

Selected using **tuning MAE only**: `lightgbm_l1`. Do not pick a different winner merely because its October score is better.
Its October point MAE is **100.40 minutes**. Calibrated deadline on-time rate: **87.15%**; **4,714** deliveries late.
The deadline adds **137.4 minutes** to the point ETA. Longer promises can improve on-time rate without improving point predictions; mean unused promise time is **140.4 minutes**.

## Selected-model diagnostic slices

| October slice | Cases | MAE (min) | By deadline | Mean promised duration (min) |
|---|---:|---:|---:|---:|
| seen_courier | 31,857 | 97.66 | 87.0% | 385.1 |
| unseen_courier | 4,838 | 118.42 | 87.9% | 390.5 |
| duration_at_most_24_hours | 36,130 | 89.55 | 87.6% | 365.0 |
| duration_over_24_hours | 565 | 794.46 | 55.8% | 1719.7 |
| missing_accept_gps | 299 | 117.00 | 96.3% | 504.0 |

Outcome-based duration slices are diagnostics only, not features or pre-decision filters.

## Uncertainty

```json
{
  "repeats": 1000,
  "day_clusters": 31,
  "mae_minutes_descriptive_95_interval": [
    97.21822683460434,
    103.38616596781611
  ],
  "mae_gain_vs_region_hour_minutes_descriptive_95_interval": [
    29.334447876897816,
    33.28251504626299
  ],
  "deadline_on_time_pct_descriptive_95_interval": [
    86.47455225992687,
    87.89949563276241
  ],
  "caveat": "Resampled whole acceptance days, not iid packages; days may be correlated. One seed, city, month, and previously inspected test. Not a deployment or coverage guarantee."
}
```

## Caveats

- Acceptance time is not customer order time or verified physical pickup time. No upstream-order wait modeled.
- Ten structures include two simple baselines and three LightGBM variants, not ten independent algorithm families. Fixed bounded configs, not exhaustive tuning.
- Models have different loss functions and categorical representations; relative performance includes these choices. May-Aug training cases are identical.
- Serial dependence and drift invalidate an unconditional conformal guarantee; 90% is a target, not a guarantee per customer, courier, or subgroup.
- Calibration uses completed September tasks available by Oct 1; unfinished long tasks are excluded and can bias tail estimates downward. October retains all supplied October-accepted outcomes.
- October was already inspected and is reused only for exploratory comparison; a fresh holdout is needed for confirmatory performance claims.
- Larger deadline buffers raise on-time rate by relaxing the promise, not necessarily by improving predictions. Track duration, unused slack, and lateness together.
- Recorded completion is not independently audited customer receipt. Source lacks vehicle type, explicit waiting durations, live traffic, route sequence, and full workload.
- Courier IDs recur across dates; actual route IDs are unavailable. Same-day courier packages are correlated. No causal conclusion from feature ablation alone.
- One city and one training seed; no poisoning injection/countermeasure, deployment validation, human workload study, or earnings estimate.
- Timing measures local CPU wall time only, not human review effort. Source data and model/prediction artifacts remain local pending rights review.

Detailed settings, versions, timing, per-model scores, and lineage: `metrics.json`. Per-week and region metrics: `metrics_by_week.csv` and `metrics_by_region.csv`. Local row-level outputs are gitignored.
