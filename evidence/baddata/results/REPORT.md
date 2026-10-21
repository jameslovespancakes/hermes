# Bad-data experiment: stale and low-quality data vs the live ETA model, and industry-standard safeguards

**Simulated progression** on real Yantai courier data (LaDe-D). Always scored against true delivery times, on the
same real packages at the same true checkpoint moments for every condition.

## Setup

- **Lq rollout:** 0% -> 60% of couriers, Jul 1 -> Sep 30 (bulk sync to the hour, ~1 km GPS jitter, 50% re-sent)
- **Stale rollout:** 0% -> 60% of couriers, Sep 16 -> Sep 30, uploads 60 min late
- **Retraining:** monthly: Jul 1, Aug 1, Sep 1 (fit before cutoff, early-stop next 15 days, test rest of month)
- **Countermeasure:** data contract + DataGuard (dedupe, GPS repair, bulk-scan quarantine, review flags) + event-time processing with upload-lag monitoring + staleness-aware model when a feed is stale + PSI drift monitoring + gated retraining on a 10% audited sample
- **Code path:** systems trained by server.pipeline.train.train_bundle and scored by server.serving.predictor.LiveETAPredictor
- **Scoring:** true delivery times; same real packages and true checkpoint moments for every condition
## 1. The four required conditions, with and without the full fix (average error, minutes)

| Condition | No fix | With fix | Damage from bad data: no fix -> with fix | Damage recovered |
|---|---:|---:|---:|---:|
| reference | 58.5 | 58.5 | +0.0 -> +0.0 | - |
| stale only | 63.3 | 60.0 | +4.9 -> +1.6 | 68% |
| low quality only | 80.1 | 66.7 | +21.6 -> +8.2 | 62% |
| combined | 84.0 | 66.9 | +25.5 -> +8.4 | 67% |

What each layer contributes (ablations, same test cases):

- stale only: event time processing only 63.2 (no fix 63.3, full fix 60.0)
- stale only: staleness model always on 60.2 (no fix 63.3, full fix 60.0)
- low quality only: guard only 69.8 (no fix 80.1, full fix 66.7)
- combined: event time processing only 83.8 (no fix 84.0, full fix 66.9)
- combined: guard only 72.8 (no fix 84.0, full fix 66.9)

Affected couriers only:

| Condition | Share of predictions affected | No fix | With fix |
|---|---:|---:|---:|
| stale only | 18.4% | 90.5 | 72.3 |
| low quality only | 69.8% | 88.7 | 69.4 |
| combined | 72.6% | 94.9 | 71.2 |

## 2. Over time: monthly retraining on progressively worse records

| Retrained on | Bad-feed share at test | Clean reference | Bad data, no fix | Bad data, guard |
|---|---:|---:|---:|---:|
| 07-01 | 15% | 59.4 | 68.3 | 62.8 |
| 08-01 | 36% | 61.2 | 73.5 | 67.2 |
| 09-01 | 56% | 58.5 | 80.1 | 69.8 |

Gated retraining (champion vs challenger on a 10% audited sample; the deployed model is scored on the test weeks):

| Track | Cutoff | Gate decision (champion vs challenger, audited MAE) | Deployed | Test MAE gated | Test MAE always-retrain |
|---|---|---|---|---:|---:|
| lq_raw | 07-01 | first model | lq_raw@07-01 | 68.3 | 68.3 |
| lq_raw | 08-01 | promote (72.5 vs 67.5) | lq_raw@08-01 | 73.5 | 73.5 |
| lq_raw | 09-01 | promote (78.4 vs 75.3) | lq_raw@09-01 | 80.1 | 80.1 |
| lq_guarded | 07-01 | first model | lq_guarded@07-01 | 62.8 | 62.8 |
| lq_guarded | 08-01 | promote (65.9 vs 63.8) | lq_guarded@08-01 | 67.2 | 67.2 |
| lq_guarded | 09-01 | promote (70.7 vs 69.7) | lq_guarded@09-01 | 69.8 | 69.8 |

## 3. Day by day in the test window (delayed uploads ramp 0% -> 60%)

