# What the LaDe Hugging Face scores actually measure

Checked 2026-10-17. Dataset-card revision: `be2cec02775cafc8d52230303f32134382bcc50b`. Author-code commit inspected: `9e5155a5e03b0e752749f726914f73bf08d62666`. This is a documentation/code audit, **not** a reproduction of the authors' experiments.

## Reported numbers

The [Hugging Face card, section 4.2](https://huggingface.co/datasets/Cainiao-AI/LaDe/blob/be2cec02775cafc8d52230303f32134382bcc50b/README.md) identifies its leaderboard as **Shanghai**:

| Method | Reported MAE (minutes) | Reported ACC@30 |
|---|---:|---:|
| LightGBM | 30.99 | 0.59 |
| SPEED | 23.75 | 0.73 |
| KNN | 36.00 | 0.58 |
| MLP | 21.54 +/- 2.20 | 0.79 +/- 0.04 |
| FDNET | **18.47 +/- 0.25** | **0.84 +/- 0.01** |

**ACC@30 is error within 30 minutes of the actual arrival**, not the fraction arriving before a promised deadline. Do not compare it to our 90%-target deadline coverage.

The [v3 paper, Table 4](https://arxiv.org/html/2306.10675v3) has a different/expanded table with **ACC@20**. Selected entries:

| Method | Shanghai MAE | Yantai MAE |
|---|---:|---:|
| LightGBM | 17.24 | 23.32 |
| FDNET | 18.81 | 22.41 |
| RankETPA | 15.76 | 21.36 |
| M2G4RTP | **8.23** | **17.21** |

These are the numbers printed in those sources, not interchangeable versions of one verified local experiment. The source card and paper are not fully synchronized.

## Why our scores are not directly comparable

| Aspect | Our task | Published definition / inspected author code |
|---|---|---|
| Prediction time | Immediately when a package task is accepted | ETA query at time `t` during a route; current code uses completed-stop checkpoints |
| Target | Full acceptance-to-completion duration | Remaining time from query/checkpoint to completion for unfinished tasks |
| Evaluation population | All valid October-accepted Yantai deliveries, including multi-day outcomes | Constructed route/query examples with task/trajectory filters; current default remaining-time label range is `(0, 120]` minutes |
| Context | Initial parcel/courier/location features; new refinement adds strictly prior logged workload/history | Current route node, unfinished tasks, completed-node history, spatial relationships |
| Split | Train May-Aug; tune Sep 1-15; calibrate Sep 16-30; test October | Paper describes chronological 60/20/20; code splits on completion-date groups |
| Unit | One prediction per accepted package | Multiple route checkpoints can query unfinished tasks; not one row per original parcel |
| Deadline | Separate residual-calibrated deliver-by upper bound | Accuracy-tolerance metrics, not our deadline policy |

The code's 120-minute limit is a **remaining-time** filter, not evidence that original acceptance-to-delivery durations were at most two hours. An exact reproduction would require matching the archived data preparation, versions, settings, query construction, and metric aggregation. Current code defaults do not prove which options produced every historical card entry.

### Code evidence

- [`time_prediction/data/dataset_delivery.py`](https://github.com/wenhaomin/LaDe/blob/9e5155a5e03b0e752749f726914f73bf08d62666/time_prediction/data/dataset_delivery.py):
  - `get_features()` iterates route finish-time steps.
  - It computes candidate `time_label = finish_time(task) - finish_time(start)` and filters against `label_range`.
  - `current_time` is the completed start node's finish time.
  - `V_at`/returned `time_label` represent remaining task time from that checkpoint.
  - Defaults include `label_range=(0,120)`, `len_range=(1,25)`, `T=12`, and date ratios 0.6/0.2/0.2.
- [`time_prediction/data/preprocess_delivery.py`](https://github.com/wenhaomin/LaDe/blob/9e5155a5e03b0e752749f726914f73bf08d62666/time_prediction/data/preprocess_delivery.py): creates courier/day trajectories, prior-stop intervals, distances, and courier/AOI aggregates; filters some GPS/duplicate-stop cases.
- [`time_prediction/utils/eval.py`](https://github.com/wenhaomin/LaDe/blob/9e5155a5e03b0e752749f726914f73bf08d62666/time_prediction/utils/eval.py): `acc_eta()` checks absolute error within a tolerance. RMSE is computed per query and then aggregated, unlike our single global package-level RMSE.
- [`readme.md`](https://github.com/wenhaomin/LaDe/blob/9e5155a5e03b0e752749f726914f73bf08d62666/readme.md), section 3, states the collection dates as **2022-05-01 through 2022-10-31**. Our initial baseline omitted weekday because the CSV itself has no year. The new calendar-feature trials use this explicit source-year assumption.

### Reproduction cautions

- The Hugging Face KNN row prints MAE 36.00 and RMSE 31.89. With the same cases and consistent weighting, RMSE cannot be smaller than MAE. Treat this as an unresolved table/definition inconsistency, not an independently verified result.
- At the inspected commit, [`time_prediction/algorithm/lgb/train.py`](https://github.com/wenhaomin/LaDe/blob/9e5155a5e03b0e752749f726914f73bf08d62666/time_prediction/algorithm/lgb/train.py) actually instantiates `MultiOutputRegressor(xgb.XGBRegressor(...))`, despite its `lgb` path. Do not assume running this current file reproduces the card's historical LightGBM entry.
- The preprocessing entry point builds some courier/AOI aggregates before the later split. We did not copy those aggregates into our operational experiment; any reproduction should audit information availability rather than blindly adopt the code.

## What we adopted, and what we did not

The useful idea is **operational context**, not just choosing a different model: how many tasks a courier already has, what has already been completed, and where the courier last completed a stop.

Our follow-up adds only information known strictly before each task's acceptance. The current task's future outcome, future acceptances/completions, full-day totals, and actual future route sequence are excluded. The work-log is still an incomplete proxy and assumes source event timestamps correspond to information availability.

We **did not** move the prediction time later, discard targets above two hours, join pickup data, or change October evaluation cases to make our number resemble the leaderboard. Reproducing the authors' route-checkpoint benchmark would be a separate task and should be labeled separately.
