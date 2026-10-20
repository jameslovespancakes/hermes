# Running the LaDe authors' time-prediction code locally

Source: https://github.com/wenhaomin/LaDe at commit `9e5155a5e03b0e752749f726914f73bf08d62666`.
The repository has **no license file**: kept local and gitignored (`external/`), not redistributed.
Security review: no network access, shell execution, or file deletion; pickles/checkpoints are only
files the code itself writes under its own `data/` and `output/` folders.

## A. Environment/bug fixes (needed for the published code to run at all) — `LADE_environment_fixes.diff`
| File | Change | Why |
|---|---|---|
| utils/util.py | `CUDA_VISIBLE_DEVICES="4"` -> default `"0"` | hard-coded 5th GPU; this machine has one |
| utils/util.py | optional `nni` import (no-op stub) | NNI tuning service not needed for plain runs |
| utils/util.py | training loop accepts `(predictions, loss)` from `process_batch` | M2G4RTP returns a tuple; loop crashed |
| m2g4rtp_delivery/m2g4rtp.py, train.py | imports `m2g4rtp_pickup.*` -> `m2g4rtp_delivery.*`; `gat_encoder.py` copied from route_prediction | module path did not exist in time_prediction |
| m2g4rtp_delivery/train.py (test_model) | edge tensor size 4 -> actual feature count (3) | evaluation crashed; training uses 3 |
| rankepta/*, run.py, utils/util.py | `algorithm.ranketpa` -> `algorithm.rankepta` | folder is named `rankepta` |
| (deps) | geohash2 replaced by a tested standard encoder; other deps installed into `external/_deps` | geohash2 wheel fails to build |
| run settings | `workers=0`; M2G4RTP batch 16 (paper states 32; code default 64) | Windows data loading; 12 GB GPU spills at 32/64 |

Published code could not have produced its reported results as released (evaluation crashed, imports
pointed at missing modules); the authors presumably ran a different version.

## B. Cleaned pipeline (`make_clean_lade.py` -> `data/*_clean.py`, dataset `delivery_yt_clean`)
1. Courier statistics from training dates only (were computed over all dates incl. test).
2. Area statistics (avg time per package, area-to-area travel time) from training dates only.
3. M2G4RTP area features no longer walk pending packages in the TRUE future delivery order (run lengths,
   truncation at first revisit); unique pending areas ordered by distance from the courier, with counts.
4. Busy test courier-days no longer discarded (task skipped as in training).
Unchanged (their task definition): a pending package is a query only if it finishes 0-120 min later, and at
most 25 tasks. This still uses future outcomes to choose inputs, so even "clean" numbers are not
comparable to a forward-looking system; our own live pipeline scores the unfiltered task.
