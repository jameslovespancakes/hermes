# Bad-data experiment: stale and low-quality data vs the live ETA model, and industry-standard safeguards

**Simulated progression** on real Yantai courier data (LaDe-D). Always scored against true delivery times, on the
same real packages at the same true checkpoint moments for every condition.

## Setup

- **Lq rollout:** 0% -> 60% of couriers, Jul 1 -> Sep 30 (bulk sync to the hour, ~1 km GPS jitter, 50% re-sent)
- **Stale rollout:** 0% -> 60% of couriers, Sep 16 -> Sep 30, uploads 60 min late
- **Retraining:** monthly: Jul 1, Aug 1, Sep 1 (fit before cutoff, early-stop next 15 days, test rest of month)
- **Countermeasure:** data contract + DataGuard (dedupe, GPS repair, bulk-scan quarantine, review flags) + event-time processing with upload-lag monitoring + staleness-aware model when a feed is stale + PSI drift monitoring + gated retraining on a 10% audited sample
- **Scoring:** true delivery times; same real packages and true checkpoint moments for every condition
## 1. The four required conditions, with and without the full fix (average error, minutes)

| Condition | No fix | With fix | Damage from bad data: no fix -> with fix | Damage recovered |
|---|---:|---:|---:|---:|
| reference | 58.7 | 58.5 | +0.0 -> -0.2 | - |
| stale only | 63.6 | 59.9 | +4.9 -> +1.2 | 75% |
| low quality only | 79.7 | 65.6 | +21.1 -> +6.9 | 67% |
| combined | 83.6 | 66.0 | +24.9 -> +7.4 | 70% |

What each layer contributes (ablations, same test cases):

- stale only: event time processing only 63.4 (no fix 63.6, full fix 59.9)
- stale only: staleness model always on 60.2 (no fix 63.6, full fix 59.9)
- low quality only: guard only 69.8 (no fix 79.7, full fix 65.6)
- combined: event time processing only 83.5 (no fix 83.6, full fix 66.0)
- combined: guard only 72.9 (no fix 83.6, full fix 66.0)

Affected couriers only:

| Condition | Share of predictions affected | No fix | With fix |
|---|---:|---:|---:|
| stale only | 18.4% | 91.0 | 71.6 |
| low quality only | 69.8% | 88.2 | 67.9 |
| combined | 72.6% | 94.3 | 70.1 |

## 2. Over time: monthly retraining on progressively worse records

| Retrained on | Bad-feed share at test | Clean reference | Bad data, no fix | Bad data, guard |
|---|---:|---:|---:|---:|
| 07-01 | 15% | 59.5 | 68.1 | 63.2 |
| 08-01 | 36% | 61.2 | 73.5 | 67.4 |
| 09-01 | 56% | 58.7 | 79.7 | 69.8 |

Gated retraining (champion vs challenger on a 10% audited sample; the deployed model is scored on the test weeks):

| Track | Cutoff | Gate decision (champion vs challenger, audited MAE) | Deployed | Test MAE gated | Test MAE always-retrain |
|---|---|---|---|---:|---:|
| lq_raw | 07-01 | first model | lq_raw@07-01 | 68.1 | 68.1 |
| lq_raw | 08-01 | promote (71.9 vs 67.5) | lq_raw@08-01 | 73.5 | 73.5 |
| lq_raw | 09-01 | promote (78.4 vs 74.6) | lq_raw@09-01 | 79.7 | 79.7 |
| lq_guarded | 07-01 | first model | lq_guarded@07-01 | 63.2 | 63.2 |
| lq_guarded | 08-01 | promote (66.1 vs 63.6) | lq_guarded@08-01 | 67.4 | 67.4 |
| lq_guarded | 09-01 | promote (70.9 vs 69.1) | lq_guarded@09-01 | 69.8 | 69.8 |

## 3. Day by day in the test window (delayed uploads ramp 0% -> 60%)

| Day | Clean | Stale, no fix | Stale, fix | Combined, no fix | Combined, fix |
|---|---:|---:|---:|---:|---:|
| 09-16 | 53.4 | 53.4 | 53.4 | 70.8 | 58.7 |
| 09-17 | 53.9 | 53.9 | 53.7 | 71.6 | 58.8 |
| 09-18 | 57.3 | 57.3 | 57.0 | 80.3 | 63.4 |
| 09-19 | 59.4 | 60.5 | 59.1 | 79.8 | 67.3 |
| 09-20 | 55.1 | 59.9 | 56.7 | 77.7 | 63.4 |
| 09-21 | 54.8 | 60.5 | 56.7 | 80.0 | 63.9 |
| 09-22 | 52.4 | 56.8 | 53.7 | 75.0 | 58.1 |
| 09-23 | 85.6 | 90.9 | 86.6 | 109.0 | 91.8 |
| 09-24 | 58.4 | 64.9 | 59.3 | 86.3 | 65.7 |
| 09-25 | 54.8 | 62.0 | 56.2 | 82.4 | 62.5 |
| 09-26 | 61.5 | 65.1 | 62.2 | 86.8 | 70.4 |
| 09-27 | 60.4 | 65.6 | 61.6 | 87.9 | 67.7 |
| 09-28 | 57.7 | 65.3 | 59.3 | 90.6 | 66.4 |
| 09-29 | 56.0 | 64.3 | 59.1 | 80.7 | 62.3 |
| 09-30 | 56.4 | 69.9 | 60.8 | 90.5 | 67.8 |

## 4. Mechanism: what bad data changed (same package, same moment)

| Condition | Error clean -> degraded | Packages-held change | Route position changed | Feed-age change (min) |
|---|---:|---:|---:|---:|
| stale only | 58.7 -> 63.6 | 0.72 | 17% | 78 |
| low quality only | 58.7 -> 79.7 | 8.13 | 79% | 237 |
| combined | 58.7 -> 83.6 | 8.84 | 81% | 294 |

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

timestamps randomly off by +/-30 min instead of bulk-synced: detectors not designed for it: no fix 69.6 min, with fix 62.7 min (clean 58.7).

## 8. Human oversight

- reference: 0.0% of predictions flagged for a dispatcher; error flagged - vs not flagged 58.5 min
- stale only: 18.3% of predictions flagged for a dispatcher; error flagged 64.7 vs not flagged 58.8 min
- low quality only: 26.9% of predictions flagged for a dispatcher; error flagged 72.2 vs not flagged 63.2 min
- combined: 39.0% of predictions flagged for a dispatcher; error flagged 71.0 vs not flagged 62.9 min

_Generated from results.json (2026-10-20T23:28:58 UTC, 21 min run)._
