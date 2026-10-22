"""Input drift monitoring with the Population Stability Index (PSI), as used by common model monitors."""

import numpy as np
import pandas as pd

from server.quality.config import QUALITY, QualityConfig

EPSILON = 1e-4


def _edges(reference: np.ndarray, bins: int) -> np.ndarray:
    finite = reference[np.isfinite(reference)]
    if not len(finite):
        return np.array([0.0])
    return np.unique(np.append(np.quantile(finite, np.linspace(0, 1, bins + 1)[1:-1]), finite.max()))


def _shares(values: np.ndarray, edges: np.ndarray) -> np.ndarray:
    finite = np.isfinite(values)
    counts = np.bincount(np.digitize(values[finite], edges, right=True), minlength=len(edges) + 1).astype(float)
    counts = np.append(counts, (~finite).sum())
    return np.maximum(counts / max(len(values), 1), EPSILON)


def psi(reference, current, bins: int = 10) -> float:
    reference, current = np.asarray(reference, dtype=float), np.asarray(current, dtype=float)
    edges = _edges(reference, bins)
    ref, cur = _shares(reference, edges), _shares(current, edges)
    return float(np.sum((cur - ref) * np.log(cur / ref)))


def calibrate(reference: pd.DataFrame, earlier: pd.DataFrame, features: list[str], config: QualityConfig = QUALITY) -> dict:
    """Per-input thresholds: conventional levels, raised above each input's natural drift in clean history."""
    natural = {f: psi(reference[f], earlier[f]) for f in features}
    margin = config.drift_margin
    return {
        f: {"natural_psi": v, "watch": max(config.drift_watch, margin * v), "act": max(config.drift_act, 2 * margin * v)} for f, v in natural.items()
    }


def level(value: float, watch: float = QUALITY.drift_watch, act: float = QUALITY.drift_act) -> str:
    return "act" if value > act else "watch" if value > watch else "stable"


def drift_report(reference: pd.DataFrame, current: pd.DataFrame, features: list[str], thresholds: dict | None = None, bins: int = 10) -> dict:
    """PSI and alert level per input (calibrated thresholds if given), plus the most severe input."""
    scores = {f: psi(reference[f], current[f], bins) for f in features}
    limits = thresholds or {f: {"watch": QUALITY.drift_watch, "act": QUALITY.drift_act} for f in features}
    levels = {f: level(v, limits[f]["watch"], limits[f]["act"]) for f, v in scores.items()}
    severity = {"stable": 0, "watch": 1, "act": 2}
    worst = max(features, key=lambda f: (severity[levels[f]], scores[f] / limits[f]["act"]))
    return {"psi": scores, "levels": levels, "worst_feature": worst, "worst_psi": scores[worst], "alert": levels[worst]}
