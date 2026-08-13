# Four-Model Experiment Plan

This is the agreed machine-learning plan for the IEEE-CIS fraud-detection project. It describes exactly what each model receives, why it is included, how it is trained, and how the four results are compared in the deployed hackathon application.

## 1. Decision summary

We will compare four supervised binary-classification approaches:

| # | Model | Role in the project | Expected strength |
| ---: | --- | --- | --- |
| 1 | Logistic Regression | Simple, interpretable baseline | Establishes a minimum performance reference. |
| 2 | LightGBM | High-performance gradient-boosted-tree benchmark | Fast nonlinear tabular model. |
| 3 | CatBoost | Main categorical-aware candidate | Strong handling of missing values and high-cardinality categories. |
| 4 | Embedding-based tabular neural network | Deep-learning benchmark | Learns compact representations of cards, devices, emails, and other high-cardinality categories. |

The hackathon application loads and displays **all four approved model bundles**. We still identify a champion in the comparison table, but the champion label does not hide the other three outputs.

## 2. The rule that makes the comparison fair

All four models use the same source data, same left join, same time period, same target, and same train/validation/test partitions. They receive the same underlying fraud signals.

```text
Transaction table + identity table
              ↓
Left join on TransactionID
              ↓
Shared fraud signals and safe cleaning
              ↓
Chronological split: 70% train / 15% validation / 15% final test
              ↓
Algorithm-specific representation
   ├── Logistic Regression
   ├── LightGBM
   ├── CatBoost
   └── Tabular neural network
```

“Same feature engineering” does **not** mean every model receives identical column types. For example, `DeviceInfo="iPhone"` is the same business signal for each model, but the linear model receives a frequency number, CatBoost receives a category label, and the neural network receives an embedding ID.

## 3. Shared data-science pipeline

### 3.1 Load only the data needed for a training run

The current training workflow begins with `train_transaction.csv` and `train_identity.csv`. Join these two files first. Do not load training and Kaggle test tables simultaneously during model development: they consume unnecessary memory and can restart a cloud notebook kernel.

The Kaggle test files are used later only to generate a competition-style prediction file, not to select the model.

### 3.2 Left join and identity availability

```python
train = train_transaction.merge(train_identity, on="TransactionID", how="left")
```

This keeps all 590,540 transactions. Only about 24% have an identity row; losing the rest would give an unrealistic fraud population. Add `has_identity` so the model can distinguish “no identity record” from a present record with a particular missing field.

### 3.3 Basic quality checks

Before modelling:

- verify unique `TransactionID` values in each source table;
- retain rows with missing values;
- drop all-null and constant feature columns;
- exclude `TransactionID` from model inputs;
- keep `isFraud` as the label only;
- reduce numerical memory types where safe (`float64` → `float32`, large integer types → smaller types) before heavy transformations.

### 3.4 Shared row-level fraud signals

These features use only the current transaction row, so they are available at real-time scoring.

| Signal group | Current features | Why it is useful |
| --- | --- | --- |
| Amount | `TransactionAmt`, `log_TransactionAmt` | Captures payment scale while reducing skew from extreme amounts. |
| Relative time | `transaction_relative_day`, `transaction_relative_week`, `transaction_relative_hour_phase` | Captures movement and periodic phase in the observed timeline without claiming an undisclosed calendar origin. |
| Identity availability | `has_identity` | Device/identity availability has a different fraud profile from its absence. |
| Missingness | selected `<field>_missing` flags and `num_missing` | Missing context can itself be a risk signal. |
| Combined entities | `card1_card2`, `addr1_addr2`, `email_pair` | Risk can depend on a combination rather than one field alone. |
| Original signals | transaction, card, address, email, `C*`, `D*`, `M*`, `V*`, and `id_*` fields | Even anonymized features can contain strong measured fraud signal. |

We will add `num_missing` (the number of null fields in a row) during the memory-safe preparation revision. It summarizes whether a transaction has unusually sparse context.

### 3.5 Type contract: actual quantities versus codes

Not every numeric-looking field is a real quantity.

| Category | Examples | Treatment intention |
| --- | --- | --- |
| Continuous/numeric signal | `TransactionAmt`, `C*`, `D*`, `V*`, numeric `id_*`, time/missingness features | Treat as numeric. |
| Categorical label stored as text | `ProductCD`, `card4`, `card6`, `M*`, string `id_*`, `DeviceType`, `DeviceInfo`, emails | Treat as categorical. |
| Identifier-like code stored as number | `card1`, `card2`, `card3`, `card5`, `addr1`, `addr2` | Treat as a category/identifier for category-aware models; add frequency features rather than assuming a larger code is a larger quantity. |

### 3.6 High-cardinality strategy

High cardinality means many unique labels, for example `card1` has thousands of values. It is useful in fraud detection but must not be blindly one-hot encoded.

For categorical/identifier-like fields, apply learned mappings **after the chronological split**:

