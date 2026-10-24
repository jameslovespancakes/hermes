"""Bad-data experiment: stale and low-quality feeds vs the live ETA server, with and without its safeguards.

    uv run python -m evidence.baddata.run [--city yt] [--smoke] [--reuse]     # ~1.5 h for Yantai (smoke: 20 couriers); then report.py

SIMULATED degradation on real city data (Yantai by default; labelled as such):
  * low-quality scanner app: 0% -> 60% of couriers, Jul 1 -> Sep 30 (bulk-synced times, ~1 km GPS jitter, half of
    records re-sent); monthly retraining on Jul 1 / Aug 1 / Sep 1 learns from worse and worse records;
  * delayed uploads (60 min): 0% -> 60% of couriers across the Sep 16-30 test window.
Every system is trained by server.pipeline.train.train_bundle and scored by server.serving.predictor.LiveETAPredictor,
so this tests exactly the code that serves. Scoring always uses TRUE delivery times on the same real packages and
true checkpoint moments for every condition.
"""

import argparse
import json
import pickle
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from evidence.baddata.corrupt import Rollout, TimestampFault, fast_clocks, lost_scans, low_quality_feed, sync_delay
from evidence.baddata.score import (
    FrozenHabits,
    contract_summary,
    daily,
    daily_drift,
    drift_summary,
    evaluate,
    guard_quality,
    label_corruption,
    mechanism,
    missed_detection,
    summary,
)
from server.config import Split, ts
from server.data.loading import load_city
from server.models.bundle import ModelBundle
from server.pipeline.features import checkpoints
from server.pipeline.train import train_bundle
from server.quality.config import QUALITY, CleanMode
from server.quality.contract import city_bounds, daily_report
from server.quality.gating import audited_gate

HERE = Path(__file__).resolve().parent
RESULTS, ARTIFACTS = HERE / "results", HERE / "artifacts"
CITY, SMOKE_COURIERS = "yt", 20
LQ_ROLLOUT = Rollout(ts("07-01"), ts("09-30"), 0.6)
STALE_ROLLOUT = Rollout(ts("09-16"), ts("09-30"), 0.6)
STALE_LAG_MINUTES = 60
CUTOFFS = [ts("07-01"), ts("08-01"), ts("09-01")]
LAST = CUTOFFS[-1]
STOP_DAYS = 15
TEST = (ts("09-16"), ts("10-01"))

# Systems, keyed by training track: (records it learns from, safeguards it carries)
TRACKS = {"clean": ("clean", False), "lq_raw": ("lq", False), "lq_guarded": ("lq", True), "clean_guarded": ("clean", True)}
SEVERITY = (0.2, 0.4)  # low-quality adoption shares tested besides the main 0.6 (last cutoff only)
LAST_ONLY = {"clean_guarded"} | {f"lq{int(s * 100)}_{kind}" for s in SEVERITY for kind in ("raw", "guarded")}
SEED_OFFSET = 0  # --seed: every simulated defect draws from seeds shifted by 100 x this
CORE = False  # --core: four conditions and the new faults only (repeat seeds)


@dataclass(frozen=True)
class Condition:
    """One required condition: the naive pipeline vs the protected pipeline, each with the view it receives.
    Views ending in _pt store arrival time as delivery time (naive); _et keep scanner time + receive time."""

    name: str
    naive: str
    naive_view: str
    protected: str
    protected_view: str


CONDITIONS = [
    Condition("reference", "clean", "clean", "clean_guarded", "clean"),
    Condition("stale_only", "clean", "stale_pt", "clean_guarded", "stale_et"),
    Condition("low_quality_only", "lq_raw", "lq", "lq_guarded", "lq"),
    Condition("combined", "lq_raw", "combined_pt", "lq_guarded", "combined_et"),
]

