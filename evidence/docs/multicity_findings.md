# Cross-city findings and data-quality boundaries

These are post-test diagnostics of the frozen, validation-selected `local_context` policy in `results/multicity_v1/`. No parameters, training rows, or deadline thresholds were changed in response to October/Jilin scores. Diagnostic slices overlap and are not alternative headline populations.

## What improved, and what did not

- Four city-specific models won the equal-city-weighted September validation comparison: macro MAE **101.86 minutes**, versus **103.64** for the shared context model and **104.64** for the shared acceptance-feature baseline.
- On the three first-evaluated known-city October tests, selected local-model macro MAE was **120.52**, versus **123.34** for the shared base model: a modest improvement, not a breakthrough.
- Shared context (**120.47**) and a 50/50 shared/local blend (**119.81**) were competitive or slightly better on those October cases. We did not change the selected policy after seeing that.
- The common-configuration Yantai model scored **95.24** MAE, slightly worse than the earlier Yantai-specific refinement (**94.94**). The older artifact remains available; this study is not a claim that every earlier result was surpassed.
- In the entirely withheld city, Jilin, the shared-model fallback scored **145.96-minute MAE** and **60.42% deadline coverage**. The local/blend policies use the same point fallback there, but their pooled residual calibration differs slightly, so their deadline coverages need not be identical.

**Conclusion:** location-specific training helps in this experiment, but the current model/deadline policy must not be treated as reliable in a new city without local validation and calibration. All five cities are historical Chinese courier operations; no claim extends to arbitrary geography or autonomous vehicles.

## Long-duration outcomes dominate some locations' errors

All these long-duration examples remain in the headline evaluation.

| City | Test cases | Duration >24 h | Share of cases | Share of total absolute prediction error from >24 h | Maximum recorded duration |
|---|---:|---:|---:|---:|---:|
| Yantai | 36,695 | 565 | 1.54% | 9.77% | 7.11 days |
| Shanghai | 376,329 | 1,108 | 0.29% | 10.79% | 16.30 days |
| Hangzhou | 398,606 | 2,340 | 0.59% | 23.87% | 47.48 days |
| Chongqing | 277,456 | 10,440 | **3.76%** | **48.03%** | **72.32 days** |
| Jilin | 1,089 | 0 | 0% | 0% | 0.59 days |

For diagnosis only, the <=24 h slice has MAE **51.16** minutes in Shanghai, **68.94** in Hangzhou, and **115.75** in Chongqing. These are **not** replacements for the headline errors. We cannot know a task belongs to that slice at acceptance without predicting it.

Long elapsed time could be genuine waiting, exception handling, scan/reporting semantics, or a data defect. This analysis does not establish which explanation is correct. Do not remove these records just because they hurt the score. A responsible next step is to inspect source timestamp definitions and exception policies, then predeclare any task-boundary changes on development data.

## Three ambiguous year-rollover records

The CSV timestamps omit years. The existing preprocessing uses a single-year parsing anchor, and its predeclared negative-duration rule excluded **three Chongqing rows**:

| Acceptance | Recorded completion |
|---|---|
| 10-31 10:57 | 01-11 19:20 |
| 10-31 12:14 | 01-13 14:16 |
| 10-22 17:54 | 01-19 12:56 |

These may be legitimate completions in the **following January**, not bad records. With no year in the CSV, the current parser treats January as preceding October. Consequently, the headline denominator is all **eligible** October cases under the documented parser/filter, not literally every raw October row.

**Unresolved:** confirm the completion-year convention and run a separately labeled next-year-rollover sensitivity analysis without changing the frozen models. It was not implemented in this study. The excluded cases must not be presented as proven corruption, and excluding potentially very long outcomes can understate tail error.

No source files were modified. Counts are recorded in `profile_cq.json` and the source checksums remain unchanged.

## Geographic failure is not just a long-outcome issue

Jilin's 1,089 test tasks span **23 acceptance days and 17 couriers**. All those courier IDs are unseen in model fitting because the entire city was withheld. Its median recorded duration is **234 minutes**, and none of its test tasks lasts over 24 hours. Thus its poor deadline coverage cannot be explained by the long-duration slice above alone.

The transfer test permits strictly prior Jilin event-log features as operational input, but **no Jilin target fitting or residual calibration**. It is not a no-history cold start. The source is a sampled operational archive, not a complete live dispatch roster.

Jilin has relatively few independent days/couriers, and it was deliberately selected as a small geographic stress holdout. It is evidence of a boundary, not an estimate of universal cross-city failure rates. Until local onboarding is performed, the numeric fallback should be considered diagnostic rather than an operational promise.

## Next bounded work

1. **Data owner:** resolve event semantics/year rollover and document what counts as customer receipt versus an exception/late scan. Keep valid rare events.
2. **Model owner:** use development-period geographic/temporal folds to compare local adaptation, quantile deadlines, and drift-aware recalibration. Do not keep choosing winners on these October results.
3. **Dispatcher/product owner:** define acceptable deadline coverage, maximum promise length, and a visible deferral/review policy for unsupported locations.
4. **Decision checkpoint:** require fresh evaluation data or a genuinely prospective replay before claiming deployment readiness. None of the current policies establishes 90% coverage for every location.
