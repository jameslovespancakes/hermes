"""Prove each leak in the LaDe time-prediction benchmark straight from the authors' code (pinned commit).

    uv run python -m evidence.leaks.setup           # once
    uv run python -m evidence.leaks.check           # one line per leak, with file:line references
    uv run python -m evidence.leaks.check --clean   # the same checks on clean.py's leak-free copies

A leak is confirmed when every code fragment that creates it is present, in that order, in the file.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path

TP = Path(__file__).resolve().parent / "LaDe" / "time_prediction"
DATASET, PREPROCESS, M2G_TRAIN = "data/dataset_delivery.py", "data/preprocess_delivery.py", "algorithm/m2g4rtp_delivery/train.py"
CLEAN_FILES = {DATASET: "data/dataset_delivery_clean.py", PREPROCESS: "data/preprocess_delivery_clean.py"}


@dataclass(frozen=True)
class Leak:
    title: str
    why: str
    code: tuple[tuple[str, tuple[str, ...]], ...]  # (file, fragments that must appear in this order)


LEAKS = [
    Leak(
        "Inputs chosen by the answer",
        "a pending package is shown to the model only if its ACTUAL delivery is 0-120 min after now (not in the paper)",
        (
            (
                DATASET,
                (
                    "time_label = c_v[c_idx][self.idx_finish_time] - c_v[start][self.idx_finish_time]",
                    "if time_label <= self.params['label_range'][0] or time_label > self.params['label_range'][1]:",
                    "parser.add_argument('--label_range', type=tuple, default=(0, 120))",
                ),
            ),
        ),
    ),
    Leak(
        "Inputs cut by true delivery order",
        "packages are numbered in actual delivery order, and only the courier-day's first 24 can be inputs",
        (
            (PREPROCESS, ("df = df.sort_values(by=['ds', 'courier_id', 'delivery_time'])", "df.insert(0, 'index', range(1, df.shape[0] + 1))")),
            (
                DATASET,
                (
                    "self.N = params['len_range'][1]",
                    "c_idx = task_id - id_first",
                    "if c_idx >= self.N - 1:",
                    "parser.add_argument('--len_range', type=tuple, default=(1, 25))",
                ),
            ),
        ),
    ),
    Leak(
        "Busy test days discarded",
        "a test courier-day with a package beyond that cap is dropped entirely (training days are kept)",
        ((DATASET, ("if c_idx >= self.N - 1:", "if mode == 'test':", "return 0")),),
    ),
    Leak(
        "Statistics computed over all dates",
        "courier and area statistics are built from the whole file, test dates included, before the date split",
        (
            (
                PREPROCESS,
                (
                    "couriers, couriers_feature = courier_info(df)",
                    'aoi_actime[aoi] += courier_l[i].iloc[j]["time_to_last_package"]',
                    'aoi_time_adj[from_aoi][to_aoi] = aoi_time_adj[from_aoi][to_aoi] + courier_l[i].iloc[j][ "time_to_last_package"]',
                ),
            ),
            (DATASET, ("pre_process(fin=self.params['fin_original']", "df = df[df['ds'].isin(test_dates)]")),
        ),
    ),
    Leak(
        "Area features from the actual future route",
        "M2G4RTP's area inputs walk pending packages in true delivery order and stop at the first area revisit",
        (
            (
                DATASET,
                (
                    "todo_rank.sort()",
                    "last_aoi = self.aoi_dict[cou[cou['index'] == todo_rank[0]]['aoi_id'].iloc[0]]",
                    "for i in range(1, len(todo_rank)):",
                    "if aoi in aoi_set:",
                    "break",
                ),
            ),
        ),
    ),
    Leak(
        "Scored by rhythm, not by package",
        "M2G4RTP's k-th predicted time is compared with the k-th actual delivery, whichever package it predicted",
        (
            (DATASET, ("V_at[t, todo_rank_.index(task)] = c_v[task_idx][self.idx_finish_time] - c_v[start][self.idx_finish_time]",)),
            (M2G_TRAIN, ("get_eta_result(eta, V_at, label_len, label, pred_pointers)",)),
        ),
    ),
]


def locate(text: str, fragments: tuple[str, ...]) -> list[int] | None:
    """1-based line of each fragment, each found after the previous one; None if any is missing."""
    lines, position = [], 0
    for fragment in fragments:
        found = text.find(fragment, position)
        if found < 0:
            return None
        lines.append(text.count("\n", 0, found) + 1)
        position = found + len(fragment)
    return lines


def check(leak: Leak, root: Path, files: dict[str, str] | None = None) -> dict[str, list[int]] | None:
    """Where the leak lives ({file: lines}), or None if its code is not there."""
    where = {}
    for name, fragments in leak.code:
        name = (files or {}).get(name, name)
        path = root / name
        lines = locate(path.read_text(encoding="utf-8"), fragments) if path.exists() else None
        if lines is None:
            return None
        where[name] = lines
    return where


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="check clean.py's leak-free copies instead")
    args = parser.parse_args()
    if not (TP / DATASET).exists():
        raise SystemExit("run `uv run python -m evidence.leaks.setup` first")
    files = CLEAN_FILES if args.clean else None
    confirmed = 0
    for number, leak in enumerate(LEAKS, 1):
        where = check(leak, TP, files)
        confirmed += where is not None
        status = "LEAK " if where else "clean"
        refs = "; ".join(f"{name}:{','.join(map(str, lines))}" for name, lines in (where or {}).items())
        print(f"[{status}] {number}. {leak.title}: {leak.why}" + (f"\n          {refs}" if refs else ""))
    print(f"\n{confirmed} of {len(LEAKS)} leaks present in {'clean.py output' if args.clean else 'the published code'}.")


if __name__ == "__main__":
    main()