| Day | Clean | Stale, no fix | Stale, fix | Combined, no fix | Combined, fix |
|---|---:|---:|---:|---:|---:|
| 09-16 | 52.9 | 53.0 | 53.4 | 71.4 | 60.0 |
| 09-17 | 53.4 | 53.4 | 53.7 | 71.9 | 60.2 |
| 09-18 | 57.2 | 57.2 | 57.0 | 81.0 | 65.1 |
| 09-19 | 59.4 | 60.5 | 59.3 | 79.4 | 68.0 |
| 09-20 | 55.0 | 59.9 | 56.7 | 78.3 | 64.5 |
| 09-21 | 54.7 | 60.4 | 56.7 | 80.5 | 65.0 |
| 09-22 | 52.6 | 57.0 | 53.7 | 74.8 | 58.9 |
| 09-23 | 85.3 | 90.7 | 87.2 | 109.2 | 92.3 |
| 09-24 | 58.1 | 64.3 | 59.3 | 87.0 | 65.6 |
| 09-25 | 54.6 | 61.7 | 56.2 | 82.8 | 62.3 |
| 09-26 | 61.6 | 65.2 | 62.1 | 87.7 | 70.7 |
| 09-27 | 59.9 | 65.3 | 61.7 | 88.3 | 68.8 |
| 09-28 | 57.7 | 65.5 | 59.5 | 91.0 | 67.3 |
| 09-29 | 55.7 | 63.7 | 59.7 | 81.0 | 63.2 |
| 09-30 | 55.7 | 68.9 | 61.1 | 91.1 | 68.5 |

## 4. Mechanism: what bad data changed (same package, same moment)

| Condition | Error clean -> degraded | Packages-held change | Route position changed | Feed-age change (min) |
|---|---:|---:|---:|---:|
| stale only | 58.5 -> 63.3 | 0.72 | 17% | 78 |
| low quality only | 58.5 -> 80.1 | 8.13 | 79% | 237 |
| combined | 58.5 -> 84.0 | 8.84 | 81% | 294 |

## 5. Guard detection quality (against the simulation's ground truth)

- Injected re-sent records removed: 100.0%; real packages wrongly removed: 0
- Bad-feed records quarantined: 97.4%; good records quarantined: 0.03%
- Bad-feed coordinates repaired: 32.2%; good coordinates changed: 0.31%
- Naive training labels: 1.5 min average error; 2.44% of training rows were injected copies

## 6. Early warning: data contract and drift monitoring

| Monitor | Clean feed | Low-quality feed |
|---|---|---|
| Data contract: days failed | 0 of 92 | 88 of 92 (first 07-05) |
| Most common contract failure | - | courier timestamps not repeated |

| Drift series (daily PSI vs training inputs) | Days 'act' (>0.25) | Days 'watch' | First 'act' day | Most drifted input |
|---|---:|---:|---|---|
| clean | 3 of 47 | 17 | 07-19 | pace_today_min |
| combined | 15 of 15 | 0 | 09-16 | feed_age_min |
| low quality | 47 of 47 | 0 | 07-16 | feed_age_min |
| low quality only | 15 of 15 | 0 | 09-16 | feed_age_min |
| stale only | 11 of 15 | 2 | 09-20 | feed_age_min |

## 7. Limit: a degradation the guard was not designed for

timestamps randomly off by +/-30 min instead of bulk-synced: detectors not designed for it: no fix 69.7 min, with fix 62.7 min (clean 58.5).

## 8. Human oversight

- reference: 0.0% of predictions flagged for a dispatcher; error flagged - vs not flagged 58.5 min; staleness-aware model used for 0.0% of predictions
- stale only: 17.4% of predictions flagged for a dispatcher; error flagged 63.8 vs not flagged 59.2 min; staleness-aware model used for 17.4% of predictions
- low quality only: 13.2% of predictions flagged for a dispatcher; error flagged 68.1 vs not flagged 66.4 min; staleness-aware model used for 35.1% of predictions
- combined: 27.5% of predictions flagged for a dispatcher; error flagged 67.8 vs not flagged 66.5 min; staleness-aware model used for 44.7% of predictions

_Generated from results.json (2026-10-21T04:29:38 UTC, 136 min run)._
