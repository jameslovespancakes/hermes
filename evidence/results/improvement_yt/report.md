# Ten additional ETA refinement trials

Target unchanged: **acceptance to delivery**. All valid Yantai cases retained; no random sampling.
Train May-Aug; validation Sep 1-15; deadline calibration Sep 16-30; exploratory October evaluation. Validation has been reused for model search.
Selection was saved to `selection.json` before new calibration/test evaluations. The previous winner was kept as a control and remained eligible.

| Configuration | Validation MAE | October MAE | Within 30 min | Added deadline buffer | By deadline |
|---|---:|---:|---:|---:|---:|
| **10_history_geometry_calendar** | 92.69 | 94.94 | 31.9% | 123.8 min | 87.3% |
| 09_history_recent | 93.25 | 95.43 | 30.7% | 115.9 min | 87.2% |
| 08_history_wider | 93.51 | 96.13 | 30.3% | 122.9 min | 87.5% |
| 05_recent_weighting | 94.03 | 99.95 | 33.0% | 129.1 min | 86.5% |
| 06_geometry_calendar | 94.77 | 100.81 | 32.8% | 128.0 min | 87.3% |
| 07_causal_history | 94.91 | 96.64 | 30.8% | 127.4 min | 87.5% |
| 02_wider_trees | 95.01 | 102.06 | 32.0% | 135.1 min | 87.2% |
| 03_deeper_trees | 95.23 | 103.68 | 32.1% | 130.8 min | 87.1% |
| 01_more_rounds | 95.27 | 100.61 | 32.2% | 136.4 min | 87.1% |
| previous_lightgbm_l1 | 95.35 | 100.40 | 32.0% | 137.4 min | 87.2% |
| 04_strong_regularization | 95.78 | 100.59 | 31.9% | 138.5 min | 87.0% |

Validation-selected: **10_history_geometry_calendar**. October MAE: **100.40 -> 94.94 minutes**, a **5.4%** change in error (positive means improvement).

History features use strictly earlier logged events, not future completions or full-day workload. The model remains frozen while this operational state updates.
Do not pick a different configuration based on its October result. Source benchmark comparisons are discussed in `docs/huggingface_benchmark.md`.

## Selected vs previous: diagnostic slices

| Slice | Model | Cases | MAE | By deadline |
|---|---|---:|---:|---:|
| seen_courier | previous_lightgbm_l1 | 31,857 | 97.66 | 87.0% |
| seen_courier | 10_history_geometry_calendar | 31,857 | 92.98 | 87.7% |
| unseen_courier | previous_lightgbm_l1 | 4,838 | 118.42 | 87.9% |
| unseen_courier | 10_history_geometry_calendar | 4,838 | 107.86 | 84.5% |
| duration_at_most_24_hours | previous_lightgbm_l1 | 36,130 | 89.55 | 87.6% |
| duration_at_most_24_hours | 10_history_geometry_calendar | 36,130 | 87.05 | 87.8% |
| duration_over_24_hours | previous_lightgbm_l1 | 565 | 794.46 | 55.8% |
| duration_over_24_hours | 10_history_geometry_calendar | 565 | 599.17 | 53.5% |

## Uncertainty

```json
{
  "repeats": 1000,
  "day_clusters": 31,
  "mae_minutes_descriptive_95_interval": [
    91.93050946699033,
    97.48944452458532
  ],
  "deadline_on_time_pct_descriptive_95_interval": [
    86.55351907814091,
    88.02983134281794
  ],
  "caveat": "Resampled whole acceptance days, not iid packages; days may be correlated. One seed, city, month, and previously inspected test. Not a deployment or coverage guarantee.",
  "mae_gain_vs_previous_lightgbm_minutes_descriptive_95_interval": [
    4.476951822862,
    6.365362300663087
  ]
}
```

## Limitations

- Same chronological validation/calibration/test partitions are reused from the earlier benchmark. More validation trials can overfit validation; October is exploratory, not a fresh holdout.
- Ten fixed configurations around the previous winner, not an unlimited search. Previous winner remains eligible if all trials are worse.
- No sampled rows or target-based long-duration trimming. All valid October acceptances remain, including multi-day deliveries.
- Known prior completion durations are legitimate historical inputs, not the query package's future outcome; changing the query's future outcome must not change its acceptance-time features.
- History features require real event availability/ingestion timing in a deployment. The source gives event times, not ingestion guarantees or all outstanding tasks.
- Added geometry/calendar features assume the year documented in author code (2022). Prior baseline did not use weekday; target duration and split ordering remain unchanged.
- 90% deadline coverage is a target only. Fixed padding can fail under drift/correlation; longer promises are not automatically better. Calibration only includes outcomes available by Oct 1.
- One city and one seed. No true order-to-receipt labels, injected data degradation, causal attribution, earnings calculation, or deployment validation.
