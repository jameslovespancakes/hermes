"""Create a CLEANED copy of LaDe's delivery time-prediction data pipeline (originals untouched).

Fixes (each a minimal, asserted text edit; documented in external/LADE_PATCHES.md):
  1. Courier statistics (speed, distance/day, time per order, ...) from TRAINING dates only.
  2. Area statistics (avg time per package, area-to-area travel times) from TRAINING dates only.
  3. M2G4RTP area (AOI) features no longer built by walking pending packages in their TRUE future
     delivery order (run lengths, truncation at first revisit). Instead: unique pending areas ordered by
     distance from the courier, with the count of pending packages per area.
  4. Test courier-days are no longer discarded when a pending task index exceeds the 25-slot cap; the
     task is skipped exactly as in training.
Not changed: their task definition (a pending package is a query only if it finishes 0-120 min later).
"""
from pathlib import Path

TP = Path(__file__).resolve().parent / "LaDe" / "time_prediction" / "data"


def edit(text, old, new, count=1):
    assert text.count(old) == count, f"expected {count} match(es) for:\n{old[:200]}"
    return text.replace(old, new)


# ---------------------------------------------------------------- preprocess_delivery_clean.py
pre = (TP / "preprocess_delivery.py").read_text(encoding="utf-8")
pre = edit(pre, "    # get couriers features\n    couriers, couriers_feature = courier_info(df)\n",
           "    # get couriers features  [CLEAN: training dates only; unseen couriers get training medians]\n"
           "    couriers, couriers_feature = courier_info_train_only(df)\n")
pre = edit(pre, "def courier_info(df):\n", '''def train_dates_of(df, train_ratio=0.6):
    all_dates = df['ds'].unique()  # df is sorted by ds, same order as dataset_delivery.get_data
    return set(all_dates[: int(len(all_dates) * train_ratio)].tolist())


def courier_info_train_only(df):
    train = df[df['ds'].isin(train_dates_of(df))]
    _, feat = courier_info(train)
    couriers = list(set(df['courier_id']))
    for key, values in feat.items():
        if key in ('index', 'id'):
            continue
        median = float(np.median(list(values.values())))
        for c in couriers:
            values.setdefault(c, median)
    for i, c in enumerate(couriers):
        feat['index'][c], feat['id'][c] = i, c
    return couriers, feat


def courier_info(df):
''')
pre = edit(pre, "    courier_l = split_trajectory(df)\n\n    aoi_nums = df[\"aoi_id\"].nunique()\n",
           "    train_dates = train_dates_of(df)  # [CLEAN] area time statistics from training dates only\n"
           "    courier_l = split_trajectory(df)\n\n    aoi_nums = df[\"aoi_id\"].nunique()\n    aoi_time_num = np.zeros([aoi_nums])\n")
pre = edit(pre, '''            aoi_actime[aoi] += courier_l[i].iloc[j]["time_to_last_package"]
''', '''            is_train_day = courier_l[i].iloc[j]["ds"] in train_dates
            if is_train_day:
                aoi_actime[aoi] += courier_l[i].iloc[j]["time_to_last_package"]
                aoi_time_num[aoi] += 1
''')
pre = edit(pre, "            if j != 0:\n                from_aoi", "            if j != 0 and is_train_day:\n                from_aoi")
pre = edit(pre, "    aoi_actime = np.divide(aoi_actime, aoi_order_num)\n",
           "    aoi_actime = np.divide(aoi_actime, np.maximum(aoi_time_num, 1))\n")
(TP / "preprocess_delivery_clean.py").write_text(pre, encoding="utf-8")

# ---------------------------------------------------------------- dataset_delivery_clean.py
ds = (TP / "dataset_delivery.py").read_text(encoding="utf-8")
ds = edit(ds, "from data.preprocess_delivery import pre_process, split_trajectory, list2str",
          "from data.preprocess_delivery_clean import pre_process, split_trajectory, list2str")
