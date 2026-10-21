"""Render results.json + daily.csv into REPORT.md (uv run python -m evidence.baddata.report [--smoke])."""

import argparse
import json
from pathlib import Path

import pandas as pd

RESULTS = Path(__file__).resolve().parent / "results"


def _f(value, digits: int = 1, suffix: str = "") -> str:
    return "-" if value is None else f"{value:.{digits}f}{suffix}"


def _name(key: str) -> str:
    return key.replace("_", " ")


def _conditions(results: dict) -> list[str]:
    four = results["four_conditions"]
    ref = four["reference"]["no_fix"]["mae"]
    lines = ["## 1. The four required conditions, with and without the full fix (average error, minutes)", "",
             "| Condition | No fix | With fix | Damage from bad data: no fix -> with fix | Damage recovered |", "|---|---:|---:|---:|---:|"]
    for name, entry in four.items():
        nf, wf = entry["no_fix"]["mae"], entry["with_fix"]["mae"]
        recovered = (nf - wf) / (nf - ref) * 100 if nf - ref > 0.5 else None
        lines.append(f"| {_name(name)} | {nf:.1f} | {wf:.1f} | {nf - ref:+.1f} -> {wf - ref:+.1f} | {_f(recovered, 0, '%')} |")
    lines += ["", "What each layer contributes (ablations, same test cases):", ""]
    for name, entry in four.items():
        for key in ("event_time_processing_only", "guard_only", "staleness_model_always_on"):
            if key in entry:
                lines.append(f"- {_name(name)}: {_name(key)} {entry[key]['mae']:.1f} (no fix {entry['no_fix']['mae']:.1f}, "
                             f"full fix {entry['with_fix']['mae']:.1f})")
    lines += ["", "Affected couriers only:", "", "| Condition | Share of predictions affected | No fix | With fix |", "|---|---:|---:|---:|"]
    for name, entry in four.items():
        nf, wf = entry["no_fix"], entry["with_fix"]
        if "mae_affected_couriers" in nf:
            lines.append(f"| {_name(name)} | {_f(nf.get('affected_share_pct'), 1, '%')} | {_f(nf['mae_affected_couriers'])} | "
                         f"{_f(wf.get('mae_affected_couriers'))} |")
    return lines


def _timeline(results: dict) -> list[str]:
    lines = ["", "## 2. Over time: monthly retraining on progressively worse records", "",
             "| Retrained on | Bad-feed share at test | Clean reference | Bad data, no fix | Bad data, guard |", "|---|---:|---:|---:|---:|"]
    for cutoff, m in results["monthly"].items():
        lines.append(f"| {cutoff} | {m['lq_feed_share_at_test_pct']:.0f}% | {m['reference']['mae']:.1f} | {m['bad_data_no_fix']['mae']:.1f} | "
                     f"{m['bad_data_with_guard']['mae']:.1f} |")
    lines += ["", "Gated retraining (champion vs challenger on a 10% audited sample; the deployed model is scored on the test weeks):", "",
              "| Track | Cutoff | Gate decision (champion vs challenger, audited MAE) | Deployed | Test MAE gated | Test MAE always-retrain |",
              "|---|---|---|---|---:|---:|"]
    always = {"lq_raw": "bad_data_no_fix", "lq_guarded": "bad_data_with_guard"}
    for track, history in results["gated_retraining"].items():
        for h in history:
            g = h["gate"]
            if g is None:
                decision = "first model"
            else:
                verdict = "promote" if g["promote"] else "keep champion"
                decision = f"{verdict} ({g['champion_mae']:.1f} vs {g['challenger_mae']:.1f})"
            lines.append(f"| {track} | {h['cutoff']} | {decision} | {h['deployed']} | {h['test_mae']:.1f} | "
                         f"{results['monthly'][h['cutoff']][always[track]]['mae']:.1f} |")
    return lines


def _daily(daily: pd.DataFrame) -> list[str]:
    lines = ["", "## 3. Day by day in the test window (delayed uploads ramp 0% -> 60%)", "",
             "| Day | Clean | Stale, no fix | Stale, fix | Combined, no fix | Combined, fix |", "|---|---:|---:|---:|---:|---:|"]
    pivot = daily.pivot_table(index="day", columns="system", values="mae")
    for day in pivot.index:
        row = pivot.loc[day]
        keys = ("reference|no_fix", "stale_only|no_fix", "stale_only|with_fix", "combined|no_fix", "combined|with_fix")
        cells = [row.get(k, float("nan")) for k in keys]
        lines.append(f"| {day} | " + " | ".join(f"{c:.1f}" for c in cells) + " |")
    return lines


