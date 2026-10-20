"""Categorical encoding with a vocabulary fitted on training rows only (unseen values become missing)."""

import pandas as pd

from server.config import CATS


def fit_schema(frame: pd.DataFrame, columns: list[str]) -> dict[str, list[str]]:
    return {name: sorted(frame[name].astype("string").dropna().unique().tolist()) for name in CATS if name in columns}


def encode(frame: pd.DataFrame, columns: list[str], schema: dict[str, list[str]]) -> pd.DataFrame:
    out = frame[columns].copy()
    for name, categories in schema.items():
        out[name] = out[name].astype("string").astype(pd.CategoricalDtype(categories=categories))
    return out


def categorical_columns(columns: list[str]) -> list[str]:
    return [c for c in CATS if c in columns]
