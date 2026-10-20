"""Run LaDe's own time-prediction models via their run() entry point (their default hyper-parameters).
Only change: workers=0 (Windows cannot fork-share the large in-memory dataset)."""
import os, sys, time
TP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LaDe", "time_prediction")
os.chdir(TP); sys.path.insert(0, TP)
from utils.util import get_common_params, dict_merge
from run import run

dataset, models = sys.argv[1], sys.argv[2:]
base = vars(get_common_params().parse_known_args([])[0])
for model in models:
    params = dict_merge([base, {"model": model, "dataset": dataset, "hidden_size": 64, "workers": 0, "batch_size": int(os.environ.get("LADE_BATCH", 64)), "num_epoch": int(os.environ.get("LADE_EPOCHS", 60)), "early_stop": int(os.environ.get("LADE_PATIENCE", 11)), "is_test": False, "inference": False}])
    t0 = time.time()
    print(f"===== {model} on {dataset}", flush=True)
    run(params)
    print(f"===== {model} done in {(time.time() - t0) / 60:.1f} min", flush=True)