DESIGN = {
    "lq_rollout": "0% -> 60% of couriers, Jul 1 -> Sep 30 (bulk sync to the hour, ~1 km GPS jitter, 50% re-sent)",
    "stale_rollout": f"0% -> 60% of couriers, Sep 16 -> Sep 30, uploads {STALE_LAG_MINUTES} min late",
    "retraining": "monthly: Jul 1, Aug 1, Sep 1 (fit before cutoff, early-stop next 15 days, test rest of month)",
    "countermeasure": (
        "data contract + DataGuard (dedupe, GPS repair, bulk-scan quarantine, review flags) + event-time processing "
        "with upload-lag monitoring + staleness-aware model when a feed is stale + PSI drift monitoring + gated "
        "retraining on a 10% audited sample"
    ),
    "code_path": "systems trained by server.pipeline.train.train_bundle and scored by server.serving.predictor.LiveETAPredictor",
    "scoring": "true delivery times; same real packages and true checkpoint moments for every condition",
}


STARTED = time.perf_counter()


def log(message: str) -> None:
    print(f"[{(time.perf_counter() - STARTED) / 60:5.1f} min] {message}", flush=True)


def key(track: str, cutoff: pd.Timestamp) -> str:
    return f"{track}@{cutoff:%m-%d}"


def split_for(cutoff: pd.Timestamp) -> Split:
    return Split(fit_end=f"{cutoff:%m-%d}", stop_end=f"{cutoff + pd.Timedelta(days=STOP_DAYS):%m-%d}")


def month_window(cutoff: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp]:
    return cutoff + pd.Timedelta(days=STOP_DAYS), cutoff + pd.offsets.MonthBegin(1)


def build_views(clean: pd.DataFrame) -> dict[str, pd.DataFrame]:
    o = 100 * SEED_OFFSET
    lq = low_quality_feed(clean, LQ_ROLLOUT, seed=11 + o)
    views = {
        "clean": clean,
        "lq": lq,
        "lq_noise": low_quality_feed(clean, LQ_ROLLOUT, seed=11 + o, fault=TimestampFault.NOISE),
        "stale_pt": sync_delay(clean, STALE_ROLLOUT, STALE_LAG_MINUTES, seed=23 + o),
        "stale_et": sync_delay(clean, STALE_ROLLOUT, STALE_LAG_MINUTES, seed=23 + o, event_time=True),
        "combined_pt": sync_delay(lq, STALE_ROLLOUT, STALE_LAG_MINUTES, seed=23 + o),
        "combined_et": sync_delay(lq, STALE_ROLLOUT, STALE_LAG_MINUTES, seed=23 + o, event_time=True),
        "lost": lost_scans(clean, STALE_ROLLOUT, seed=41 + o),
        "clock": fast_clocks(clean, STALE_ROLLOUT, seed=53 + o),
    }
    for share in SEVERITY:
        views[f"lq{int(share * 100)}"] = low_quality_feed(clean, Rollout(LQ_ROLLOUT.start, LQ_ROLLOUT.end, share), seed=11 + o)
    return views


def cutoffs_for(track: str) -> list[pd.Timestamp]:
    """Which monthly systems a track trains; a --core run keeps only what the four conditions and new faults need."""
    if CORE:
        return {"clean": [CUTOFFS[0], LAST], "lq_raw": [LAST], "lq_guarded": [LAST], "clean_guarded": [LAST]}.get(track, [])
    return [LAST] if track in LAST_ONLY else CUTOFFS


def train_systems(views: dict, clean: pd.DataFrame, truth: pd.Series) -> dict[str, ModelBundle]:
    """Monthly systems per track; the protected tracks get the staleness-aware model at the last cutoff."""
    systems = {}
    tracks = TRACKS | {f"lq{int(s * 100)}_{kind}": (f"lq{int(s * 100)}", kind == "guarded") for s in SEVERITY for kind in ("raw", "guarded")}
    for track, (view, guarded) in tracks.items():
        for cutoff in cutoffs_for(track):
            split, full = split_for(cutoff), guarded and cutoff == LAST
            events = checkpoints(clean, CITY, clean["delivered_at"].min(), split.stop_cutoff) if full else None
            name = key(track, cutoff)
            systems[name] = train_bundle(
                views[view],
                CITY,
                split,
                use_guard=guarded,
                use_staleness=full,
                staleness_events=events,
                truth=truth,
                log=lambda message, n=name: log(f"{n}: {message}"),
            )
    return systems


def guard_only(bundle: ModelBundle) -> ModelBundle:
    return replace(bundle, staleness=None)