1. Build category counts from the training partition only.
2. Replace values observed fewer than 20 times in training with `OTHER` for the linear/LightGBM paths.
3. Reserve separate labels for `MISSING` and unseen future values (`UNKNOWN`).
4. Create training-only frequency features for important fields: `card1`, `card2`, `card3`, `card5`, `addr1`, `addr2`, `DeviceInfo`, payer email domain, recipient email domain, and the three combined entities.
5. Apply exactly the stored maps to validation, test, API, and dashboard inputs.

This prevents leakage and keeps the model stable when it sees a new card/device/email in production.

### 3.7 Time-aware split and leakage rule

Sort by `TransactionDT`:

```text
Earliest 70%  → training
Next 15%      → validation: model/feature/threshold decisions
Latest 15%    → final test: used once after all decisions are fixed
```

All learned transformations—medians, scalers, rare-category maps, category IDs, and frequency maps—are fitted on training rows only. The final test period must never guide model choice, feature selection, or thresholds.

## 4. Approach 1 — Logistic Regression

### Why we include it

It is the transparent baseline. It answers: “How well can a simple linear risk score perform?” If tree models or the neural network improve substantially, we can demonstrate that their added complexity is justified.

### Feature representation

| Input kind | Representation for Logistic Regression |
| --- | --- |
| Continuous numeric features | Training median imputation, missingness indicators, then `StandardScaler`. |
| Low-cardinality categorical fields | One-hot encoding with unknown-category handling. |
| High-cardinality categorical/identifier-like fields | Training-only rare grouping plus frequency encoding. |
| Numeric identifier-like fields | Replace their raw magnitude with frequency features; do not imply that a larger card/address code is inherently riskier. |

### Training configuration

- Regularized Logistic Regression with `class_weight="balanced"`.
- CPU model; a GPU is not needed.
- Use a practical selected subset if the full linear feature matrix is too large.
- Report ROC-AUC, PR-AUC, precision/recall, and recall at fixed alert capacity.

### Limitation

It cannot naturally learn conditions such as “high amount **and** rare device **and** a particular card-email pairing.” It remains a benchmark, not the expected production winner.

## 5. Approach 2 — LightGBM

### Why we include it

LightGBM is a fast gradient-boosted-tree model that learns nonlinear thresholds and feature interactions efficiently. It gives a strong production-quality benchmark with lower inference cost.

### Feature representation

| Input kind | Representation for LightGBM |
| --- | --- |
| Continuous numeric features | Keep numeric values and `NaN`; LightGBM can learn missing-value branches. No scaling. |
| Low-cardinality categoricals | Use stable integer/category representation derived from training data. |
| High-cardinality categoricals | Training-only rare grouping plus frequency features; avoid huge one-hot matrices. |
| Identifier-like codes | Frequency features are primary; optional stable categorical representation can be compared later. |

### Training configuration

- `LGBMClassifier` with early stopping on the validation period.
- `scale_pos_weight = legitimate_count / fraud_count` from the training split only.
- CPU training is reliable; GPU is optional and not necessary for the first benchmark.
- Tune tree depth/leaves, learning rate, number of trees, row/column sampling, and regularization only after the first valid run.

### Strength and limitation

It is fast and strong on numeric/tabular interactions. It needs more deliberate categorical handling than CatBoost.

## 6. Approach 3 — CatBoost

### Why we include it

CatBoost is the leading initial deployment candidate because the dataset contains missing values, many categorical fields, and high-cardinality card/device/email patterns.

### Feature representation

| Input kind | Representation for CatBoost |
| --- | --- |
| Continuous numeric features | Keep as numeric and retain `NaN`. |
| Categorical text fields | Fill null with `MISSING`, retain category strings. |
| Identifier-like card/address codes | Convert to strings and pass as categorical fields rather than treating code magnitude as a quantity. |
| High-cardinality categoricals | Retain as category labels after `MISSING` handling; CatBoost's ordered categorical statistics learn useful patterns without a huge one-hot matrix. Store optional frequency features as extra signals only if validation proves value. |

### Training configuration

- `CatBoostClassifier` with `class_weights=[1, negative/positive]` from training data.
- Early stopping against validation PR-AUC/ROC-AUC.
- T4 GPU may be used after validating a smaller CPU run. Use GPU memory consciously: moderate depth, batching handled internally, and no duplicate dataframes in memory.
- Save model, exact feature list, categorical feature list, threshold, and model metadata.

### Strength and limitation

It usually handles this type of data exceptionally well with modest manual preprocessing. The model can be less straightforward to explain than Logistic Regression, so we will provide feature importance/SHAP explanations for the analyst UI.

## 7. Approach 4 — embedding-based tabular neural network

### Why we include it

This is a meaningful deep-learning experiment for the hackathon. It can learn dense representations (embeddings) for high-cardinality cards, devices, browsers, and email categories, then combine them with numeric fraud signals.

### Feature representation

| Input kind | Representation for neural network |
| --- | --- |
| Continuous numeric features | Median-impute from training data, add missingness flags, then standard-scale. |
| Categorical/identifier-like fields | `MISSING`/`OTHER`/`UNKNOWN` handling, training-only integer IDs, then learned embeddings. |
| High-cardinality fields | Learned embeddings; never one-hot encode. |

### Architecture

