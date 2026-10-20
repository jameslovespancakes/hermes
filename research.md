# Research findings: delivery-time prediction on LaDe

Plain-language summary of what the published research says about this dataset, what we found when we checked
it, and what our own experiments showed. Numbers come from files in `evidence/`; the best model lives in `server/`.

## 1. In one paragraph
We predict **how many minutes until a courier delivers a package**, re-predicted after every delivery. Our best
model (two chained LightGBM models: delivery **order**, then **time**) is off by **58 minutes on average and
29 minutes typically**, about **33 minutes for packages due within two hours** (Yantai, late September). The
published state of the art looks far better (12-17 minutes), but when we re-ran it ourselves we found its
headline numbers depend on **information from the future** and a **scoring shortcut**. Tested fairly on the same
packages, it scores **77 minutes; ours scores 58.6**.

## 2. The dataset (LaDe-D, Cainiao)
- About 4.5 million deliveries from five Chinese cities, May-October (we used Yantai: 206,431 records).
- Each record: courier, destination (area + coordinates), **when the courier accepted the task**, and **when it was
  recorded delivered**. There is no customer order time and no independent proof of receipt.
- Typical delivery takes **1 h 45 min** after acceptance, but the average is **3.1 h** because **1% of deliveries
  take over a day** and account for **21% of all delivery time**.
- Quirks we found (not documented by the authors):
  - A courier's consecutive deliveries are **never less than 5 minutes apart**, in all five cities, even for
    next-door stops. Timestamps appear processed (spread out or thinned). This puts a floor under any accuracy.
  - The delivery GPS time equals the delivery time in 100% of rows (checked in Yantai and Shanghai).
  - Three Chongqing records run from October to January; the files have no year, so these look negative.
- Data rights: provided by the case organizers; use confirmed with the case owners. Public metadata differs
  (Hugging Face: Apache-2.0; paper: CC BY-NC 4.0), so we keep attribution and non-commercial use.

## 3. How others build these models
- **Industry** (Uber, DoorDash, Swiggy, JD): start with gradient-boosted trees; move to deep learning only at huge
  scale; use live signals (recent delivery times in the area); losses that penalise lateness; retrain regularly.
- **Research on courier routes** (Cainiao/LaDe authors): predict the courier's **stop order**, then times. Route
  accuracy has plateaued: the best models get the **next 3 stops right about 72% of the time**, and plain LightGBM
  is only 1-2 points behind.
- **No ready-made model exists to download**: companies keep theirs private; the LaDe code ships without weights
  and without a license file.

## 4. What we found when we checked the published benchmark
We downloaded the LaDe authors' code and trained their best ETA model (M2G4RTP) ourselves.

**The code did not run as published.** Seven fixes were needed (missing modules, wrong imports, an evaluation crash,
a hard-coded GPU, a results-saving crash). See `evidence/lade_reproduction/LADE_PATCHES.md`.

**Leaks and shortcuts in their setup** (from reading and running the code):
1. **Inputs filtered by the answer:** a package is shown to the model only if it *will* be delivered within
   2 hours. The paper never mentions this filter.
2. **Inputs limited to the next ~24 deliveries in true delivery order.**
3. **Busy test days discarded** (more than 25 packages).
4. **Statistics computed over all dates**, test period included.
5. **M2G4RTP only:** area features built from the courier's *actual future route*.
6. **M2G4RTP's scoring checks the rhythm, not the package:** the 1st predicted time is compared with the 1st actual
   delivery, the 2nd with the 2nd, and so on, without checking *which* package was predicted.

**What that does to the score** (Yantai):
| Their M2G4RTP | Error |
|---|---:|
| Paper's reported result | 17.2 min |
| Our rerun of their code, their scoring | 12.5 min |
| Same model, scored per package | 22.2 min |
| Leaks 3-5 removed (inputs still filtered/windowed), per package | 23.3 min |
| **Fully fair** (real pending packages, per-package scoring) | **77.1 min** |
| **Our model on the same 149,263 packages** | **58.6 min** |

Their simpler models (MLP, "LightGBM" which is actually XGBoost in their code, RankETPA) are scored per package
but share the leaky inputs. We found no leak-free model in their benchmark.

## 5. What our own experiments showed
| Idea | Effect | Kept? |
|---|---|---|
| Re-predict after every delivery (live ETA) | **-18%** error vs the original acceptance-time prediction | Yes |
| Retrain regularly | a frozen model drifted 91 -> 103 -> 111 min over 3 months; monthly retraining held ~90-92 | Yes (re-run `train` on fresh data) |
| Courier habits (when they usually reach an area) | -2 to -2.5% | Yes |
| Learned route-order model + area-to-area habits | about -2% | Yes |
| More training data, tuning | about -2% each at acceptance time | Partly |
| Optuna search (60 trials, 3 future months) | about -0.5% vs hand tuning | No (not worth it) |
| Neural network / PyTorch graph "chain-of-thought" model | worse alone; ~1% when blended | No |
| Travel time along the predicted route | 0% | No |
| Google TimesFM 3.0 pace forecasts | 0% (worse than a 7-day average at forecasting pace) | No |
| Dropping weak features | 0% (20 features do the work of 51) | No |

Two lessons about *measurement*:
- **Random 80/20 splits overstate accuracy** by 5-10 minutes compared with what happens the following month.
  Time order must be preserved.
- **If the true delivery order were known**, error would fall about 38% (58 -> 37 min). Order is the main missing
  information, but no model, ours or published, predicts it much better than ~70% for the next 3 stops.

## 6. The best model (in `server/`)
After each courier delivery: build the courier's pending packages -> predict their delivery order -> predict
minutes remaining. Trained on May-August, early-stopped on September 1-15, tested on September 16-30.

| Yantai test (Sep 16-30) | Result |
|---|---:|
| Average error | **58.4 min** |
| Typical error | **29.0 min** |
| Due within 30 min / 30-60 min / 1-3 h / 3-24 h | 33.0 / 33.5 / 35.6 / 106.8 min |
| Next 3 stops predicted correctly | 69% |

## 7. Honest limits
- One city (Yantai), one test window, one random seed. September was inspected during development, so it is not
  an untouched final test. October is untouched.
- "Delivered" means the courier recorded it, not that the customer confirmed it.
- Coordinates are privacy-perturbed; distances are straight-line, not roads.
- The 5-minute timestamp floor and multi-day holds limit any model's accuracy.

## 8. Next steps
1. The case-a-thon question: degrade the data (stale feeds, low-quality records), measure the damage, test a fix.
2. Live area conditions (how long deliveries in this area are taking right now), the most promising missing signal.
3. Confirm on Shanghai and October; add an uncertainty range for customer-facing promises.

## Sources
- Wu et al., *LaDe*, arXiv:2306.10675; dataset huggingface.co/datasets/Cainiao-AI/LaDe; code github.com/wenhaomin/LaDe (commit 9e5155a).
- Wen et al., *Survey on Service Route and Time Prediction in Instant Delivery*, arXiv:2309.01194.
- Uber DeeprETA (arXiv:2206.02127); Google Maps GNN ETA (arXiv:2108.11482); JD TransPDT (arXiv:2505.00375);
  DoorDash and Swiggy engineering blogs; Google TimesFM 3.0 (non-commercial license).
- Our evidence: `evidence/` (results JSON, Optuna trials, LaDe reproduction notes and re-scoring).
