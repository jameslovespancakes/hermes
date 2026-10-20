# evidence/

Unmodified copies of result files and documents cited by `mockup/assets/research-evidence.json` and by
`research.md`, preserved byte-for-byte when the experiment scripts were removed. Paths mirror their original
locations (e.g. `results/live_eta_baseline/yt/metrics.json` -> `evidence/results/live_eta_baseline/yt/metrics.json`).

- `results/`  metrics JSON from each experiment (live ETA, route models, habits, tuning, Optuna trials,
  TimesFM, fair M2G4RTP comparison, multi-city study).
- `docs/`     earlier write-ups (Hugging Face benchmark audit, industry review, multi-city findings).
- `scripts/live_eta_pipeline.py`  the original consolidated pipeline (provenance only; superseded by `server/`,
  which reproduces its result exactly and no longer depends on the removed helper scripts).
- `lade_reproduction/`  how the LaDe authors' code was run: patch notes, code diff, the cleaning script, runners,
  re-scoring script, their results file, and the re-scoring numbers.
