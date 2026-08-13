# Feature Engineering Guide

This guide explains, in simple terms, how raw IEEE-CIS transaction data is turned into useful model inputs. It describes the features **currently created in Notebook 01** and clearly separates them from suggested future improvements.

## 1. What is feature engineering?

Feature engineering means creating clearer and more useful signals from raw data so a machine-learning model can recognize suspicious behavior.

For example, a raw field such as `TransactionAmt` is useful, but a model may learn more easily from both:

```text
TransactionAmt       = 5,000
log_TransactionAmt   = log(1 + 5,000)
```

The logarithmic version reduces the influence of a few extremely large payments while retaining the difference between small and large payments.

The key principle is: **use only information that would have been available when the transaction occurred.** Do not use fraud labels, future transactions, or validation/test data to build training features.

## 2. Shared pipeline: the same business signals for every model

All three models use the same starting dataset, base cleaning, engineered features, and chronological split.

```text
Transaction table + identity table
              ↓
Left join on TransactionID
              ↓
Shared engineered features
              ↓
Chronological 70% / 15% / 15% split
              ↓
Model-specific formatting only
      ├── Logistic Regression
      ├── LightGBM
      └── CatBoost
```

This makes the model comparison fair: each model receives the same underlying business information. Only the final representation changes because the algorithms accept different data formats.

## 3. Step 1 — merge the two source tables

The dataset has two related files:

- `train_transaction.csv`: one row per payment, with amount, card-related fields, emails, addresses, and anonymized variables.
- `train_identity.csv`: device, browser, operating system, and other identity signals for only some payments.

They are joined on `TransactionID` with a **left join**:

```python
train = train_transaction.merge(train_identity, on="TransactionID", how="left")
```

A left join preserves all 590,540 transactions, then fills identity fields where they exist. An inner join would throw away the roughly 75.6% of transactions that have no identity record.

### `has_identity`

```python
has_identity = 1  # an identity-table row exists
has_identity = 0  # no identity-table row exists
```

This is deliberately created because the absence of identity data can be informative. In this dataset, transactions with identity data and transactions without it have different fraud rates.

## 4. Step 2 — common engineered features currently implemented

These are defined in `add_common_features()` in `notebooks/01_colab_data_preparation.ipynb`.

| Feature | Raw columns used | How it is created | Why it helps |
| --- | --- | --- | --- |
| `log_TransactionAmt` | `TransactionAmt` | `log1p(TransactionAmt)` | Large amounts are heavily skewed; the log version makes their scale easier for models to learn. |
| `transaction_day` | `TransactionDT` | Relative seconds ÷ 86,400 | Captures change in behavior over the 182-day period. |
| `transaction_week` | `TransactionDT` | Relative seconds ÷ 604,800 | Captures broader weekly patterns. |
| `transaction_hour` | `TransactionDT` | Relative hour modulo 24 | Certain hours can have different fraud behavior. |
| `is_weekend` | `transaction_day` | Day index mapped to a weekend flag | Weekend shopping behavior may differ from weekday behavior. |
| `has_identity` | Join result | 1 if identity row exists, otherwise 0 | Preserves useful information about identity-data availability. |
| `<column>_missing` | Selected important columns | 1 when the source field is missing, otherwise 0 | Missing information can be a risk signal rather than just a data problem. |
| `card1_card2` | `card1`, `card2` | String concatenation, with `MISSING` where needed | Lets the model see a card combination rather than two independent pieces. |
| `addr1_addr2` | `addr1`, `addr2` | String concatenation, with `MISSING` where needed | Represents a combined address pattern. |
| `email_pair` | `P_emaildomain`, `R_emaildomain` | String concatenation, with `MISSING` where needed | Captures the sender/receiver email-domain relationship. |

### Missingness flags currently added

The current notebook adds missingness indicators for these fields when present:

```text
TransactionAmt, dist1, dist2, DeviceInfo, id_30, id_31
```

For example:

```text
DeviceInfo = "SM-G950F"       → DeviceInfo_missing = 0
DeviceInfo = missing           → DeviceInfo_missing = 1
```

This lets a model distinguish a true value from a value that is absent.

## 5. Cleaning before modelling

The preparation notebook applies light, safe cleaning that is common to every model:

1. **Keep all rows after the left join.** Missing identity values are retained.
2. **Remove all-empty features.** A column with no values cannot help a model.
3. **Remove constant features.** A column with only one value cannot separate fraud from non-fraud.
4. **Keep the target separate.** `isFraud` is used only as the training label, never as a model input.
5. **Exclude `TransactionID` from model features.** It is a row identifier, not a meaningful business signal for deployment.
6. **Sort by `TransactionDT`.** The first 70% is training data, the next 15% validation data, and the final 15% is the untouched test set.

The notebook does **not** globally fill every missing number with a median. That is intentional: LightGBM and CatBoost can work with numeric missing values, and the missingness flags preserve the fact that a value was absent. Logistic Regression performs median imputation inside its own pipeline because that model cannot accept missing values.

