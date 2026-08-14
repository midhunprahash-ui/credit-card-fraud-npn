# Class imbalance and data leakage guide

This guide explains two of the most important decisions in the fraud-detection
pipeline:

1. how the four models learn when fraud is rare; and
2. how we stop labels and future information from leaking into training.

The explanations below describe the implemented notebooks and source code, not
only a proposed design.

## 1. The problem in simple terms

Only about 3.5% of the labelled transactions are fraudulent. Roughly 96.5% are
normal. A useless model could predict `not fraud` for every row and still obtain
about 96.5% accuracy.

That creates two separate risks:

- **Class imbalance:** the model may pay too little attention to the rare fraud
  examples.
- **Data leakage:** the model may appear unusually strong because it accidentally
  learned from a fraud label or from information that belongs to the future.

Our pipeline treats these as different problems. Class weights address the first.
A chronological split and training-only preprocessing address the second.

## 2. End-to-end safety boundary

```text
Transaction table + identity table
              │
              ▼
Left join on TransactionID
              │
              ▼
Current-row features only
              │
              ▼
Chronological 70% / 15% / 15% split
              │
              ├── Training: fit mappings, class weights and model
              ├── Validation: early stopping and threshold selection
              └── Test: final reporting after decisions are frozen
```

The full split contains:

| Partition | Rows | Time position | Allowed purpose |
| --- | ---: | --- | --- |
| Training | 413,378 | Earliest 70% | Learn preprocessing and model parameters |
| Validation | 88,581 | Next 15% | Early stopping, model comparison and threshold selection |
| Test | 88,581 | Latest 15% | Final reporting only |

The split is shared by all four models so their results are comparable.

## 3. How class imbalance is handled

### 3.1 Training-period class ratio

The imbalance weight is calculated from `y_train` only:

```python
negative, positive = np.bincount(y_train)
fraud_weight = negative / positive
```

For the full training partition this value is approximately `27.43`. In simple
terms, a fraud error receives about 27 times the training importance of a normal
transaction error.

Validation and test labels are never used to calculate this weight.

### 3.2 Treatment in each model

| Model | Implemented setting | Meaning |
| --- | --- | --- |
| Logistic Regression | `class_weight="balanced"` | Scikit-learn calculates inverse-frequency weights from the training labels. |
| LightGBM | `scale_pos_weight=negative/positive` | Fraud gradients receive greater weight during tree construction. |
| CatBoost | `class_weights=[1.0, fraud_weight]` | Normal rows have weight 1 and fraud rows have the larger training-only weight. |
| Neural network | `BCEWithLogitsLoss(pos_weight=fraud_weight)` | Missing a fraud example contributes more to the neural-network loss. |

All four methods change the learning objective. They do not copy rows or create
fake transactions.

### 3.3 Why SMOTE is not used

SMOTE creates artificial minority-class rows between existing fraud examples.
We do not use it in the benchmark because this dataset mixes transaction amounts,
time, cards, addresses, emails, devices and anonymized identity codes. An
interpolated row could represent a combination that never occurs in a real
checkout.

Weighted training is preferable here because it:

- preserves the real chronological population;
- keeps every original transaction exactly once;
- avoids unrealistic categorical combinations;
- avoids increasing memory use on an already large dataset; and
- is supported directly by all four selected algorithms.

SMOTE is not universally wrong. It is simply not the safest first choice for
this mixed-type, time-ordered dataset.

### 3.4 Why accuracy is not the headline metric

The primary comparison metric is **PR-AUC**, also called Average Precision. It
measures how well the model ranks rare fraud cases without being dominated by
the much larger normal class.

The reports also include:

- precision: of the alerts raised, how many are fraud;
- recall: of all fraud cases, how many were caught;
- F1: a balance of precision and recall;
- ROC-AUC: overall ranking quality;
- Brier score: probability/risk-score error;
- confusion matrix; and
- fraud captured when analysts review the top 1%, 5% or 10% of transactions.

### 3.5 Operational threshold

Training produces a continuous score. Fraud/non-fraud classification requires a
threshold. The threshold is selected on validation data only:

```text
maximize recall while validation precision is at least 10%
```

