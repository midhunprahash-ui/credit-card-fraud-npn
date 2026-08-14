# Final four-model selection

This document freezes the four full-data model runs approved for application
integration. Selection uses validation PR-AUC; the chronological test period is
retained for final reporting.

## Approved runs

| Rank | Model | Approved run | Validation PR-AUC | Test PR-AUC | Test ROC-AUC |
| ---: | --- | --- | ---: | ---: | ---: |
| 1 | LightGBM | `20260814T050814Z` | 0.630256 | 0.539716 | 0.893617 |
| 2 | CatBoost | `20260814T043639Z` | 0.599982 | 0.532720 | 0.911352 |
| 3 | Neural network | `20260814T051404Z` | 0.516257 | 0.413006 | 0.859204 |
| 4 | Logistic Regression | `20260814T044445Z` | 0.399714 | 0.170222 | 0.831853 |

LightGBM is the champion because it has the highest validation PR-AUC, our
primary rare-fraud ranking metric. The application will still load and display
all four outputs independently.

## Operating points

Each threshold was chosen on validation by maximizing recall while maintaining
at least 10% validation precision. It is then reused unchanged on the test set.

| Model | Threshold | Validation recall | Test precision | Test recall |
| --- | ---: | ---: | ---: | ---: |
| LightGBM | 0.003483 | 0.904339 | 0.092749 | 0.878365 |
| CatBoost | 0.155765 | 0.935897 | 0.094963 | 0.918586 |
| Neural network | 0.149067 | 0.850099 | 0.085767 | 0.842037 |
| Logistic Regression | 0.498292 | 0.776792 | 0.081763 | 0.823548 |

Thresholds are model-specific and must be loaded from each run's
`threshold.json`. They must not be replaced with a common `0.5` threshold.

## What the results mean

- **LightGBM:** strongest validation PR-AUC and therefore the deployment
  champion. It provides the best validated rare-fraud ranking in this benchmark.
- **CatBoost:** very close PR-AUC and the strongest test recall/ROC-AUC. It is a
  strong mixed-type model and a useful independent opinion beside LightGBM.
- **Neural network:** valid embedding-based deep-learning comparison. It is
  weaker than the boosted trees but stronger than the linear baseline.
- **Logistic Regression:** transparent baseline. The finalized rerun used
  `max_iter=600`, `tol=0.001`, and converged at iteration 578. Its lower nonlinear
  performance is expected and demonstrates why the tree models are needed.

Because class weighting changes score distributions, the UI should label these
values as **fraud risk scores** rather than guaranteed calibrated probabilities.
Raw scores from different models should not be directly averaged unless an
ensemble is fitted and validated using validation predictions only.

## Bundle validation completed

For every selected run we checked:

- `FAST_RUN` is `False`;
- model, preprocessor, schema, metrics, threshold and prediction files exist;
- model/preprocessor reload succeeds;
- validation and test prediction files contain 88,581 unique transactions;
- probabilities contain no missing or out-of-range values;
- saved PR-AUC/ROC-AUC match values recomputed from prediction files; and
- manifest sizes and SHA-256 checksums match the packaged files.

The Logistic Regression delivery exposed a manifest self-reference created by
rerunning its packaging cell. The manifest builder now always excludes
`manifest.json` itself, and the extracted deployment bundle was regenerated.

## Reproducibility and leakage rule

All models use the same earliest-70% training, next-15% validation and latest-15%
test partitions. Preprocessors and class weights are learned from training only.
Validation chooses the run and threshold. Test metrics are for reporting and
must not drive additional tuning.

See [`CLASS_IMBALANCE_AND_DATA_LEAKAGE.md`](CLASS_IMBALANCE_AND_DATA_LEAKAGE.md)
for the full reasoning and teammate checklist.

## Application rule

One normalized transaction is sent to all four saved preprocessing/model
pipelines. The API returns four separate scores, decisions, thresholds and model
versions. LightGBM is clearly marked as the champion, but no model output is
silently replaced by an average.

Machine-readable run IDs are in
[`../config/model_registry.json`](../config/model_registry.json).
