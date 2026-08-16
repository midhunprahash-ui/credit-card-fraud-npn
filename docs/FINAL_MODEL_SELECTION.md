# Final V1/V2 model selection

This document freezes the eight standalone runs approved for application
integration: four model approaches in V1 and the same four in V2. Selection
uses validation PR-AUC; the chronological test period is retained for final
reporting and is not used for further tuning.

## Approved V1 runs

| Rank | Model | Approved run | Validation PR-AUC | Test PR-AUC | Test ROC-AUC |
| ---: | --- | --- | ---: | ---: | ---: |
| 1 | LightGBM.V1 | `20260814T050814Z` | 0.630256 | 0.539716 | 0.893617 |
| 2 | CatBoost.V1 | `20260814T043639Z` | 0.599982 | 0.532720 | 0.911352 |
| 3 | NeuralNetwork.V1 | `20260814T051404Z` | 0.516257 | 0.413006 | 0.859204 |
| 4 | LogisticRegression.V1 | `20260814T044445Z` | 0.399714 | 0.170222 | 0.831853 |

LightGBM.V1 is the V1 champion because it has the highest V1 validation PR-AUC.

## Approved V2 runs

| Rank | Model | Approved run | Validation PR-AUC | Test PR-AUC | Threshold |
| ---: | --- | --- | ---: | ---: | ---: |
| 1 | CatBoost.V2 | `20260815T121042Z` | 0.725072 | 0.607110 | 0.019238 |
| 2 | LightGBM.V2 | `20260815T061730Z` | 0.653215 | 0.570442 | 0.000190 |
| 3 | NeuralNetwork.V2 | `20260815T130503Z` | 0.517591 | 0.391322 | 0.001054 |
| 4 | LogisticRegression.V2 | `20260815T133526Z` | 0.397775 | 0.171740 | 0.484119 |

CatBoost.V2 is the V2 and overall champion because it has the highest validation
PR-AUC across the approved runs. The optional LightGBM/CatBoost consensus is
deferred and is not one of the eight application pipelines.

## V1 operating points

Each threshold was chosen on validation by maximizing recall while maintaining
at least 10% validation precision. It is then reused unchanged on the test set.

| Model | Threshold | Validation recall | Test precision | Test recall |
| --- | ---: | ---: | ---: | ---: |
| LightGBM.V1 | 0.003483 | 0.904339 | 0.092749 | 0.878365 |
| CatBoost.V1 | 0.155765 | 0.935897 | 0.094963 | 0.918586 |
| NeuralNetwork.V1 | 0.149067 | 0.850099 | 0.085767 | 0.842037 |
| LogisticRegression.V1 | 0.498292 | 0.776792 | 0.081763 | 0.823548 |

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

V2 adds leakage-safe behavioral features. CatBoost.V2 gains the strongest
validated rare-fraud ranking and replaces LightGBM.V1 as the overall champion.
This does not hide any other pipeline: users may select V1, V2, or both and run
any subset of the eight models independently.

Because class weighting changes score distributions, the UI should label these
values as **fraud risk scores** rather than guaranteed calibrated probabilities.
Raw scores from different models should not be directly averaged unless an
ensemble is fitted and validated using validation predictions only.

## Bundle validation completed

For every selected V1 run we checked:

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

The same artifact, schema, threshold, score-range, V1/V2 separation, and common
raw-transaction checks were then applied to all eight selected pipelines through
the golden-prediction verification gate. See
[MODEL_VERIFICATION_GATE.md](MODEL_VERIFICATION_GATE.md).

## Reproducibility and leakage rule

All models use the same earliest-70% training, next-15% validation and latest-15%
test partitions. Preprocessors and class weights are learned from training only.
Validation chooses the run and threshold. Test metrics are for reporting and
must not drive additional tuning.

See [`CLASS_IMBALANCE_AND_DATA_LEAKAGE.md`](CLASS_IMBALANCE_AND_DATA_LEAKAGE.md)
for the full reasoning and teammate checklist.

## Application rule

One normalized raw transaction may be sent to any selected subset of the eight
saved pipelines. Each selected model applies its own versioned features,
preprocessor, model, and threshold. The API returns separate scores, decisions,
thresholds, and versions. CatBoost.V2 is marked as the overall champion, but no
model output is silently replaced by an average.

Machine-readable run IDs are in
[`../config/model_registry.json`](../config/model_registry.json) and
[`../config/model_registry_v2.json`](../config/model_registry_v2.json).
