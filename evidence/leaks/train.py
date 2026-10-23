"""Train (or re-score) one of the LaDe authors' time-prediction models with their own run() entry point and settings.

    python evidence/leaks/train.py delivery_yt m2g4rtp_delivery              # train; writes their results CSV
    python evidence/leaks/train.py delivery_yt m2g4rtp_delivery <checkpoint> # score a saved checkpoint

Needs a Python env with PyTorch and LaDe/time_prediction/requirements.txt (see setup.py). Only changes from their
defaults: workers=0 (Windows cannot fork-share the in-memory dataset); batch 16 for M2G4RTP (fits a 12 GB GPU;
the paper states 32).
"""

import os
import sys

TP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LaDe", "time_prediction")
os.chdir(TP)
sys.path.insert(0, TP)
from run import run  # noqa: E402
from utils.util import dict_merge, get_common_params  # noqa: E402

dataset, model = sys.argv[1], sys.argv[2]
checkpoint = sys.argv[3] if len(sys.argv) > 3 else None
params = {
    "model": model,
    "dataset": dataset,
    "hidden_size": 64,
    "workers": 0,
    "is_test": False,
    "inference": False,
    "batch_size": 16 if model.startswith("m2g4rtp") else 64,
    "num_epoch": 60,
    "early_stop": 11,
}
if checkpoint:
    params["model_path"] = checkpoint
run(dict_merge([vars(get_common_params().parse_known_args([])[0]), params]))
