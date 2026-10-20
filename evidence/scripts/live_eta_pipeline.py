"""Consolidated live-ETA baseline: the best-performing pieces in one reproducible pipeline.

Pieces (each tested in scripts/*_probe.py):
  * live re-prediction after every courier delivery (live_eta_probe)
  * courier habits from previous days: usual area timing and shift pattern (habit_probe)
  * courier area-to-area transition habits, leave-one-day-out for training events (live_transition_probe)
  * learned route-order model, out-of-fold for training events (live_route_probe)
  * LightGBM live ETA using everything above

Split (development data only; October is never loaded):
  fit       events before Sep 1 with outcomes known before Sep 1
  stopping  events Sep 1-15 with outcomes known before Sep 16 (early stopping only)
  test      events Sep 16-30, all outcomes

Outputs: results/live_eta_baseline/<city>/{metrics.json,manifest.json}; models and row-level
predictions under gitignored artifacts/live_eta_baseline/<city>/.
"""

import argparse
import importlib.metadata
import json
import time
from datetime import datetime, timezone

import lightgbm as lgb
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from download_data import ROOT, sha256_file
from habit_probe import habit_features
from live_eta_probe import LIVE_COLS, STATIC_COLS, build_queries, summarize
from live_route_probe import ROUTE_COLS, hit_rates
from multicity_eta import CATS, dump_pickle, encode_for_model, load_pickle
from route_model_probe import spearman_by_moment
from train_baseline import save_json

T = lambda s: pd.Timestamp("2000-" + s)
SEED = 42
TRANSITION_COLS = ["p_courier_next_area", "p_all_next_area", "courier_transition_support", "p_courier_next_area_rank", "p_all_next_area_rank"]
ROUTE_PARAMS = {"objective": "regression", "n_estimators": 500, "learning_rate": 0.05, "num_leaves": 255, "min_child_samples": 50,
                "colsample_bytree": 0.8, "subsample": 0.8, "subsample_freq": 1}
ETA_PARAMS = {"objective": "regression_l1", "n_estimators": 3000, "learning_rate": 0.05, "num_leaves": 255, "min_child_samples": 50,
              "reg_lambda": 5.0, "colsample_bytree": 0.9}
HORIZONS = [("under_30_min", 0, 30), ("30_to_60_min", 30, 60), ("1_to_3_hours", 60, 180), ("3_to_24_hours", 180, 1440), ("over_24_hours", 1440, np.inf)]


def load_dev(city):
    data = load_pickle(ROOT / "artifacts" / "experiments_v2" / "features" / f"{city}.pkl")
    data = data.loc[data["_accepted_at"] < T("10-01")].reset_index(drop=True)
    assert data["_accepted_at"].max() < T("10-01"), "October must not be loaded"
    return pd.concat([data, habit_features(data)], axis=1)


def live_frame(data, city):
    cache = ROOT / "artifacts" / "route_probe" / f"live_queries_{city}.pkl"
    live = load_pickle(cache) if cache.exists() else build_queries(data)
    if not cache.exists():
        dump_pickle(cache, live)
    habit_cols = [c for c in data.columns if c.startswith("hab_")]
    live = pd.concat([live.reset_index(drop=True), data[STATIC_COLS + habit_cols].iloc[live["row"].to_numpy()].reset_index(drop=True)], axis=1)
    rows = live["row"].to_numpy()
    live["_delivered_at"] = data["_delivered_at"].to_numpy()[rows]
    live["courier_s"] = data["courier_id"].astype(str).to_numpy()[rows]
    live["event"] = pd.factorize(live["courier_s"] + "|" + live["s"].astype(str))[0]
    g = live.groupby("event")
    live["true_pos"] = ((g["remaining_min"].rank(method="first") - 1) / (live["n_pending"] - 1).clip(lower=1)).astype("float32")
    live["elapsed_rank"] = (g["elapsed_min"].rank(method="first") - 1) / (live["n_pending"] - 1).clip(lower=1)
    live["day"] = pd.to_datetime(live["s"]).dt.strftime("%m-%d")
    return live, habit_cols