def staleness_always_on(bundle: ModelBundle) -> ModelBundle:
    return replace(bundle, eta=bundle.staleness, staleness=None)


def monthly(systems, views, truth, clean, baseline) -> tuple[dict, list]:
    results, drift = {}, []
    for cutoff in CUTOFFS:
        events = checkpoints(clean, CITY, *month_window(cutoff))
        month = {}
        for label, track, view in (("reference", "clean", "clean"), ("bad_data_no_fix", "lq_raw", "lq"), ("bad_data_with_guard", "lq_guarded", "lq")):
            rows = evaluate(guard_only(systems[key(track, cutoff)]), views[view], truth, events)
            month[label] = summary(rows)
            if label != "bad_data_with_guard":
                drift.append(daily_drift(baseline, rows, "clean" if label == "reference" else "low_quality"))
        start, end = month_window(cutoff)
        month["lq_feed_share_at_test_pct"] = float(LQ_ROLLOUT.share(pd.Series([start + (end - start) / 2]))[0] * 100)
        results[f"{cutoff:%m-%d}"] = month
        log(f"monthly {cutoff:%m-%d}: " + ", ".join(f"{k} {v['mae']:.1f}" for k, v in month.items() if isinstance(v, dict)))
    return results, drift


def gated(systems, track, view, truth, clean) -> list[dict]:
    """A retrained model replaces the deployed one only if it wins on audited deliveries known at decision time."""
    deployed, history = None, []
    for cutoff in CUTOFFS:
        challenger, decision, gate_end = key(track, cutoff), None, cutoff + pd.Timedelta(days=STOP_DAYS)
        if deployed is None:
            deployed = challenger
        else:
            events = checkpoints(clean, CITY, cutoff, gate_end)
            decision = audited_gate(
                evaluate(guard_only(systems[deployed]), view, truth, events),
                evaluate(guard_only(systems[challenger]), view, truth, events),
                truth,
                gate_end,
            )
            deployed = challenger if decision.promote else deployed
        rows = evaluate(guard_only(systems[deployed]), view, truth, checkpoints(clean, CITY, *month_window(cutoff)))
        history.append(
            {
                "cutoff": f"{cutoff:%m-%d}",
                "deployed": deployed,
                "test_mae": summary(rows)["mae"],
                "gate": None if decision is None else decision.__dict__,
            }
        )
    log(f"gated {track}: " + ", ".join(f"{h['cutoff']} {h['deployed']} {h['test_mae']:.1f}" for h in history))
    return history


def four_conditions(systems, views, truth, clean, baseline) -> tuple[dict, dict, list, list]:
    events = checkpoints(clean, CITY, *TEST)
    results, mechanisms, daily_frames, drift = {}, {}, [], []
    reference = None
    for c in CONDITIONS:
        naive, protected = systems[key(c.naive, LAST)], systems[key(c.protected, LAST)]
        entry = {}
        for label, bundle, view in (("no_fix", naive, c.naive_view), ("with_fix", protected, c.protected_view)):
            rows = evaluate(bundle, views[view], truth, events)
            entry[label] = summary(rows)
            daily_frames.append(daily(rows, f"{c.name}|{label}"))
            if label == "no_fix" and c.name == "reference":
                reference = rows
            elif label == "no_fix":
                mechanisms[c.name] = mechanism(reference, rows)
                drift.append(daily_drift(baseline, rows, c.name))
        if c.naive_view != c.protected_view:
            entry["event_time_processing_only"] = summary(evaluate(naive, views[c.protected_view], truth, events))
        if c.protected == "lq_guarded":
            entry["guard_only"] = summary(evaluate(guard_only(protected), views[c.protected_view], truth, events))
        if c.name == "stale_only":
            entry["staleness_model_always_on"] = summary(evaluate(staleness_always_on(protected), views[c.protected_view], truth, events))
        results[c.name] = entry
        log(f"{c.name}: no fix {entry['no_fix']['mae']:.2f} | with fix {entry['with_fix']['mae']:.2f}")
    return results, mechanisms, daily_frames, drift


