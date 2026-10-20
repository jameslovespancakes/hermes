"""Chronological row selection for live queries. Training rows only use outcomes known by the cutoff."""

import pandas as pd

from server.config import FIT_SAMPLE, SEED, Split


def fit_rows(live: pd.DataFrame, split: Split, sample: int | None = FIT_SAMPLE) -> pd.DataFrame:
    """Events before fit_end whose package outcome was also known before fit_end (optionally sampled)."""
    cutoff = split.fit_cutoff
    rows = live.loc[(live["s"] < cutoff) & (live["_delivered_at"] < cutoff)]
    if sample and len(rows) > sample:
        rows = rows.sample(n=sample, random_state=SEED)
    return rows


def stop_rows(live: pd.DataFrame, split: Split) -> pd.DataFrame:
    """Early-stopping window: events fit_end..stop_end with outcomes known before stop_end."""
    s = live["s"]
    return live.loc[(s >= split.fit_cutoff) & (s < split.stop_cutoff) & (live["_delivered_at"] < split.stop_cutoff)]


def test_rows(live: pd.DataFrame, split: Split) -> pd.DataFrame:
    """Held-out window: events stop_end..test_end, every outcome kept."""
    s = live["s"]
    return live.loc[(s >= split.stop_cutoff) & (s < split.data_cutoff)]