def add_transitions(live, data, cutoff):
    """Courier/all-courier area-to-area probabilities from consecutive same-day deliveries before `cutoff`.
    Events before the cutoff subtract their own courier-day's transitions (leave-one-day-out)."""
    done = pd.DataFrame({"courier_s": data["courier_id"].astype(str).to_numpy(), "s": data["_delivered_at"].to_numpy(),
                         "cur_aoi": data["aoi_id"].astype(str).to_numpy()}).drop_duplicates(["courier_s", "s"])
    live = live.merge(done, on=["courier_s", "s"], how="left")
    d = data.loc[data["_delivered_at"] < cutoff].sort_values(["courier_id", "_delivered_at"])
    prev = d.groupby("courier_id", observed=True).shift()
    same_day = d["_delivered_at"].dt.normalize() == prev["_delivered_at"].dt.normalize()
    tr = pd.DataFrame({"c": d["courier_id"].astype(str), "a": prev["aoi_id"].astype(str), "b": d["aoi_id"].astype(str),
                       "day": d["_delivered_at"].dt.strftime("%m-%d")}).loc[same_day]
    cab, ca = tr.groupby(["c", "a", "b"]).size(), tr.groupby(["c", "a"]).size()
    gab, ga = tr.groupby(["a", "b"]).size(), tr.groupby("a").size()
    own_cab, own_ca = tr.groupby(["c", "day", "a", "b"]).size(), tr.groupby(["c", "day", "a"]).size()
    own_gab, own_ga = own_cab.groupby(level=["day", "a", "b"]).sum(), own_ca.groupby(level=["day", "a"]).sum()
    c, cur, item, day = live["courier_s"], live["cur_aoi"].astype(str), live["aoi_id"].astype(str), live["day"]
    before = (live["s"] < cutoff.to_datetime64()).to_numpy()
    look = lambda s, *keys: s.reindex(pd.MultiIndex.from_arrays(list(keys)) if len(keys) > 1 else pd.Index(keys[0])).fillna(0).to_numpy()
    n_cab = look(cab, c, cur, item) - np.where(before, look(own_cab, c, day, cur, item), 0)
    n_ca = look(ca, c, cur) - np.where(before, look(own_ca, c, day, cur), 0)
    n_gab = look(gab, cur, item) - np.where(before, look(own_gab, day, cur, item), 0)
    n_ga = look(ga, cur) - np.where(before, look(own_ga, day, cur), 0)
    live["p_courier_next_area"] = np.where(n_ca > 0, n_cab / np.maximum(n_ca, 1), np.nan).astype("float32")
    live["p_all_next_area"] = np.where(n_ga > 0, n_gab / np.maximum(n_ga, 1), np.nan).astype("float32")
    live["courier_transition_support"] = n_ca.astype("float32")
    for col in ["p_courier_next_area", "p_all_next_area"]:
        live[col + "_rank"] = (live.groupby("event")[col].rank(method="first", ascending=False) - 1) / (live["n_pending"] - 1).clip(lower=1)
    return live


