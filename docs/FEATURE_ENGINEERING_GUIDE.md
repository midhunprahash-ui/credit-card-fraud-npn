# Feature engineering guide

This guide explains what the finalized Lightning AI pipeline does, why each
decision is made, and how the same fraud evidence is represented for four
different algorithms.

## 1. Shared data population

```text
train_transaction
        LEFT JOIN train_identity ON TransactionID
```

The left join retains all 590,540 labelled transactions. Only about 24.42% have
an identity row. An inner join would remove most of the training population and
produce an unrealistic model.

`has_identity` distinguishes “no identity record exists” from “an identity row
exists but a particular identity value is missing.”

## 2. Features created before the split

Shared features use only values already present in the current transaction row.
They do not learn medians, frequencies, vocabularies, or fraud rates.

| Feature | Construction | Reason |
| --- | --- | --- |
| `has_identity` | Whether an identity-table row exists | Identity availability has a different fraud profile and is missing for most rows. |
| `num_missing` | Null count across source inputs | Overall information sparsity can itself be predictive. |
| `transaction_missing` | Missing count for basic transaction fields | Separates transaction-data absence from identity absence. |
| `card_address_missing` | Missing count for card/address fields | Indicates incomplete payment-location context. |
| `identity_missing` | Missing count for identity/device fields | Summarizes device and browser evidence availability. |
| `transaction_amount_log1p` | `log(1 + max(amount, 0))` | Compresses the long amount tail while retaining order. |
| `transaction_amount_cents` | Decimal/cents component | Payment pricing patterns may differ by fraud behavior. |
| `transaction_relative_day` | `TransactionDT // 86400` | Captures progress through the observed dataset period. |
| `transaction_relative_week` | `TransactionDT // 604800` | Captures slower time variation. |
| `transaction_relative_hour_phase` | Seconds modulo one day, divided by 3600 | Adds a periodic phase without claiming a real timezone clock. |
| `card_1_2` | `card1 + card2` | Represents a combined card identity. |
| `address_1_2` | `addr1 + addr2` | Represents an address combination. |
| `email_pair` | payer + recipient email domains | Captures relationships between email sides. |

`TransactionDT` has an undisclosed calendar origin. Therefore, the finalized
pipeline does not create an `is_weekend` claim and does not call the periodic
phase a real hour of day.

## 3. Cleaning and chronological partitions

The data is sorted by `TransactionDT`, with `TransactionID` as a deterministic
tie breaker:

```text
Earliest 70% → training
Next 15%     → validation
Latest 15%   → final chronological holdout
```

All-null and constant columns are identified using training only. `isFraud` is
the target and `TransactionID` remains only for traceability; neither enters a
model.

No global median fill occurs in shared preparation because CatBoost and
LightGBM can preserve numeric missingness, while Logistic Regression and the
neural network need their own fitted transformations.

## 4. Numeric-looking identifiers

`card1`, `card2`, `card3`, `card5`, `addr1`, and `addr2` are stored as numbers,
but their values are codes. A code of 9000 is not quantitatively larger than a
code of 1000.

They are therefore handled as:

- frequency signals for Logistic Regression and high-cardinality LightGBM paths;
- categorical strings for CatBoost;
- categorical embedding IDs for the neural network.

Actual continuous measurements—including anonymized `V*`, `C*`, `D*`, and
numeric `id_*` fields—remain numerical. A continuous field is not discarded
merely because it has thousands of unique values.

## 5. Cardinality policy

Cardinality is the number of distinct labels in a categorical field, measured
on the training partition only.

| Band | Training unique labels |
| --- | ---: |
| Low | 0–20 |
| Medium | 21–100 |
| High | 101–1,000 |
| Very high | More than 1,000 |

High cardinality is not inherently bad. It becomes a problem when represented
with a huge one-hot matrix or when rare labels overfit.

The pipeline reserves three meanings:

- `MISSING`: no value was supplied;
- `OTHER`: the label existed in training but was too rare;
- `UNKNOWN`: the label was not seen during training.

Rare means fewer than 20 training occurrences by default. This threshold is
configurable and must be tuned using validation data rather than the holdout.

## 6. Model-specific representations

### Logistic Regression

| Input | Transformation | Why |
| --- | --- | --- |
| Numeric quantity | Training median, missing indicator, standard scaling | Linear solvers cannot accept NaN and are sensitive to scale. |
| Low/medium category | Rare grouping and sparse one-hot encoding | Preserves category identity at manageable width. |
| High-cardinality category/code | Training-only frequency encoding | Avoids enormous one-hot matrices. |

The transformations and classifier are saved together in `model.joblib`.

### LightGBM

| Input | Transformation | Why |
| --- | --- | --- |
| Numeric quantity | Retain numeric value and NaN | Trees learn missing branches and need no scaling. |
| Low/medium category | Stable categorical levels | LightGBM can split on native categories. |
| High-cardinality category/code | Training-only frequency encoding | Controls memory and category complexity. |

The mappings are saved in `preprocessor.joblib`; the booster is `model.txt`.

### CatBoost

| Input | Transformation | Why |
| --- | --- | --- |
| Numeric quantity | Retain numeric value and NaN | Native numeric missing handling. |
| All categorical and identifier fields | String labels with `MISSING` | CatBoost learns ordered categorical statistics without huge one-hot expansion. |

No manual target encoding is added. The model is saved as `model.cbm`, with a
small schema/order preprocessor in Joblib.

### Neural network

| Input | Transformation | Why |
| --- | --- | --- |
| Numeric quantity | Training median, missing flag, standard scaling | Stable gradient optimization and explicit absence signal. |
| Categorical/identifier field | Training vocabulary and embedding ID | Learns compact category representations. |
| Rare/unseen/missing label | Reserved `OTHER`/`UNKNOWN`/`MISSING` IDs | Stable inference on future categories. |

Embeddings are concatenated with numeric inputs and passed through dense layers
`256 → 128 → 64 → 1`.

## 7. Missing-value reasoning

- Rows are not removed because real transactions often lack identity data.
- Sparse columns are not automatically removed; absence can contain fraud signal.
- Tree models retain numeric NaN.
- Linear and neural models use training medians plus explicit missing indicators.
- Categorical missingness becomes a real `MISSING` category.
- All-null and constant training columns are removed because they contain no
  variation during the learning period.

## 8. Leakage prevention

The following objects are fitted using training rows only:

- numerical medians, means, and standard deviations;
- rare-category decisions;
- frequency maps;
- categorical levels;
- neural-network vocabularies;
- model parameters.

Validation selects hyperparameters and the decision threshold. The latest 15%
must not influence those decisions.

## 9. Feature importance and later reduction

EDA provides candidate signals but cannot prove final importance because fraud
patterns are nonlinear and interaction-heavy. The baseline begins with all
usable features. After valid runs:

1. Collect logistic coefficient magnitudes, LightGBM gain, CatBoost importance,
   and neural grouped ablations.
2. Create a consensus candidate ranking.
3. Retrain a reduced 150–250-feature version on the same training/validation rows.
4. Keep the reduced version only if validation performance and operational
   metrics are similar or better.
5. Do not use the holdout to choose the feature count.

## 10. Interview summary

> We preserve all transactions through a left join, create only row-available
> shared signals, and freeze chronological partitions. The underlying evidence
> is common, but its representation matches each algorithm: sparse encoding for
> the linear baseline, native/frequency categoricals for LightGBM, ordered
> categorical handling for CatBoost, and learned embeddings for the neural
> network. Every learned mapping is fitted on the earliest training period only
> and saved with the model for identical API inference.
