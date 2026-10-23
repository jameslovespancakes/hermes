"""Render results.json + daily.csv into REPORT.md (uv run python -m evidence.baddata.report [--smoke]), and with
--figures the line graphs of the site's results page
(uv run --with matplotlib --with fonttools --with brotli python -m evidence.baddata.report --figures)."""

import argparse
import json
from pathlib import Path

import pandas as pd

RESULTS = Path(__file__).resolve().parent / "results"
ROOT = Path(__file__).resolve().parents[2]
FIGURES = ROOT / "app" / "public" / "assets" / "results"
CITIES = {"yt": "Yantai", "jl": "Jilin", "sh": "Shanghai", "cq": "Chongqing", "hz": "Hangzhou"}


def _f(value, digits: int = 1, suffix: str = "") -> str:
    return "-" if value is None else f"{value:.{digits}f}{suffix}"


def _name(key: str) -> str:
    return key.replace("_", " ")


def _conditions(results: dict) -> list[str]:
    four = results["four_conditions"]
    ref = four["reference"]["no_fix"]["mae"]
    lines = [
        "## 1. The four required conditions, with and without the full fix (average error, minutes)",
        "",
        "| Condition | No fix | With fix | Damage from bad data: no fix -> with fix | Damage recovered |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, entry in four.items():
        nf, wf = entry["no_fix"]["mae"], entry["with_fix"]["mae"]
        recovered = (nf - wf) / (nf - ref) * 100 if nf - ref > 0.5 else None
        lines.append(f"| {_name(name)} | {nf:.1f} | {wf:.1f} | {nf - ref:+.1f} -> {wf - ref:+.1f} | {_f(recovered, 0, '%')} |")
    lines += ["", "What each layer contributes (ablations, same test cases):", ""]
    for name, entry in four.items():
        for key in ("event_time_processing_only", "guard_only", "staleness_model_always_on"):
            if key in entry:
                lines.append(
                    f"- {_name(name)}: {_name(key)} {entry[key]['mae']:.1f} (no fix {entry['no_fix']['mae']:.1f}, "
                    f"full fix {entry['with_fix']['mae']:.1f})"
                )
    lines += ["", "Affected couriers only:", "", "| Condition | Share of predictions affected | No fix | With fix |", "|---|---:|---:|---:|"]
    for name, entry in four.items():
        nf, wf = entry["no_fix"], entry["with_fix"]
        if "mae_affected_couriers" in nf:
            lines.append(
                f"| {_name(name)} | {_f(nf.get('affected_share_pct'), 1, '%')} | {_f(nf['mae_affected_couriers'])} | "
                f"{_f(wf.get('mae_affected_couriers'))} |"
            )
    return lines


def _timeline(results: dict) -> list[str]:
    lines = [
        "",
        "## 2. Over time: monthly retraining on progressively worse records",
        "",
        "| Retrained on | Bad-feed share at test | Clean reference | Bad data, no fix | Bad data, guard |",
        "|---|---:|---:|---:|---:|",
    ]
    for cutoff, m in results["monthly"].items():
        lines.append(
            f"| {cutoff} | {m['lq_feed_share_at_test_pct']:.0f}% | {m['reference']['mae']:.1f} | {m['bad_data_no_fix']['mae']:.1f} | "
            f"{m['bad_data_with_guard']['mae']:.1f} |"
        )
    lines += [
        "",
        "Gated retraining (champion vs challenger on a 10% audited sample; the deployed model is scored on the test weeks):",
        "",
        "| Track | Cutoff | Gate decision (champion vs challenger, audited MAE) | Deployed | Test MAE gated | Test MAE always-retrain |",
        "|---|---|---|---|---:|---:|",
    ]
    always = {"lq_raw": "bad_data_no_fix", "lq_guarded": "bad_data_with_guard"}
    for track, history in results["gated_retraining"].items():
        for h in history:
            g = h["gate"]
            if g is None:
                decision = "first model"
            else:
                verdict = "promote" if g["promote"] else "keep champion"
                decision = f"{verdict} ({g['champion_mae']:.1f} vs {g['challenger_mae']:.1f})"
            lines.append(
                f"| {track} | {h['cutoff']} | {decision} | {h['deployed']} | {h['test_mae']:.1f} | "
                f"{results['monthly'][h['cutoff']][always[track]]['mae']:.1f} |"
            )
    return lines


def _daily(daily: pd.DataFrame) -> list[str]:
    lines = [
        "",
        "## 3. Day by day in the test window (delayed uploads ramp 0% -> 60%)",
        "",
        "| Day | Clean | Stale, no fix | Stale, fix | Combined, no fix | Combined, fix |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    pivot = daily.pivot_table(index="day", columns="system", values="mae")
    for day in pivot.index:
        row = pivot.loc[day]
        keys = ("reference|no_fix", "stale_only|no_fix", "stale_only|with_fix", "combined|no_fix", "combined|with_fix")
        cells = [row.get(k, float("nan")) for k in keys]
        lines.append(f"| {day} | " + " | ".join(f"{c:.1f}" for c in cells) + " |")
    return lines


def _mechanism_and_guard(results: dict) -> list[str]:
    lines = [
        "",
        "## 4. Mechanism: what bad data changed (same package, same moment)",
        "",
        "| Condition | Error clean -> degraded | Packages-held change | Route position changed | Feed-age change (min) |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, m in results["mechanism"].items():
        lines.append(
            f"| {_name(name)} | {m['mae_reference']:.1f} -> {m['mae_degraded']:.1f} | {m['mean_abs_change_n_pending']:.2f} | "
            f"{m['route_position_changed_pct']:.0f}% | {m['mean_abs_change_feed_age_min']:.0f} |"
        )
    q, lab = results["guard_detection_quality"], results.get("training_label_corruption", {})
    lines += [
        "",
        "## 5. Guard detection quality (against the simulation's ground truth)",
        "",
        f"- Injected re-sent records removed: {_f(q['duplicates_found_pct_of_injected'], 1, '%')}; real packages wrongly removed: "
        f"{q['real_packages_wrongly_removed_as_duplicates']}",
        f"- Bad-feed records flagged: {_f(q['bad_feed_records_flagged_pct'], 1, '%')} (mean weight {_f(q['bad_feed_mean_weight'], 2, '')}); "
        f"good records flagged: {_f(q['good_records_flagged_pct'], 2, '%')} (mean weight {_f(q['good_mean_weight'], 2, '')})",
        f"- Bad-feed coordinates repaired: {_f(q['bad_feed_coordinates_repaired_pct'], 1, '%')}; good coordinates changed: "
        f"{_f(q['good_coordinates_repaired_pct'], 2, '%')}",
        f"- Naive training labels: {_f(lab.get('mean_abs_label_error_min'))} min average error; "
        f"{_f(lab.get('training_rows_from_fake_duplicates_pct'), 2, '%')} of training rows were injected copies",
    ]
    return lines


def _monitoring(results: dict) -> list[str]:
    c = results["data_contract"]
    lines = [
        "",
        "## 6. Early warning: data contract and drift monitoring",
        "",
        "| Monitor | Clean feed | Low-quality feed |",
        "|---|---|---|",
        f"| Data contract: days failed | {c['clean']['days_failed']} of {c['clean']['days']} | {c['low_quality']['days_failed']} of "
        f"{c['low_quality']['days']} (first {c['low_quality']['first_failed_day']}) |",
        f"| Most common contract failure | - | {c['low_quality']['most_common_failure']} |",
    ]
    drift = results["drift"]
    lines += [
        "",
        "| Drift series (daily PSI vs training inputs) | Days 'act' (>0.25) | Days 'watch' | First 'act' day | Most drifted input |",
        "|---|---:|---:|---|---|",
    ]
    for series, d in drift.items():
        lines.append(
            f"| {_name(series)} | {d['days_act']} of {d['days']} | {d['days_watch']} | {d['first_act_day'] or '-'} | {d['most_drifted_feature']} |"
        )
    return lines


def _limits(results: dict) -> list[str]:
    four, u = results["four_conditions"], results["unseen_degradation"]
    ref = four["reference"]["no_fix"]["mae"]
    lines = [
        "",
        "## 7. Limit: a degradation the guard was not designed for",
        "",
        f"{u['description']}: no fix {u['no_fix']['mae']:.1f} min, with fix {u['with_fix']['mae']:.1f} min (clean {ref:.1f}).",
        "",
        "## 8. Human oversight",
        "",
    ]
    for name, entry in four.items():
        wf = entry["with_fix"]
        if "flagged_for_review_pct" in wf:
            lines.append(
                f"- {_name(name)}: {wf['flagged_for_review_pct']:.1f}% of predictions flagged for a dispatcher; error flagged "
                f"{_f(wf.get('mae_flagged'))} vs not flagged {_f(wf.get('mae_not_flagged'))} min; staleness-aware model used for "
                f"{_f(wf.get('staleness_model_pct'), 1, '%')} of predictions"
            )
    return lines


def render(results: dict, daily: pd.DataFrame) -> str:
    lines = [
        "# Bad-data experiment: stale and low-quality data vs the live ETA model, and industry-standard safeguards",
        "",
        "**Simulated progression** on real Yantai courier data (LaDe-D). Always scored against true delivery times, on the",
        "same real packages at the same true checkpoint moments for every condition.",
        "",
        "## Setup",
        "",
    ]
    lines += [f"- **{_name(k).capitalize()}:** {v}" for k, v in results["design"].items()]
    for section in (_conditions(results), _timeline(results), _daily(daily), _mechanism_and_guard(results), _monitoring(results), _limits(results)):
        lines += section
    lines += [
        "",
        f"_Generated from results.json ({results['created_utc'][:19]} UTC, {results['seconds'] / 60:.0f} min run"
        f"{', SMOKE: 20 couriers' if results.get('smoke') else ''})._",
        "",
    ]
    return "\n".join(lines)


def figures() -> None:
    """The results page's line graphs, in the site's colours and fonts: every bad-data test, the test over three
    retrains and by severity, the test window day by day, model training per city, and the arrival windows."""
    import tempfile

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from fontTools.ttLib import TTFont
    from matplotlib import font_manager

    from server.config import MODEL_STORE
    from server.models.bundle import ModelBundle

    fonts = Path(tempfile.mkdtemp())
    for name in ("figtree-regular", "figtree-medium", "eb-garamond-regular"):
        font = TTFont(ROOT / "app" / "public" / "assets" / "fonts" / f"{name}.woff2")
        font.flavor = None
        font.save(fonts / f"{name}.ttf")
        font_manager.fontManager.addfont(str(fonts / f"{name}.ttf"))
    cream, ink, muted, green, orange = "#ffffeb", "#1a1a1a", "#4d6256", "#034f46", "#c2410c"
    plt.rcParams.update(
        {
            "font.family": "Figtree",
            "font.size": 10,
            "text.color": ink,
            "axes.labelcolor": muted,
            "xtick.color": muted,
            "ytick.color": muted,
            "axes.edgecolor": "#c9cbb8",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": "#e1e3d4",
            "figure.facecolor": cream,
            "axes.facecolor": cream,
            "savefig.facecolor": cream,
            "figure.dpi": 160,
            "savefig.bbox": "tight",
            "legend.frameon": False,
            "axes.titlesize": 13,
        }
    )
    clean_colour, palette = "#8c9a92", ["#034f46", "#5b8f7b", "#c2410c", "#d79a3f", "#8c9a92"]
    colours = {"Clean data": clean_colour, "No fix": orange, "With fix": green}
    FIGURES.mkdir(parents=True, exist_ok=True)

    def load(city: str, seed: str = "") -> dict:
        return json.loads((RESULTS / f"results{'' if city == 'yt' else '_' + city}{seed}.json").read_text(encoding="utf-8"))

    runs = {c: load(c) for c in ("yt", "jl")}
    seeds = {c: [load(c, s) for s in ("", "_seed1", "_seed2")] for c in ("yt", "jl")}

    def mean(get, pool) -> float:
        return float(np.mean([np.mean([get(r) for r in results]) for results in pool.values()]))

    def save(fig, name: str) -> None:
        fig.savefig(FIGURES / f"{name}.png")
        plt.close(fig)

    first = {c: [r] for c, r in runs.items()}
    tests = [
        ("Clean data", "four_conditions", "reference"),
        ("Late uploads", "four_conditions", "stale_only"),
        ("Low-quality feed", "four_conditions", "low_quality_only"),
        ("Both at once", "four_conditions", "combined"),
        ("Never retrained", "new_faults", "never_retrained"),
        ("Frozen habits", "new_faults", "frozen_habits"),
        ("Fast device clocks", "new_faults", "fast_clocks"),
        ("Lost scans", "new_faults", "lost_scans"),
    ]
    rows = [
        (name, mean(lambda r, g=g, k=k: r[g][k]["no_fix"]["mae"], seeds), mean(lambda r, g=g, k=k: r[g][k]["with_fix"]["mae"], seeds))
        for name, g, k in tests
    ]
    rows.append(
        (
            "Unseen fault (±30 min)",
            mean(lambda r: r["unseen_degradation"]["no_fix"]["mae"], first),
            mean(lambda r: r["unseen_degradation"]["with_fix"]["mae"], first),
        )
    )
    rows.append(
        (
            "Random weights (control)",
            mean(lambda r: r["random_weight_control"]["random_weights"], first),
            mean(lambda r: r["random_weight_control"]["guard_weights"], first),
        )
    )
    fig, ax = plt.subplots(figsize=(10, 4.6))
    y = np.arange(len(rows))[::-1]
    for yi, (_, before, after) in zip(y, rows, strict=True):
        ax.plot([before, after], [yi, yi], color="#c9cbb8", lw=2, zorder=1)
    ax.scatter([r[1] for r in rows], y, color=orange, s=36, label="Without the fix (control: random weights)", zorder=2)
    ax.scatter([r[2] for r in rows], y, color=green, s=36, label="With the fix", zorder=3)
    ax.axvline(rows[0][1], color=clean_colour, ls="--", lw=1)
    ax.set_yticks(y, [r[0] for r in rows])
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Mean absolute error (min)")
    ax.legend(loc="upper right")
    save(fig, "every-test")

    def pair(name: str, draw, xlabel: str) -> None:
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), sharey=True)
        for ax, (city, results) in zip(axes, runs.items(), strict=True):
            draw(ax, city, results)
            ax.set_title(CITIES[city], loc="left", family="EB Garamond")
            ax.set_xlabel(xlabel)
        axes[0].set_ylabel("Mean absolute error (min)")
        axes[0].legend()
        save(fig, name)

    def monthly(ax, city, results):
        months = list(results["monthly"])
        for key, label in (("reference", "Clean data"), ("bad_data_no_fix", "No fix"), ("bad_data_with_guard", "With fix")):
            ax.plot(months, [results["monthly"][m][key]["mae"] for m in months], marker="o", color=colours[label], label=label)

    def severity(ax, city, results):
        share = [s["share"] * 100 for s in results["severity"]]
        clean = results["four_conditions"]["reference"]["no_fix"]["mae"]
        ax.plot(share, [clean] * len(share), ls="--", color=clean_colour, label="Clean data")
        for key, label in (("no_fix", "No fix"), ("with_fix", "With fix")):
            ax.plot(share, [s[key] for s in results["severity"]], marker="o", color=colours[label], label=label)

    def daily(ax, city, results):
        frame = pd.read_csv(RESULTS / f"daily{'' if city == 'yt' else '_' + city}.csv")
        for system, label in (("reference|no_fix", "Clean data"), ("combined|no_fix", "No fix"), ("combined|with_fix", "With fix")):
            part = frame.loc[frame["system"] == system]
            ax.plot(part["day"], part["mae"], marker=".", color=colours[label], label=label)
        ax.tick_params(axis="x", rotation=60, labelsize=8)

    pair("retraining", monthly, "Retrained on")
    pair("severity", severity, "Couriers on the low-quality feed (%)")
    pair("test-window", daily, "Day (September)")

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10, 3.6))
    validation, test, median = [], [], []
    for (city, name), colour in zip(CITIES.items(), palette, strict=True):
        curve = ModelBundle.load(MODEL_STORE / city / "model.pkl").eta.models[0].evals_result_["valid_0"]["l1"]
        ax.plot(np.arange(1, len(curve) + 1), curve, color=colour, label=name)
        overall = json.loads((MODEL_STORE / city / "metrics.json").read_text(encoding="utf-8"))["overall"]
        validation.append(min(curve))
        test.append(overall["mae"])
        median.append(overall["median_ae"])
    ax.set_yscale("log")
    ax.set_xlabel("Trees")
    ax.set_ylabel("Validation error (min, log)")
    ax.legend(fontsize=8)
    for values, label, colour, style in (
        (validation, "Validation", clean_colour, "--"),
        (test, "Test", green, "-"),
        (median, "Test, median", orange, "-"),
    ):
        bx.plot(list(CITIES.values()), values, marker="o", color=colour, ls=style, label=label)
    bx.set_yscale("log")
    bx.set_ylabel("Error (min, log)")
    bx.legend()
    save(fig, "models")

    windows = json.loads((ROOT / "app" / "src" / "pages" / "dashboard" / "windows.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(10, 3.4))
    for (city, name), colour in zip(CITIES.items(), palette, strict=True):
        spread = windows[city]
        width = [(a or 0) - (b or 0) for a, b in zip(spread["after_min"][:4], spread["before_min"][:4], strict=True)]
        ax.plot(
            ["< 30 min", "30-60 min", "1-3 h", "3-24 h"], width, marker="o", color=colour, label=f"{name}, {spread['test_coverage_pct']:.0f}% inside"
        )
    ax.set_yscale("log")
    ax.set_xlabel("How far away the ETA was")
    ax.set_ylabel("Window width (min, log)")
    ax.legend(fontsize=8)
    save(fig, "windows")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--figures", action="store_true", help="draw the results page's line graphs instead")
    args = parser.parse_args()
    if args.figures:
        return figures()
    suffix = "_smoke" if args.smoke else ""
    results = json.loads((RESULTS / f"results{suffix}.json").read_text(encoding="utf-8"))
    daily = pd.read_csv(RESULTS / f"daily{suffix}.csv", dtype={"day": str})
    (RESULTS / f"REPORT{suffix}.md").write_text(render(results, daily), encoding="utf-8")
    print(f"wrote {RESULTS / f'REPORT{suffix}.md'}")


if __name__ == "__main__":
    main()