def add_route_predictions(live, cutoff, threads):
    """Out-of-fold (5 folds by courier-day) for fit-period events; a model trained on all fit events for the rest."""
    cols = ROUTE_COLS + TRANSITION_COLS
    trainable = ((live["s"] < cutoff) & (live.groupby("event")["_delivered_at"].transform("max") < cutoff) & (live["n_pending"] >= 2)).to_numpy()
    grp = pd.factorize(live["courier_s"] + "|" + live["day"])[0]
    fold = np.random.default_rng(SEED).integers(0, 5, grp.max() + 1)[grp]

    def fit(mask):
        model = lgb.LGBMRegressor(**ROUTE_PARAMS, random_state=SEED, n_jobs=threads, verbosity=-1)
        with threadpool_limits(limits=threads):
            model.fit(live.loc[mask, cols], live.loc[mask, "true_pos"])
        return model

    score = np.full(len(live), np.nan)
    for k in range(5):
        score[trainable & (fold == k)] = fit(trainable & (fold != k)).predict(live.loc[trainable & (fold == k), cols])
    full = fit(trainable)
    score[~trainable] = full.predict(live.loc[~trainable, cols])
    live["route_score"] = score
    live["route_ahead"] = (live.groupby("event")["route_score"].rank(method="first") - 1).astype("float32")
    pace = live["pace_today_min"].fillna(live["hab_courier_usual_shift_hours"] * 60 / live["hab_courier_usual_deliveries_per_day"])
    live["route_ahead_x_pace"] = ((live["route_ahead"] + 1) * pace).astype("float32")
    return live, full, cols


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", default="yt")
    parser.add_argument("--threads", type=int, default=16)
    parser.add_argument("--train-cap", type=int, default=800_000)
    args = parser.parse_args()
    started = time.perf_counter()
    out = ROOT / "results" / "live_eta_baseline" / args.city
    art = ROOT / "artifacts" / "live_eta_baseline" / args.city
    out.mkdir(parents=True, exist_ok=True)
    sep1, sep16, oct1 = T("09-01"), T("09-16"), T("10-01")

    data = load_dev(args.city)
    live, habit_cols = live_frame(data, args.city)
    live = add_transitions(live, data, sep1)
    live, route_model, route_cols = add_route_predictions(live, sep1.to_datetime64(), args.threads)
    print(f"features ready: {len(live):,} live queries ({time.perf_counter() - started:.0f}s)", flush=True)

    s = live["s"]
    fit_rows = live.loc[(s < sep1) & (live["_delivered_at"] < sep1)]
    fit_rows = fit_rows.sample(n=min(args.train_cap, len(fit_rows)), random_state=SEED)
    stop_rows = live.loc[(s >= sep1) & (s < sep16) & (live["_delivered_at"] < sep16)]
    test = live.loc[(s >= sep16) & (s < oct1)].copy()
    columns = STATIC_COLS + habit_cols + LIVE_COLS + TRANSITION_COLS + ["route_score", "route_ahead", "route_ahead_x_pace"]
    xfit, schema = encode_for_model(fit_rows, columns)
    xstop, _ = encode_for_model(stop_rows, columns, schema)
    eta_model = lgb.LGBMRegressor(**ETA_PARAMS, random_state=SEED, n_jobs=args.threads, deterministic=True, force_col_wise=True, verbosity=-1)
    with threadpool_limits(limits=args.threads):
        eta_model.fit(xfit, fit_rows["remaining_min"], eval_set=[(xstop, stop_rows["remaining_min"])], eval_metric="l1",
                      categorical_feature=[c for c in CATS if c in columns], callbacks=[lgb.early_stopping(80, verbose=False)])
        test["pred_remaining_min"] = np.maximum(eta_model.predict(encode_for_model(test, columns, schema)[0]), 0)

    actual, pred = test["remaining_min"].to_numpy(), test["pred_remaining_min"].to_numpy()
    h1, h3 = hit_rates(test, "route_score")
    metrics = {"city": args.city, "target": "minutes until delivery, re-predicted after every courier delivery",
               "split": {"fit": f"events < 09-01 with outcomes < 09-01 (sampled to {len(fit_rows):,} rows)",
                         "early_stopping": "events 09-01..09-15 with outcomes < 09-16", "test": "events 09-16..09-30, all outcomes",
                         "october": "not loaded"},
               "rows": {"fit": len(fit_rows), "early_stopping": len(stop_rows), "test": len(test), "test_packages": int(test["row"].nunique())},
               "eta_rounds": int(eta_model.best_iteration_),
               "overall": summarize(actual, {"live_eta": pred})["live_eta"],
               "by_time_remaining": {lab: summarize(actual, {"live_eta": pred}, ((actual > lo) & (actual <= hi)) if lo else (actual <= hi))["live_eta"]
                                     for lab, lo, hi in HORIZONS},
               "route_quality": {"next_stop_pct": h1, "next3_pct": h3,
                                 "order_agreement_spearman": spearman_by_moment(test.assign(moment=test["event"], pp=test["route_score"]), "pp")},
               "seconds": time.perf_counter() - started}
    save_json(out / "metrics.json", metrics)
    dump_pickle(art / "models.pkl", {"route_model": route_model, "route_columns": route_cols, "eta_model": eta_model,
                                     "eta_columns": columns, "eta_schema": schema})
    dump_pickle(art / "test_predictions.pkl", test[["row", "event", "s", "remaining_min", "pred_remaining_min", "route_score", "route_ahead", "n_pending"]])
    importance = pd.Series(eta_model.booster_.feature_importance("gain"), index=columns)
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(), "city": args.city, "seed": SEED,
                "route_params": ROUTE_PARAMS, "eta_params": ETA_PARAMS, "eta_columns": columns, "route_columns": route_cols,
                "top_eta_features_by_gain_share": (importance / importance.sum()).sort_values(ascending=False).head(15).round(4).to_dict(),
                "source_manifest_sha256": sha256_file(ROOT / "data" / f"manifest_{args.city}.json"),
                "code_sha256": {p: sha256_file(ROOT / "scripts" / p) for p in ["live_eta_pipeline.py", "live_eta_probe.py", "habit_probe.py", "live_route_probe.py"]},
                "versions": {p: importlib.metadata.version(p) for p in ["lightgbm", "numpy", "pandas"]}}
    save_json(out / "manifest.json", manifest)
    print(json.dumps({"overall_mae": round(metrics["overall"]["mae"], 2), "median_ae": round(metrics["overall"]["median_ae"], 1),
                      "by_time_remaining_mae": {k: round(v["mae"], 1) for k, v in metrics["by_time_remaining"].items()},
                      "route": {k: round(v, 3) for k, v in metrics["route_quality"].items()}}, indent=1))


if __name__ == "__main__":
    main()
