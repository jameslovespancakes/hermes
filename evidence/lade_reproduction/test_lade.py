"""Score a saved LaDe checkpoint on the test split (their own test_model via their run(), model_path set)."""
import os, sys
TP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LaDe", "time_prediction")
os.chdir(TP); sys.path.insert(0, TP)
from utils.util import get_common_params, dict_merge
from run import run
dataset, model, path = sys.argv[1], sys.argv[2], sys.argv[3]
base = vars(get_common_params().parse_known_args([])[0])
run(dict_merge([base, {"model": model, "dataset": dataset, "hidden_size": 64, "workers": 0, "batch_size": 16,
                       "is_test": False, "inference": False, "model_path": path}]))