The selected value is stored in `threshold.json` and applied unchanged to the
test set and later API requests.

A threshold below `0.5` is not automatically an error. Class weighting changes
the score distribution. Until a separate calibration step is added, the UI
should call model outputs **fraud risk scores**, not guaranteed real-world fraud
probabilities.

## 4. What data leakage means here

Data leakage is any information used during training that would not be available
when a new transaction is scored in production.

| Example | Safe? | Reason |
| --- | --- | --- |
| Current transaction amount | Yes | It exists when the transaction arrives. |
| Current device/browser identity | Yes | It belongs to the same transaction. |
| `isFraud` used as a model input | No | This is the answer the model must predict. |
| Frequency calculated using future test rows | No | The past model would be learning future population information. |
| Median calculated using all rows | No | Validation/test distributions influence training. |
| Threshold selected using test labels | No | The final holdout becomes tuning data. |
| Row-level amount log calculated before splitting | Yes | It uses only that row and learns no population mapping. |

## 5. Leakage controls implemented in the pipeline

### 5.1 The left join is label-safe

`train_transaction` is left-joined to `train_identity` on `TransactionID`.
Identity rows describe the same checkout event and do not contain the fraud
target. A left join preserves all labelled transactions, including rows with no
matching identity record.

After the join:

- `isFraud` is kept only as the target;
- `TransactionID` is kept for tracing predictions but removed from model input;
- missing identity values remain missing instead of dropping the transaction.

The join itself does not create historical or future information.

### 5.2 Only row-level shared features are created before the split

The shared feature function excludes `isFraud` and `TransactionID` from its
source columns. It creates features such as:

- log transaction amount and amount cents;
- missing-value counts;
- identity-availability count;
- relative day, week and hour phase; and
- card, address and email combinations from the current row.

These transformations are deterministic for one row. They do not calculate a
median, frequency, fraud rate or future history. Therefore, applying them before
the split is safe and makes the same function reusable by the API.

### 5.3 Chronological split instead of random split

Rows are sorted by `TransactionDT`, with `TransactionID` used only to provide a
stable order for ties. The code verifies:

```python
train["TransactionDT"].max() <= validation["TransactionDT"].min()
validation["TransactionDT"].max() <= test["TransactionDT"].min()
```

This simulates the real deployment direction: learn from earlier transactions
and predict later transactions. A random split could place similar future fraud
patterns on both sides and make results overly optimistic.

`TransactionDT` itself may remain a model feature because the current
transaction's relative time is available at scoring time. It does not reveal the
future.

### 5.4 Column removal is learned from training only

All-null and constant columns are identified using the training partition.
Validation and test rows do not determine the usable feature list.

### 5.5 Every learned preprocessor is fitted on `X_train`

The correct pattern is:

```python
preprocessor.fit(X_train)
X_train_model = preprocessor.transform(X_train)
X_validation_model = preprocessor.transform(X_validation)
X_test_model = preprocessor.transform(X_test)
```

The following objects are learned from training only:

- numeric medians, means and standard deviations;
- missing-value imputation values;
- one-hot category levels;
- rare-category decisions;
- high-cardinality frequency maps;
- LightGBM categorical levels;
- neural-network vocabularies;
- class weights; and
- model parameters.

The fitted preprocessor is saved beside the model so production uses the same
rules. The backend must load this saved object; it must not fit a new one from an
API request.

### 5.6 Unknown future categories are explicit

Categories seen only after the training period do not silently become training
categories:

- rare known training values become `OTHER`;
- previously unseen future values become `UNKNOWN` or frequency `0`;
- missing categorical values become `MISSING`;
- neural categories use reserved embedding IDs; and
- CatBoost receives a stable categorical string representation.

This is both a leakage control and a production-stability control.

### 5.7 No manual target encoding

The pipeline does not manually calculate values such as `fraud rate per card` or
`fraud rate per device`. A naive calculation of those features can leak each
row's label or future labels.

CatBoost performs its own ordered categorical processing, designed to reduce the
target leakage associated with ordinary target encoding. We do not add a second
manual target-encoding layer.

### 5.8 Validation and test have different jobs

