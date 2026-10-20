"""Re-score a trained LaDe M2G4RTP checkpoint two ways on its own test split:

  as_published : their metric. k-th predicted ETA (decode step k) vs k-th ACTUAL delivery time.
                 It never checks which package was predicted at step k.
  per_package  : each package's predicted ETA (the ETA at the step where the model chose that package)
                 vs that package's actual time. This is what a customer experiences.

Uses their model, data, and preprocessing unchanged (filter_input, edge construction as in test_model).
"""
import os
import sys

import numpy as np
import torch

TP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LaDe", "time_prediction")
os.chdir(TP)
sys.path.insert(0, TP)
from torch.utils.data import DataLoader  # noqa: E402
from utils.util import get_common_params, dict_merge, get_dataset_path, to_device  # noqa: E402
from algorithm.m2g4rtp_delivery.Dataset import M2GDataset  # noqa: E402
from algorithm.m2g4rtp_delivery.m2g4rtp import M2G4RTP  # noqa: E402
from algorithm.m2g4rtp_delivery.train import filter_input  # noqa: E402

dataset, checkpoint = sys.argv[1], sys.argv[2]
device = torch.device("cuda")
params = dict_merge([vars(get_common_params().parse_known_args([])[0]),
                     {"model": "m2g4rtp_delivery", "dataset": dataset, "hidden_size": 64, "device": device,
                      "sort_x_size": 8, "start_fea": 4}])
params["pad_value"] = params["max_task_num"] - 1
params["train_path"], params["val_path"], params["test_path"] = get_dataset_path(params)
model = M2G4RTP(params).to(device)
model.load_state_dict(torch.load(checkpoint, map_location=device))
model.eval()
loader = DataLoader(M2GDataset(mode="test", params=params), batch_size=16, shuffle=False)

pub_err, pkg_err, pkg_lab = [], [], []
with torch.no_grad():
    for batch in loader:
        batch = to_device(batch, device)
        (V, V_reach_mask, label, label_len, V_at, start_fea, cou_fea, aoi_feature_steps, aoi_start_steps,
         aoi_pos_steps, aoi_len_steps, aoi_idx_steps, aoi_index_steps, E_static_fea, E_mask) = batch
        B, T, N, _ = E_mask.shape
        E = torch.zeros([B, T, N, N, E_static_fea.shape[-1]], device=device)
        for t in range(T):
            E[:, t] = E_static_fea * E_mask[:, t].unsqueeze(-1).expand(E_static_fea.shape)
        (V, V_reach_mask, cou_fea, label, label_len, V_at, start_fea, aoi_feature_steps, aoi_start_steps, aoi_pos_steps,
         aoi_len_steps, aoi_index_steps, aoi_idx_steps, E) = filter_input(
            V, V_reach_mask, cou_fea, label, label_len, V_at, start_fea, aoi_feature_steps, aoi_start_steps,
            aoi_pos_steps, aoi_len_steps, aoi_index_steps, aoi_idx_steps, E)
        _, pointers, eta, _ = model(V, V_reach_mask, start_fea, cou_fea, aoi_feature_steps, aoi_start_steps,
                                    aoi_pos_steps, aoi_len_steps, aoi_index_steps, E, is_train=False)
        label, V_at, pointers, eta = label.long().cpu().numpy(), V_at.cpu().numpy(), pointers.cpu().numpy(), eta.cpu().numpy()
        for i, n in enumerate(label_len.long().cpu().numpy()):
            if n == 0:
                continue
            # as published: position-wise, predicted step k vs actual k-th delivery (their code casts to integer minutes)
            pub_err.extend(np.abs(np.trunc(eta[i, :n]) - np.trunc(V_at[i, :n])).tolist())
            true_time = {int(label[i, k]): float(V_at[i, k]) for k in range(n)}        # slot -> actual minutes
            pred_time = {}
            for k in range(eta.shape[1]):                                              # slot -> ETA at the step it was chosen
                slot = int(pointers[i, k])
                if slot in true_time and slot not in pred_time:
                    pred_time[slot] = float(eta[i, k])
            for slot, actual in true_time.items():
                if slot in pred_time:
                    pkg_err.append(abs(pred_time[slot] - actual))
                    pkg_lab.append(actual)

pub, pkg = np.array(pub_err), np.array(pkg_err)
print(f"{dataset}: {len(pkg):,} package predictions")
print(f"  as published (step k vs k-th actual): MAE {pub.mean():.2f} min | within 20 min {np.mean(pub <= 20) * 100:.1f}%")
print(f"  per package (customer view):          MAE {pkg.mean():.2f} min | within 20 min {np.mean(pkg <= 20) * 100:.1f}%")
