# How delivery-time models are built elsewhere, and what is open source

Reviewed on 2026-10-17. Sources were read directly (arXiv full text, company engineering blogs via the Internet Archive where sites blocked scripts). Claims below are limited to what those sources state.

## 1. The common industry pattern

| Company | What they predict | Model history | Notable design choices |
|---|---|---|---|
| **Uber** (DeepETA blog 2022; DeeprETA, arXiv 2206.02127) | Ride and delivery arrival times | Years of very large **XGBoost** ensembles, then a self-attention neural net once XGBoost stopped scaling | **Hybrid:** a routing engine computes a physics/map ETA; ML predicts only the **residual** correction. All inputs discretized and embedded. Asymmetric Huber loss (tunable robustness to outliers and early/late asymmetry). Periodic automatic retraining and validation. Tested 7 architectures. |
| **DoorDash** (blogs 2021, 2024) | Order placed to food delivered | **Tree-based models** first, then an MLP-gated mixture of experts (DeepNet + CrossNet + transformer) with multitask and probabilistic outputs | Reports ~20% relative accuracy gain from the deep model. Long-tail work (2021): **real-time features** (average delivery duration over past 20 min at store and sub-region), bucketed/target-encoded features, and a custom **asymmetric loss** encoding "late is X times worse than early". North-star metric: on-time % within a margin. 2-week shadow test, then randomized experiment; long-tail accuracy +10%. |
| **Swiggy** (blog 2023) | Delivery time shown at the cart | Moved from trees to a multi-input/multi-output neural net with entity embeddings | Predicts each **leg** separately and jointly (assignment, first mile, restaurant wait, last mile). Historical *and* near-real-time moving averages. Metrics: MAE, % within ±X ("BDC"), % egregiously late ("ED"). Embeddings cut MAE ~5%. |
| **Google Maps** (arXiv 2108.11482) | Road travel time | Graph neural network over road segments | Real-time and historical speeds per segment; production deployment cut bad ETAs 40%+ in some cities. Travel time only, not multi-stop courier work. |
| **JD Logistics** (TransPDT, arXiv 2505.00375) | Parcel delivery time for couriers with many pending packages | Transformer over the courier's **pending package set** and recent route, with **route prediction as an auxiliary task** | In their table XGBoost RMSE ~29.4 min vs TransPDT ~15.3 min (Beijing). Deployed for 2,000+ couriers. Predictions are made at steps along the route, not only at acceptance. |
| **Cainiao / Alibaba** (survey arXiv 2309.01194; LaDe) | Courier route and arrival time | Sequence/graph models (OSquare = LightGBM, DeepRoute, Graph2Route, DRL4Route, FDNET, RankETPA, M2G4RTP) | Field is "Route & Time Prediction": predict the courier's likely **stop order**, then times. Cainiao moved customers from a 2-hour window to minute-level ETA. |
| **Meituan** (UME, arXiv 2606.00979) | Checkout-page ETA across countries | Meta-learning multi-domain network | Targets **new markets with no history** (cold start), our Jilin problem. |

### Recipe that recurs across sources
1. **Start with gradient-boosted trees** (Uber, DoorDash; XGBoost is the standard industry baseline in JD's paper). Move to deep learning only at very large scale or when trees plateau.
2. **Decompose the problem**: route/travel physics plus ML correction (Uber), or separate legs (Swiggy, DoorDash), or route order then time (Cainiao, JD).
3. **Recent/real-time signals** for the area and the worker, not only static history (DoorDash, Swiggy, Google).
4. **Loss and metrics match the business**: asymmetric losses, quantiles, on-time within ±X, egregious-delay rate, not MAE alone.
5. **Uncertainty/probabilistic outputs** for promises (DoorDash; Uber supports quantiles).
6. **Operational discipline**: periodic retraining, shadow testing, and A/B tests before launch.

## 2. For our exact problem (one courier, many packages)
The survey's key point matches our own error analysis: when a worker holds many tasks, **arrival time depends on the unknown route order**. Specialized models predict that order from the pending package set and recent stops. The survey lists limitations: little public data, no road-network modelling, route errors propagating into time errors, and mostly point (non-probabilistic) predictions.

Published numbers from these papers are **not comparable** to ours: they predict at checkpoints along the route, with LaDe's benchmark restricting labels to 0-120 minutes; we predict at acceptance and keep multi-day outcomes.

## 3. What is open source

| Item | What it is | Usable for us? |
|---|---|---|
| **LaDe code** — github.com/wenhaomin/LaDe (~120 stars, **no license file**) | Research code for the LaDe dataset. Time prediction: LightGBM, KNN, MLP, speed baseline, FDNET, RankETPA, M2G4RTP. Route prediction: OSquare, DeepRoute, Graph2Route, DRL4Route, CP-Route, FDNET, M2G4RTP. | Closest match, same data. **Code only, no trained weights.** Uses the route-checkpoint task, not ours. No license means reuse rights are unclear. |
| **IGT** — github.com/enoche/IGT-WSDM23 (no license file) | Inductive graph transformer for e-commerce delivery time | Different setting (order-to-door, merchant/address graph); private data. |
| **DRL4Route** — github.com/maoxiaowei97/DRL4Route (no license file) | Reinforcement-learning route prediction | Route order only. |
| **Amazon Last Mile Routing Challenge data** (CC BY-NC 4.0) | 9,184 real 2018 US routes with stop sequences | Route data, useful for route-order research; not our dataset. |
| Uber, DoorDash, Swiggy, Google, JD, Meituan production models | — | **Not released.** Papers/blogs only. |
| Hugging Face / GitHub "delivery time" models | Student/Kaggle projects (0 downloads; small food-delivery datasets) | No credible pretrained delivery-ETA model found. |

**Conclusion:** there is no ready-made, pretrained delivery-ETA model to download. Every company trains its own on its own operations data. Our LightGBM-plus-history approach is the standard starting point; the LaDe repository is the only relevant open code, and it targets a different prediction moment.

## 4. Implications for this project
Already aligned with industry: gradient-boosted trees, chronological evaluation, recent courier-history features, separate deadline buffer, and evidence that **periodic retraining** matters.

Gaps the sources point to, cheapest first:
1. **Area-level recent signals** (e.g., average duration of deliveries recently completed in the same AOI/region), à la DoorDash's 20-minute store/sub-region features. Must use only outcomes finished before the query.
2. **Route-position proxies** from the courier's open packages (e.g., this destination's distance rank among pending packages), a lightweight step toward route-and-time prediction.
3. **Business-aligned loss and metrics**: asymmetric loss or quantile outputs; report on-time within ±X and an egregious-delay rate alongside MAE.
4. **Full route-and-time models** (RankETPA, M2G4RTP via the LaDe code): higher effort, a different task framing, and unresolved code licensing.

