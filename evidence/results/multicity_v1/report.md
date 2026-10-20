# Multi-city acceptance-to-delivery study

Validation-selected policy: **local_context**. Selection metric: equal-weight mean city MAE, not a volume-dominated aggregate.
Models train on May-Aug; tune Sep 1-15; deadlines calibrate Sep 16-30; evaluate October. Jilin never participates in fitting, tuning, or calibration.

## Data budget

| City | Raw rows | Fitting rows | Validation | Calibration | Test |
|---|---:|---:|---:|---:|---:|
| Yantai | 206,431 | 135,872 | 18,009 | 15,798 | 36,695 |
| Shanghai | 1,483,864 | 250,016 | 168,100 | 158,605 | 376,329 |
| Hangzhou | 1,861,600 | 250,023 | 175,746 | 172,770 | 398,606 |
| Chongqing | 931,351 | 250,008 | 64,026 | 73,975 | 277,456 |
| Jilin | 31,415 | 0 | 0 | 0 | 1,089 |

Only fitting data is sampled, as complete courier/day groups. Evaluation is unsampled. Historical features use all strictly prior logged events.

## Validation selection

| Policy | Mean city validation MAE (min) |
|---|---:|
| local_context | 101.86 |
| blend_context_50_50 | 102.01 |
| pooled_context | 103.64 |
| pooled_base | 104.64 |
| city_median | 136.46 |

## Selected policy: October results

| City | Status | MAE (min) | Within 30 min | By city-calibrated deadline | Mean promise (min) |
|---|---|---:|---:|---:|---:|
| Yantai | reused | 95.24 | 31.5% | 87.3% | 385.6 |
| Shanghai | new_city_time_test | 57.18 | 52.2% | 89.1% | 168.4 |
| Hangzhou | new_city_time_test | 90.03 | 37.3% | 89.0% | 255.3 |
| Chongqing | new_city_time_test | 214.35 | 24.1% | 88.3% | 466.7 |
| Jilin | geographic_holdout | 145.96 | 18.1% | 60.4% | 281.9 |

## Policy comparison on the three new known-city October tests

| Policy | Mean city MAE | Worst city MAE | Mean city deadline coverage |
|---|---:|---:|---:|
| city_median | 139.24 | 238.50 | 89.3% |
| pooled_base | 123.34 | 216.96 | 88.8% |
| pooled_context | 120.47 | 213.09 | 88.9% |
| local_context | 120.52 | 214.35 | 88.8% |
| blend_context_50_50 | 119.81 | 212.73 | 88.9% |

## Deadline calibration diagnostics (selected policy)

City-level calibration was chosen before testing; region/pooled scores are diagnostics, not post-test model choices.

| City | Pooled buffer coverage | City buffer coverage | Region buffer coverage |
|---|---:|---:|---:|
| Yantai | 87.2% | 87.3% | 86.7% |
| Shanghai | 93.1% | 89.1% | 88.9% |
| Hangzhou | 89.3% | 89.0% | 88.5% |
| Chongqing | 79.5% | 88.3% | 89.0% |
| Jilin | 60.4% | 60.4% | 60.4% |

## Uncertainty

```json
{
  "error_macro_city_95_interval": [
    117.87176468321705,
    123.30328373587479
  ],
  "gain_vs_pooled_base_macro_city_95_interval": [
    2.608885204982523,
    3.035739132846455
  ],
  "on_time_macro_city_95_interval": [
    88.48430544238857,
    89.12879319857787
  ],
  "cities": [
    "sh",
    "hz",
    "cq"
  ],
  "calendar_days": 31,
  "repeats": 1000,
  "caveat": "Descriptive whole-day bootstrap with jointly sampled calendar days; serial dependence, one seed, and geographic selection limit inference."
}
```

## Limitations

- Fitting uses a bounded whole-courier-day training sample; all eligible validation/calibration/test rows are evaluated. Historical event features use the complete prior log.
- Yantai October was previously inspected. Three other known-city October tests were first evaluated here; Jilin is held out from fitting, tuning, and calibration.
- Jilin transfer still uses strictly prior local operational history as input. It is not a no-history cold-start guarantee. Local and blended policies fall back to pooled_context there.
- Four ID/type fields are scoped by city to avoid accidental namespace collisions. Held-out city IDs become missing for native categorical model inputs.
- A frozen model sees updated causal event history. Missing/uncompleted tasks and real ingestion delays are not fully represented by this completed-task dataset.
- 90% deadline coverage is a target, not a guarantee. City is the preselected primary buffer method; pooled/region versions are diagnostics, not test-selected winners.
- Calibration includes only outcomes known before Oct 1; delayed outcomes near cutoffs can bias tail estimates downward. All supplied October-accepted outcomes remain in testing.
- One seed and one six-month source. Macro-city metrics prevent larger cities dominating the headline, but do not guarantee performance for each small region or outside these five cities.
- Calendar assumes 2022 from the author README. Coordinates are privacy-perturbed; no inferred real identities, live road traffic, vehicle types, future routes, or actual earnings.
- No poisoning injection/countermeasure or deployment validation. All data/model/prediction artifacts remain local; dataset licensing conflict remains unresolved for redistribution.

Full per-policy/city scores: `city_results.csv` and `metrics.json`. Subgroups: `metrics_by_region.csv`, `metrics_by_week.csv`. Local row-level outputs and model bundles live under gitignored `artifacts/multicity_v1/`.