def _mechanism_and_guard(results: dict) -> list[str]:
    lines = ["", "## 4. Mechanism: what bad data changed (same package, same moment)", "",
             "| Condition | Error clean -> degraded | Packages-held change | Route position changed | Feed-age change (min) |",
             "|---|---:|---:|---:|---:|"]
    for name, m in results["mechanism"].items():
        lines.append(f"| {_name(name)} | {m['mae_reference']:.1f} -> {m['mae_degraded']:.1f} | {m['mean_abs_change_n_pending']:.2f} | "
                     f"{m['route_position_changed_pct']:.0f}% | {m['mean_abs_change_feed_age_min']:.0f} |")
    q, lab = results["guard_detection_quality"], results.get("training_label_corruption", {})
    lines += ["", "## 5. Guard detection quality (against the simulation's ground truth)", "",
              f"- Injected re-sent records removed: {_f(q['duplicates_found_pct_of_injected'], 1, '%')}; real packages wrongly removed: "
              f"{q['real_packages_wrongly_removed_as_duplicates']}",
              f"- Bad-feed records quarantined: {_f(q['bad_feed_records_quarantined_pct'], 1, '%')}; good records quarantined: "
              f"{_f(q['good_records_quarantined_pct'], 2, '%')}",
              f"- Bad-feed coordinates repaired: {_f(q['bad_feed_coordinates_repaired_pct'], 1, '%')}; good coordinates changed: "
              f"{_f(q['good_coordinates_repaired_pct'], 2, '%')}",
              f"- Naive training labels: {_f(lab.get('mean_abs_label_error_min'))} min average error; "
              f"{_f(lab.get('training_rows_from_fake_duplicates_pct'), 2, '%')} of training rows were injected copies"]
    return lines


def _monitoring(results: dict) -> list[str]:
    c = results["data_contract"]
    lines = ["", "## 6. Early warning: data contract and drift monitoring", "",
             "| Monitor | Clean feed | Low-quality feed |", "|---|---|---|",
             f"| Data contract: days failed | {c['clean']['days_failed']} of {c['clean']['days']} | {c['low_quality']['days_failed']} of "
             f"{c['low_quality']['days']} (first {c['low_quality']['first_failed_day']}) |",
             f"| Most common contract failure | - | {c['low_quality']['most_common_failure']} |"]
    drift = results["drift"]
    lines += ["", "| Drift series (daily PSI vs training inputs) | Days 'act' (>0.25) | Days 'watch' | First 'act' day | Most drifted input |",
              "|---|---:|---:|---|---|"]
    for series, d in drift.items():
        lines.append(f"| {_name(series)} | {d['days_act']} of {d['days']} | {d['days_watch']} | {d['first_act_day'] or '-'} | "
                     f"{d['most_drifted_feature']} |")
    return lines


def _limits(results: dict) -> list[str]:
    four, u = results["four_conditions"], results["unseen_degradation"]
    ref = four["reference"]["no_fix"]["mae"]
    lines = ["", "## 7. Limit: a degradation the guard was not designed for", "",
             f"{u['description']}: no fix {u['no_fix']['mae']:.1f} min, with fix {u['with_fix']['mae']:.1f} min (clean {ref:.1f}).", "",
             "## 8. Human oversight", ""]
    for name, entry in four.items():
        wf = entry["with_fix"]
        if "flagged_for_review_pct" in wf:
            lines.append(f"- {_name(name)}: {wf['flagged_for_review_pct']:.1f}% of predictions flagged for a dispatcher; error flagged "
                         f"{_f(wf.get('mae_flagged'))} vs not flagged {_f(wf.get('mae_not_flagged'))} min; staleness-aware model used for "
                         f"{_f(wf.get('staleness_model_pct'), 1, '%')} of predictions")
    return lines


def render(results: dict, daily: pd.DataFrame) -> str:
    lines = ["# Bad-data experiment: stale and low-quality data vs the live ETA model, and industry-standard safeguards", "",
             "**Simulated progression** on real Yantai courier data (LaDe-D). Always scored against true delivery times, on the",
             "same real packages at the same true checkpoint moments for every condition.", "", "## Setup", ""]
    lines += [f"- **{_name(k).capitalize()}:** {v}" for k, v in results["design"].items()]
    for section in (_conditions(results), _timeline(results), _daily(daily), _mechanism_and_guard(results), _monitoring(results), _limits(results)):
        lines += section
    lines += ["", f"_Generated from results.json ({results['created_utc'][:19]} UTC, {results['seconds'] / 60:.0f} min run"
              f"{', SMOKE: 20 couriers' if results.get('smoke') else ''})._", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    suffix = "_smoke" if parser.parse_args().smoke else ""
    results = json.loads((RESULTS / f"results{suffix}.json").read_text(encoding="utf-8"))
    daily = pd.read_csv(RESULTS / f"daily{suffix}.csv", dtype={"day": str})
    (RESULTS / f"REPORT{suffix}.md").write_text(render(results, daily), encoding="utf-8")
    print(f"wrote {RESULTS / f'REPORT{suffix}.md'}")


if __name__ == "__main__":
    main()