## Sources
- Wen et al., *A Survey on Service Route and Time Prediction in Instant Delivery*, arXiv:2309.01194.
- Hu et al., *DeeprETA: An ETA Post-processing System at Scale*, arXiv:2206.02127; Uber blog "DeepETA: How Uber Predicts Arrival Times Using Deep Learning" (Feb 2022).
- Derrow-Pinion et al., *ETA Prediction with Graph Neural Networks in Google Maps*, CIKM 2021, arXiv:2108.11482.
- Yi et al., *Learning to Estimate Package Delivery Time in Mixed Imbalanced Delivery and Pickup Logistics Services* (TransPDT, JD Logistics), SIGSPATIAL 2024, arXiv:2505.00375.
- Wang et al., *UME: A Unified Meta-Generalization Framework for Cross-Domain ETA* (Meituan), arXiv:2606.00979.
- Zhou et al., *Inductive Graph Transformer for Delivery Time Estimation*, WSDM 2023, arXiv:2211.02863.
- Wu et al., *LaDe: The First Comprehensive Last-mile Delivery Dataset from Industry*, arXiv:2306.10675.
- DoorDash Engineering: "Improving ETA Prediction Accuracy for Long-tail Events" (Apr 2021); "Precision in Motion: Deep learning for smarter ETA predictions" (Oct 2024).
- Swiggy Bytes: "Predicting Food Delivery Time at Cart" (Aug 2023).
- AWS Open Data: 2021 Amazon Last Mile Routing Research Challenge dataset.

## 5. Route-and-time models on LaDe: results and a code review (added 2026-10-19)

### Published results (LaDe paper v3, Tables 3-4; PAPN 2026; MRGRP 2025)
| Task | Best reported | Notes |
|---|---|---|
| Route order, next-3 hit rate (HR@3) | DRL4Route 72-73%; PAPN (2026) ~72%; Graph2Route/M2G4RTP ~72%; **LightGBM 70-71%** | Deep models beat LightGBM by only ~1-2 points; the field has plateaued. |
| Route order, Kendall correlation | ~0.55-0.57 (LightGBM ~0.53-0.55) | |
| Mid-route ETA, LaDe | M2G4RTP: Shanghai MAE 8.2 min, ACC@20 91%; Yantai 17.2 / 69%; Chongqing 18.0 / 66%. Others: 15.8-24 min | M2G4RTP's Shanghai result is ~2x better than every other model and than its own other-city results. |
| Food-delivery route (MRGRP, Meituan) | "route accuracy 0.819" online | Different data and metric; not LaDe. |

### Code review of the public LaDe time-prediction pipeline (commit 9e5155a)
Reading `time_prediction/data/preprocess_delivery.py`, `dataset_delivery.py`, and `algorithm/m2g4rtp_delivery/m2g4rtp.py`:
1. **Input sets filtered by future outcomes.** A pending package is kept in a query only if its *future* completion falls 0-120 minutes after the query time. The model's input therefore reveals which packages will finish within two hours. This applies to every model in the benchmark.
2. **Test set restricted to light courier-days.** In test mode, a whole courier-day is discarded if any pending task index reaches the 25-task cap, favouring days with fewer packages.
3. **M2G4RTP's area (AOI) features are built in the true future visiting order.** The AOI list is assembled by walking pending packages in actual delivery order, records the run length of consecutive deliveries in each AOI, and stops at the first revisit. The list is shuffled afterwards, but run lengths and the truncated AOI set still encode the future route. This plausibly explains its outlier Shanghai score; it would need a controlled rerun to confirm.
4. **Courier statistics use the whole dataset**, test period included (average speed, distance per day, work days), and courier/row filters use full-period outcomes.

These are observations from code reading, not a rerun. They mean the published ETA numbers are not achievable targets for an honest, forward-looking system, and are not comparable to our acceptance-time task.
