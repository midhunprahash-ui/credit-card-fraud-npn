# Version 2 model training guide

## Purpose

Version 1 remains the fixed baseline. Version 2 tests whether stronger behavioral
features and more reliable time validation improve fraud ranking. All new files use a
`v2` folder or a `v2` filename, so previous notebooks and model outputs remain usable.

The primary model-selection metric is **validation PR-AUC**, because fraud is
rare. The chronological test partition is used once for final reporting and
must not drive further model selection. ROC-AUC is reported for Kaggle
comparison, while precision, recall, F1, Brier score, and top-alert metrics show
operational behavior. A Version 2 model is accepted only if its validation
result or operational trade-off justifies it; it is not accepted merely
because it is newer.

## What changed and why

### 1. Stable date-anchor features

The IEEE-CIS `D` columns represent anonymized time distances. Version 2 calculates
`transaction day - D value` for D1, D2, D4, D10, and D15. Repeated or similar anchors
can help the model recognize related activity even when raw time has moved forward.

### 2. Conservative identity proxies

The dataset has no direct customer ID. Version 2 creates proxy keys from fields such as
card, address, email, and normalized D1. These are hypotheses about related behavior,
not verified identities. They must never be displayed as a real customer identity.

### 3. Historical behavior

For each proxy, the pipeline adds useful information such as:

- how many times it appeared earlier;
- seconds since its previous transaction;
- earlier amount mean and standard deviation;
- difference, ratio, and z-score of the current amount versus earlier amounts; and
- how many distinct email, device, or amount-cent values appeared earlier.

This turns isolated transactions into behavior: a sudden amount change or rapid reuse
can be more informative than the raw field alone.

### 4. Strict leakage protection

Rows are sorted by `TransactionDT`, then `TransactionID`. Every cumulative statistic is
shifted so the current transaction and all future transactions are excluded. The
feature code never reads `isFraud`. Automated tests verify that:

- flipping every fraud label leaves all engineered inputs unchanged;
- editing a future transaction leaves every earlier engineered row unchanged; and
- the first event for a proxy has a prior count of zero.

Validation and test transactions can use attributes of earlier observed transactions.
That is valid in real time because those transactions have already occurred; their
fraud labels are never used.

### 5. Better model selection

LightGBM and CatBoost compare a small set of understandable configurations on three
expanding chronological folds. Candidate selection uses mean validation PR-AUC. The
latest 15% is kept as the final test period and is not used to choose features,
parameters, class weights, stopping iteration, threshold, or ensemble weight.

LightGBM now activates row subsampling with `subsample_freq=1`, and tests 48, 64, and
96 leaves with different regularization and class-weight strengths. CatBoost tests
depth and class-weight strength while monitoring unweighted PR-AUC.

Logistic Regression remains the explainable linear baseline. It uses balanced loss,
training-only median imputation, scaling, one-hot encoding for manageable categories,
and frequency encoding for high-cardinality categories.

The neural network uses embeddings for categorical fields, a configurable
384–192–96 network, up to 50 epochs, early stopping, learning-rate reduction, and a
validation-only comparison of balanced versus square-root-balanced positive weight.

### 6. Consensus score

After LightGBM and CatBoost finish, notebook 15 selects the best complete run of each
using validation PR-AUC. It searches one blend weight on validation predictions only,
freezes that weight, then evaluates the test period once. The blend is an additional
score; the four individual model outputs are still preserved.

## Exact workflow

1. Pull the latest `develop` branch.
2. Run `notebooks/lightning_ai/v2/10_v2_behavioral_data_preparation.ipynb` from top to bottom.
3. Confirm the final cell says that leakage and ordering checks passed.
4. Run the notebook assigned in `notebooks/lightning_ai/v2/README.md`.
5. Leave `FAST_RUN = False` for final training.
6. Confirm the final cell says `Reload check passed` and shows an archive path.
7. Send that `.tar.gz` archive to Midhun.
8. Compare Version 2 metrics with the frozen Version 1 results.
9. Run notebook 15 after complete LightGBM and CatBoost folders are together.

## Files inside a model result

Each complete run contains the model, its fitted preprocessor, `metrics.json`,
`threshold.json`, `training_config.json`, `feature_schema.json`, validation/test
predictions, an explanation or history file, and `manifest.json` with SHA-256 hashes.
The final notebook cell reloads the model and verifies sample probabilities before it
creates the archive.

The files are stored under `artifacts/v2/<model>/<UTC-run-id>/`. Data and artifacts are
Git-ignored because competition data and model binaries should not be committed.

## Deployment note

Batch evaluation calculates history chronologically. For a single new API request, the
repository saves `behavioral_reference.joblib`, a label-free snapshot of historical
counts and summaries. This is suitable for the hackathon demo. In a bank, the same
values should live in an online feature store and be updated only after each transaction
is scored. The frontend should send raw transaction fields; the backend must construct
the Version 2 features before invoking a Version 2 model.

## Interview explanation

“We kept Version 1 as an honest baseline. Version 2 adds customer-proxy and historical
behavior features inspired by the strongest IEEE-CIS solutions, but all aggregates are
past-only and target-free so they can exist at transaction time. We select settings on
expanding time validation with PR-AUC, keep the latest 15% untouched, save the complete
preprocessing contract with every model, and verify that every saved bundle reloads
before it is shared.”
