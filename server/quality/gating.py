"""Gated retraining (champion vs challenger) on an audited sample with verified delivery times."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from server.quality.config import QUALITY, QualityConfig


@dataclass(frozen=True)
class GateDecision:
    promote: bool
    champion_mae: float
    challenger_mae: float
    audited_predictions: int
    reason: str


def audit_sample(order_ids: pd.Series, rate: float = QUALITY.audit_rate, seed: int = 7) -> pd.Series:
    """Deterministic audit flag per package (e.g. deliveries confirmed by the customer or a geofence)."""
    unique = np.sort(order_ids.unique())
    chosen = set(unique[np.random.default_rng(seed).uniform(size=len(unique)) < rate])
    return order_ids.isin(chosen)


def gate(
    champion_error: np.ndarray,
    challenger_error: np.ndarray,
    min_improvement_min: float = QUALITY.min_improvement_min,
    min_audited: int = QUALITY.min_audited_predictions,
) -> GateDecision:
    champion_error, challenger_error = np.asarray(champion_error, float), np.asarray(challenger_error, float)
    if len(champion_error) != len(challenger_error):
        raise ValueError("champion and challenger must be scored on the same audited predictions")
    champ, chall = (float(np.mean(e)) if len(e) else float("nan") for e in (champion_error, challenger_error))
    if len(champion_error) < min_audited:
        return GateDecision(False, champ, chall, len(champion_error), "too few audited predictions; keep champion")
    if chall <= champ - min_improvement_min:
        return GateDecision(True, champ, chall, len(champion_error), "challenger better on audited deliveries")
    return GateDecision(False, champ, chall, len(champion_error), "challenger not better; keep champion and alert")


def audited_gate(
    champion: pd.DataFrame, challenger: pd.DataFrame, truth: pd.Series, outcomes_before: pd.Timestamp, config: QualityConfig = QUALITY
) -> GateDecision:
    """Gate on audited packages whose delivery was confirmed before `outcomes_before`."""
    both = champion.merge(challenger, on=["s", "order_id"], suffixes=("_champ", "_chall"))
    audited = both.loc[audit_sample(both["order_id"], config.audit_rate) & (both["order_id"].map(truth) < outcomes_before)]
    return gate(
        np.abs(audited["minutes_remaining_champ"] - audited["actual_champ"]),
        np.abs(audited["minutes_remaining_chall"] - audited["actual_chall"]),
        config.min_improvement_min,
        config.min_audited_predictions,
    )