def new_faults(systems, views, truth, clean) -> dict:
    """The faults added after the first study: each against the same test checkpoints, without and with the fix."""
    events = checkpoints(clean, CITY, *TEST)
    plain, guarded = systems[key("clean", LAST)], systems[key("clean_guarded", LAST)]
    lost = {"no_fix": evaluate(plain, views["lost"], truth, events), "with_fix": evaluate(guarded, views["lost"], truth, events)}
    out = {
        "never_retrained": {
            "no_fix": summary(evaluate(systems[key("clean", CUTOFFS[0])], views["clean"], truth, events)),
            "with_fix": summary(evaluate(plain, views["clean"], truth, events)),
            "description": "model trained to Jul 1 and never retrained, vs retrained monthly (Sep 1)",
        },
        "frozen_habits": {
            "no_fix": summary(evaluate(plain, views["clean"], truth, events, predictor=FrozenHabits)),
            "with_fix": summary(evaluate(plain, views["clean"], truth, events)),
            "description": "courier and area habits stop updating on Jul 1 (a failed nightly job), vs rebuilt from the log at every prediction",
        },
        "fast_clocks": {
            "no_fix": summary(evaluate(plain, views["clock"], truth, events)),
            "with_fix": summary(evaluate(guarded, views["clock"], truth, events)),
            "description": "device clocks 20 min fast on up to 60% of couriers over the test window; receive times true",
        },
        "lost_scans": {label: summary(rows) for label, rows in lost.items()} | {"detection": missed_detection(guarded, views["lost"], events)},
    }
    out["lost_scans"]["description"] = (
        "30% of delivery scans never arrive from up to 60% of couriers over the test window; the fix flags, it does not correct"
    )
    for name, entry in out.items():
        log(f"{name}: no fix {entry['no_fix']['mae']:.2f} | with fix {entry['with_fix']['mae']:.2f}")
    log(f"lost-scan detection: {out['lost_scans']['detection']}")
    return out


def severity(systems, views, truth, clean) -> list[dict]:
    """Damage and recovery as the low-quality feed reaches 20%, 40% and 60% of couriers."""
    events = checkpoints(clean, CITY, *TEST)
    out = []
    for share, view, raw, guarded in [(s, f"lq{int(s * 100)}", f"lq{int(s * 100)}_raw", f"lq{int(s * 100)}_guarded") for s in SEVERITY] + [
        (0.6, "lq", "lq_raw", "lq_guarded")
    ]:
        out.append(
            {
                "share": share,
                "no_fix": summary(evaluate(systems[key(raw, LAST)], views[view], truth, events))["mae"],
                "with_fix": summary(evaluate(systems[key(guarded, LAST)], views[view], truth, events))["mae"],
            }
        )
        log(f"severity {share:.0%}: no fix {out[-1]['no_fix']:.2f} | with fix {out[-1]['with_fix']:.2f}")
    return out