## 6. High-cardinality categorical features

A categorical field has a limited set of labels, such as:

```text
ProductCD: W, C, H, R, S
```

A **high-cardinality** categorical feature has many different labels. Examples in this project include device/browser fields, email domains, and engineered combinations such as `card1_card2`. Direct one-hot encoding would create a huge number of sparse columns, slow training, and make overfitting more likely.

### Current approach: model-specific representation

| Model | Categorical treatment | Why |
| --- | --- | --- |
| Logistic Regression | Training-only frequency encoding | Logistic Regression needs numeric input. Frequency encoding keeps the column compact. |
| LightGBM | Training-only frequency encoding | This keeps memory use manageable and avoids thousands of one-hot columns. |
| CatBoost | Native categorical processing for text/object columns | CatBoost learns from category labels directly and is designed for this situation. |

### Frequency encoding, in plain terms

Frequency encoding replaces a label with how often it appears in the **training split**.

```text
Training values for DeviceInfo:
"Windows"       occurs in 12.0% of training rows → 0.120
"Rare device X" occurs in 0.02% of training rows → 0.0002
```

The model can then recognize common and rare patterns without creating one column per device. An unseen validation or test category becomes `0`.

### Why “training-only” matters

The frequency map is calculated from training rows only, then applied to validation/test rows.

```text
Training split → build frequency map
Validation/test → look up values in that map
```

If we calculate frequencies using all data first, validation/test information leaks into training. The reported model score would look better than real-world performance.

### Important implementation detail: numeric identifier-like fields

Fields such as `card1`, `card2`, `addr1`, and `addr2` are numerically typed in the Kaggle CSV. The current notebooks leave their original numeric columns as numeric values. Their engineered string combinations (`card1_card2`, `addr1_addr2`) are treated as categorical.

For the next feature-engineering iteration, we should also create **training-only frequency features** for individual identifier-like numeric columns (for example `card1_freq`, `addr1_freq`). This is planned work, not something the current notebooks already claim to do.

## 7. How the three pipelines differ

The business features are shared. The preprocessing applied immediately before each model differs:

| Step | Logistic Regression | LightGBM | CatBoost |
| --- | --- | --- | --- |
| Numeric missing values | Median imputation | Left as missing | Left as missing |
| Categorical missing values | Replaced with `MISSING` before frequency encoding | Replaced with `MISSING` before frequency encoding | Replaced with `MISSING` strings |
| Categorical features | Frequency-encoded to numeric values | Frequency-encoded to numeric values | Text/object categoricals passed directly to CatBoost |
| Numeric scaling | StandardScaler | Not required | Not required |
| Imbalance handling | `class_weight="balanced"` | `scale_pos_weight` | `class_weights` |

### Logistic Regression

Logistic Regression expects a complete numeric matrix. Therefore it needs the most preprocessing:

```text
categorical label → training-only frequency number
missing numeric value → median
numeric feature → standardized scale
```

It is useful as an interpretable baseline, not expected to be the final winner for nonlinear fraud patterns.

### LightGBM

LightGBM is a boosted decision-tree model. It can handle numeric missing values and does not require scaling. In the current comparison, categorical labels are frequency-encoded to compact numeric columns.

### CatBoost

CatBoost is also a boosted decision-tree model but has native support for categorical text/object columns. We fill categorical nulls with `MISSING`, keep category labels as strings, and tell CatBoost which columns are categorical. This is why it is the simplest strong candidate for the final model.

## 8. Features we should add after the first benchmark

The current set is a sound, leakage-safe baseline. After recording initial metrics, add and test these features one group at a time:

1. **Individual frequency features:** frequency of `card1`, `card2`, `card3`, `card5`, `addr1`, `addr2`, `DeviceInfo`, and email domains.
2. **Rare-category grouping:** replace labels appearing fewer than a chosen training-only threshold with `OTHER`.
3. **Amount behavior features:** integer/decimal parts of the amount and transaction-amount bands.
4. **Historical behavior:** prior transaction count, prior mean amount, and time since prior activity for the same card/device/address.
5. **Cross features:** card + email domain, device + browser, card + address.

Every new group must be validated on the same chronological validation split. Keep it only if it improves PR-AUC/ROC-AUC or the review-queue business metric.

## 9. Leakage checklist

Before accepting a feature, ask:

- Is this value available at the time the transaction is scored?
- Is the mapping/aggregate fitted only on earlier training data?
- Does it accidentally contain `isFraud` or a post-transaction decision?
- Is it applied identically in training, validation, test, API, and dashboard scoring?

If any answer is no, do not use the feature.

## 10. One-minute presentation explanation

> “We merge each transaction with any available device and identity information using a left join, so we retain all transactions. We create amount, time, missingness, identity-availability, and card/address/email combination signals. The same engineered features are used for every model. Logistic Regression and LightGBM receive compact frequency-encoded categoricals, while CatBoost receives categorical labels directly. Every transformation is fitted on earlier training data only, which prevents leakage.”
