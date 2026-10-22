"""Run independent LightGBM fits side by side, splitting the CPU cores between them."""

import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from server.config import THREADS


def fit_all(jobs: list[Callable[[int], object]]) -> list:
    """Each job takes a thread count and returns a fitted model; models are reset to THREADS for prediction."""
    threads = max(2, min(THREADS, (os.cpu_count() or THREADS) // len(jobs)))
    with ThreadPoolExecutor(len(jobs)) as pool:
        models = list(pool.map(lambda job: job(threads), jobs))
    for model in models:
        model.set_params(n_jobs=THREADS)
    return models