def random_weights(systems, views, truth, clean) -> dict:
    """Control: the guard's down-weighting given to random courier-days instead (same weights, shuffled)."""
    guarded = systems[key("lq_guarded", LAST)]
    cleaned, _ = guarded.guard.clean(views["lq"], CleanMode.TRAIN)
    day = cleaned["courier_id"].astype(str) + "|" + cleaned["delivered_at"].dt.strftime("%m-%d")
    weights = cleaned.groupby(day)["weight"].first()
    shuffled = pd.Series(np.random.default_rng(7 + SEED_OFFSET).permutation(weights.to_numpy()), index=weights.index)
    cleaned["weight"] = day.map(shuffled).fillna(1.0).to_numpy()
    control = train_bundle(cleaned, CITY, split_for(LAST), use_guard=False, use_staleness=False, truth=truth, log=lambda m: None)
    control = replace(control, guard=guarded.guard)
    events = checkpoints(clean, CITY, *TEST)
    out = {
        "guard_weights": summary(evaluate(guard_only(guarded), views["lq"], truth, events))["mae"],
        "random_weights": summary(evaluate(control, views["lq"], truth, events))["mae"],
    }
    log(f"random-weight control: guard {out['guard_weights']:.2f} | random {out['random_weights']:.2f}")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help=f"{SMOKE_COURIERS} couriers, fast end-to-end check")
    parser.add_argument("--reuse", action="store_true", help="load trained systems from artifacts/ instead of training")
    parser.add_argument("--city", default="yt", help="a city whose history starts by May (yt, jl)")
    parser.add_argument("--seed", type=int, default=0, help="shift every simulated defect's random draws (repeat runs)")
    parser.add_argument("--core", action="store_true", help="four conditions and the new faults only (for repeat seeds)")
    args = parser.parse_args()
    global CITY, SEED_OFFSET, CORE
    CITY, SEED_OFFSET, CORE = args.city, args.seed, args.core
    suffix = ("" if CITY == "yt" else f"_{CITY}") + (f"_seed{SEED_OFFSET}" if SEED_OFFSET else "") + ("_smoke" if args.smoke else "")
    RESULTS.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    clean, _ = load_city(CITY, accepted_before=TEST[1])
    if args.smoke:
        chosen = clean["courier_id"].drop_duplicates().sample(SMOKE_COURIERS, random_state=0)
        clean = clean.loc[clean["courier_id"].isin(chosen)].reset_index(drop=True)
    truth = clean.set_index("order_id")["delivered_at"]
    views = build_views(clean)
    bounds = city_bounds(clean.loc[clean["accepted_at"] < CUTOFFS[0]])
    contracts = {
        label: daily_report(views[v].loc[(views[v]["delivered_at"] >= CUTOFFS[0]) & (views[v]["delivered_at"] < TEST[1])], bounds)
        for label, v in (("clean", "clean"), ("low_quality", "lq"))
    }
    log("views ready; data contract evaluated")

    store = ARTIFACTS / f"systems{suffix}.pkl"
    if args.reuse and store.exists():
        systems = pickle.loads(store.read_bytes())
    else:
        systems = train_systems(views, clean, truth)
        store.write_bytes(pickle.dumps(systems, protocol=pickle.HIGHEST_PROTOCOL))
    baseline = systems[key("clean", CUTOFFS[0])].monitor

    results = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "smoke": args.smoke,
        "design": DESIGN,
        "quality_config": QUALITY.__dict__,
        "guard_detection_quality": guard_quality(views["lq"], systems[key("lq_guarded", LAST)].guard),
        "training_label_corruption": label_corruption(views["lq"], truth, CITY, LAST),
        "data_contract": {label: contract_summary(report) for label, report in contracts.items()},
        "drift_thresholds": baseline.drift_thresholds,
    }
    drift = []
    if not CORE:
        results["monthly"], drift = monthly(systems, views, truth, clean, baseline)
        results["gated_retraining"] = {track: gated(systems, track, views["lq"], truth, clean) for track in ("lq_raw", "lq_guarded")}
        results["severity"] = severity(systems, views, truth, clean)
        results["random_weight_control"] = random_weights(systems, views, truth, clean)
    results["new_faults"] = new_faults(systems, views, truth, clean)
    results["four_conditions"], results["mechanism"], daily_frames, more_drift = four_conditions(systems, views, truth, clean, baseline)
    events = checkpoints(clean, CITY, *TEST)
    results["unseen_degradation"] = {
        label: summary(evaluate(systems[key(track, LAST)], views["lq_noise"], truth, events))
        for label, track in (("no_fix", "lq_raw"), ("with_fix", "lq_guarded"))
    }
    results["unseen_degradation"]["description"] = "timestamps randomly off by +/-30 min instead of bulk-synced: detectors not designed for it"
    drift_table = pd.concat(drift + more_drift, ignore_index=True)
    results["drift"] = drift_summary(drift_table)
    results["seconds"] = time.perf_counter() - STARTED

    (RESULTS / f"results{suffix}.json").write_text(json.dumps(results, indent=2, default=str) + "\n", encoding="utf-8")
    pd.concat(daily_frames, ignore_index=True).to_csv(RESULTS / f"daily{suffix}.csv", index=False)
    drift_table.to_csv(RESULTS / f"drift_daily{suffix}.csv", index=False)
    pd.concat([r.assign(feed=label) for label, r in contracts.items()]).to_csv(RESULTS / f"contract_daily{suffix}.csv", index=False)
    log(f"saved to {RESULTS}")


if __name__ == "__main__":
    main()