Validation labels may be used for:

- LightGBM/CatBoost/neural early stopping;
- comparing candidate runs using validation PR-AUC; and
- selecting the operating threshold.

Test labels may be used only after those choices are frozen, to report the final
generalization result. A model must never be accepted because its test PR-AUC is
higher while its validation evidence is worse.

This rule also applies to Logistic Regression: convergence status and validation
performance determine whether a rerun is accepted. Test performance is reported,
not optimized.

## 6. Model-by-model leakage summary

| Model | Training-only representation | Label protection |
| --- | --- | --- |
| Logistic Regression | Median, missing flags, scaling, sparse one-hot and frequency maps | The complete preprocessing pipeline is fitted with training rows only. |
| LightGBM | Native low-cardinality levels and training-only high-cardinality frequencies | Validation is used for early stopping; the saved training preprocessor transforms later rows. |
| CatBoost | Numeric values plus categorical strings | Ordered categorical statistics reduce target-encoding leakage; no manual target encoding is added. |
| Neural network | Training medians/scales plus training vocabularies and embeddings | Validation chooses the best epoch; test rows never update weights or vocabularies. |

## 7. Honest limitations and production improvements

The current design is appropriate for the hackathon, but the team should be able
to explain these limitations:

1. The same validation period is used for early stopping and threshold selection.
   The separate test period measures the final result. A stricter production
   system could add a separate calibration/threshold period.
2. Weighted training improves fraud attention but can reduce probability
   calibration. Scores should be labelled as risk scores until calibration is
   measured and implemented.
3. Repeatedly tuning after looking at test results would contaminate the holdout.
   Once the four bundles are frozen, changes must be judged on validation or a
   newly defined future holdout.
4. Future historical features—such as card velocity in the previous hour—must be
   calculated with event-time windows containing only earlier transactions.

A stricter future lifecycle can use:

```text
Training → fit parameters
Validation → select model and hyperparameters
Calibration → calibrate score and select threshold
Test → one final untouched report
```

## 8. Teammate review checklist

Before accepting any training run, verify:

- [ ] `FAST_RUN` is `False`.
- [ ] Training, validation and test row counts match the shared partitions.
- [ ] `isFraud` and `TransactionID` are excluded from model inputs.
- [ ] The preprocessor is fitted only on `X_train`.
- [ ] Class weight is calculated from `y_train` only.
- [ ] Early stopping uses validation, never test.
- [ ] The threshold is selected on validation and reused unchanged on test.
- [ ] Model selection uses validation PR-AUC, not test PR-AUC.
- [ ] The model and preprocessor reload test passes.
- [ ] No SMOTE or full-dataset frequency/median calculation was added silently.

## 9. Interview-ready answer

> Fraud is only about 3.5% of the data, so accuracy would be misleading. We kept
> the real transaction population and used training-only class weights: balanced
> weights for Logistic Regression, `scale_pos_weight` for LightGBM, class weights
> for CatBoost and positive loss weight for the neural network. We evaluate with
> PR-AUC, precision and recall, and select the alert threshold on validation.
>
> To prevent leakage, we left-join identity signals belonging to the same
> transaction, create only current-row shared features, and split chronologically
> into earliest 70%, next 15% and latest 15%. Every median, scaler, category
> vocabulary, frequency map, class weight and model is fitted on the earliest
> training period only. Validation controls early stopping and threshold selection;
> the latest holdout is used only for the final report.

## 10. Implementation references

- Shared row features and chronological split:
  [`src/fraud_pipeline/common.py`](../src/fraud_pipeline/common.py)
- Training-only preprocessors:
  [`src/fraud_pipeline/preprocessing.py`](../src/fraud_pipeline/preprocessing.py)
- Threshold and evaluation functions:
  [`src/fraud_pipeline/evaluation.py`](../src/fraud_pipeline/evaluation.py)
- Shared split notebook:
  [`notebooks/lightning_ai/00_shared_data_preparation.ipynb`](../notebooks/lightning_ai/00_shared_data_preparation.ipynb)
- Four training notebooks:
  [`notebooks/lightning_ai/`](../notebooks/lightning_ai/)