```text
Categorical labels → integer IDs → embedding layers
                                           ↓
Numeric features → imputation + scaling ──┼→ concatenate
                                           ↓
Dense(256) → ReLU → Dropout(0.30)
Dense(128) → ReLU → Dropout(0.20)
Dense(64)  → ReLU → Dropout(0.10)
Dense(1)   → logit → sigmoid fraud probability
```

Embedding size is selected from each category count and capped (for example, a small number for low-cardinality fields and up to 32–50 dimensions for very high-cardinality fields). This avoids a huge sparse input while letting the model learn related category behavior.

### Training configuration

- PyTorch with `BCEWithLogitsLoss(pos_weight=negative/positive)`.
- AdamW optimizer, mini-batches, early stopping by validation PR-AUC, and best-checkpoint saving.
- T4 GPU with mixed precision for efficient training.
- Start with 10–20 epochs, batch size chosen from available memory, and dropout/weight decay to control overfitting.

### Strength and limitation

It gives a genuine deep-learning comparison and uses the T4 well. On medium-size structured data, it may not beat CatBoost/LightGBM; we will report the real result and still show its independent output in the four-model application.

## 8. Common imbalance treatment

Fraud is only about 3.5% of rows. All models are trained to account for that imbalance:

| Model | Imbalance treatment |
| --- | --- |
| Logistic Regression | `class_weight="balanced"` |
| LightGBM | `scale_pos_weight` |
| CatBoost | `class_weights` |
| Neural network | `BCEWithLogitsLoss(pos_weight=...)` |

We will not use SMOTE in the first benchmark because synthetic transactions can distort mixed categorical, time-ordered fraud data.

## 9. How we compare the models and designate a champion

Use validation data to select a model and threshold. Report every model with:

- PR-AUC / Average Precision — primary rare-fraud ranking metric;
- ROC-AUC — secondary ranking metric;
- precision and recall at an operational threshold;
- recall at top 5% and top 10% of highest-risk alerts — analyst-capacity metrics;
- training time, prediction latency, and artifact size;
- calibration/reliability check before making approve/review/block decisions.

After each model's feature set and threshold are frozen, run the latest 15% holdout once. Save one approved, reload-tested deployment bundle per model. The strongest business result is labelled the champion, while the API loads all four bundles and returns four separate outputs.

## 10. Lightning AI execution plan

Lightning AI Studio is suitable because it provides a persistent cloud workspace with JupyterLab/VS Code and optional GPU instances. Use the Studio workspace as the persistent location for the repository, processed Parquet files, experiment metrics, and model artifacts. [Lightning AI Studio documentation](https://lightning.ai/docs/overview/ai-studio/)

Recommended working pattern:

1. Clone the repository inside the Studio and work on the `develop` branch.
2. Start with a CPU instance to download data, create memory-efficient processed Parquet files, and install dependencies.
3. Use persistent Studio storage for `data/processed/` and `artifacts/`; do not depend on temporary notebook memory.
4. Use CPU for Logistic Regression and the first LightGBM run.
5. Switch to a T4 only for CatBoost GPU and the neural network after data preparation is complete.
6. Push source/docs/metrics to Git; upload approved model bundles to private Cloudflare R2 rather than normal Git history.

The executable notebook order and owner assignments are in [LIGHTNING_TRAINING_GUIDE.md](LIGHTNING_TRAINING_GUIDE.md). Artifact formats are fixed in [MODEL_ARTIFACT_CONTRACT.md](MODEL_ARTIFACT_CONTRACT.md).

### Memory rule

The old preparation pattern of loading all four raw train/test CSVs and keeping raw plus merged copies in memory can restart a T4 notebook kernel. The revised preparation notebook must process the training pair first, free intermediate frames, downcast types, write its splits, and load Kaggle test only as a separate later step.

## 11. Experiment order

```text
Phase 1: memory-safe preparation + EDA outputs
Phase 2: Logistic Regression baseline
Phase 3: LightGBM benchmark
Phase 4: CatBoost benchmark
Phase 5: Tabular neural-network benchmark
Phase 6: compare metrics and feature importances
Phase 7: add one feature group at a time and retest the leading models
Phase 8: full versus reduced-feature comparison
Phase 9: final holdout test, calibration, threshold selection, and artifact export
Phase 10: FastAPI on Render + React/Vite on Cloudflare Pages
```

## 12. Data-scientist working principles

- Do not claim a feature is important from correlation alone; validate it with later-time model performance.
- Do not use a random final split for time-ordered fraud data.
- Do not fit a transformation on validation/test data.
- Do not remove high-cardinality or sparse fields simply because they are difficult; use appropriate encodings and prove their value.
- Add features in small groups and retain them only when they improve the agreed validation metrics.
- Preserve every model's preprocessing contract so the deployed API transforms new transactions exactly as training did.

## 13. Presentation-ready summary

> “We compare four complementary approaches on the same time-aware fraud dataset: an interpretable linear baseline, two gradient-boosted-tree models, and an embedding-based tabular neural network. The shared pipeline preserves missingness, handles high-cardinality signals safely, and prevents time leakage. One common transaction is transformed through four saved preprocessing contracts, and the application displays all four independent risks while clearly identifying the strongest validated model.”