ds = edit(ds, """                    if mode == 'test':
                        # print('remove sample that are out of index bound')
                        return 0
""", """                    # [CLEAN] busy test days are no longer discarded; the task is skipped as in training
""")
start = ds.index("            if len(todo_rank) <= self.N_min:\n                aoi_fea = [[0 for _ in range(self.params['aoi_fea_len'])]] * self.aoi_len")
end = ds.index("            aoi_feature_steps[t, :, :] = np.array(aoi_fea).reshape(self.aoi_len, -1)")
clean_block = '''            # [CLEAN] Area features WITHOUT the true future order: unique pending areas ordered by distance
            # from the courier, with the number of pending packages in each area. Labels (aoi_eta) still
            # come from actual finish times, as they must.
            if len(todo_rank) <= self.N_min:
                aoi_fea = [[0 for _ in range(self.params['aoi_fea_len'])]] * self.aoi_len
                aoi_eta = [0 for _ in range(self.aoi_len)]
                aoi_len = 0
                aoi_idx = [-1 for _ in range(self.aoi_len)]
                aoi_pos = [-1 for _ in range(self.aoi_len)]
                aoi_start_feature = [0, 0, 0, 0]
            else:
                area_count, area_first_finish = {}, {}
                for task in todo_rank:
                    aoi = self.aoi_dict[cou[cou['index'] == task]['aoi_id'].iloc[0]]
                    area_count[aoi] = area_count.get(aoi, 0) + 1
                    finish = c_v[task - id_first][self.idx_finish_time] - c_v[start][self.idx_finish_time]
                    area_first_finish[aoi] = min(area_first_finish.get(aoi, np.inf), finish)
                by_distance = sorted(area_count, key=lambda a: self.dis_cal(now_lat, now_lng, self.aoi_feature[a][3], self.aoi_feature[a][2]))
                aoi_fea, aoi_eta = [], []
                for aoi in by_distance:
                    f = self.aoi_feature[aoi]
                    aoi_fea.append([aoi, f[1], f[2], f[3], self.dis_cal(now_lat, now_lng, f[3], f[2]), area_count[aoi]])
                    aoi_eta.append(area_first_finish[aoi])
                aoi_len = len(by_distance)
                if aoi_len <= 1 or aoi_len > self.params['aoi_len']:
                    aoi_fea, aoi_eta, aoi_len, aoi_idx, aoi_pos, aoi_start = 0, 0, 0, 0, 0, 0

                if aoi_fea == 0:
                    aoi_fea = [0 for _ in range(self.params['aoi_fea_len'])] * self.aoi_len
                    aoi_eta = [-1 for _ in range(self.aoi_len)]
                    aoi_len = 0
                    aoi_idx = [-1 for _ in range(self.aoi_len)]
                    aoi_pos = [-1 for _ in range(self.aoi_len)]
                    aoi_start_feature = [0, 0, 0, 0]
                    aoi_index = [0 for _ in range(self.N)]
                else:
                    aoi_pos = [i for i in range(aoi_len)]
                    random.shuffle(aoi_pos)
                    aoi_fea = np.array(aoi_fea)[aoi_pos].tolist()
                    aoi_eta = np.array(aoi_eta)[aoi_pos].tolist()
                    aoi_idx = np.argsort(aoi_eta).tolist()
                    for _ in range(self.aoi_len - aoi_len):
                        aoi_fea.append([0 for _ in range(self.params['aoi_fea_len'])])
                    aoi_idx += [10 - aoi_len for _ in range(self.aoi_len - aoi_len)]
                    aoi_pos += [-1 for _ in range(self.aoi_len - aoi_len)]
                    aoi_eta += [-1 for _ in range(self.aoi_len - aoi_len)]

'''
ds = ds[:start] + clean_block + ds[end:]
ds = edit(ds, "default=ws + '/data/tmp/delivery_yt/')", "default=ws + '/data/tmp/delivery_yt_clean/')")
ds = edit(ds, "parser.add_argument('--data_name', type=str, default='delivery_yt')", "parser.add_argument('--data_name', type=str, default='delivery_yt_clean')")
(TP / "dataset_delivery_clean.py").write_text(ds, encoding="utf-8")
print("wrote preprocess_delivery_clean.py and dataset_delivery_clean.py")
