# IEEE-CIS Fraud Detection: Exploratory Data Analysis

> Generated from the supplied Kaggle files on 2026-08-13. Re-run `src/eda.py` after data or analysis changes.

## Executive summary

- The labelled training transaction table has **590,540 rows** and **394 columns**; fraud prevalence is **3.50%** (20,663 fraud vs. 569,877 non-fraud).
- Only **24.42%** of training transactions have an identity-table row. The correct integration is therefore a left join on `TransactionID`, retaining all 590,540 transactions.
- The joined training data has **435 columns** and is highly sparse: **44.97%** of all cells are missing. Missingness is itself a useful fraud signal and must be modelled carefully.
- This is an imbalanced binary-classification problem. Do not use accuracy as the headline metric; prioritize ROC-AUC, PR-AUC, precision/recall, and recall at a fixed review capacity.
- `TransactionDT` is a relative timestamp. Use chronological splits and fit encoders/features only on earlier training rows to avoid leakage.

## 1. Source files and schema

File | Rows | Columns | Numeric | Categorical | Exact duplicate rows
--- | --- | --- | --- | --- | ---
train_transaction | 590,540 | 394 | 380 | 14 | 0
train_identity | 144,233 | 41 | 24 | 17 | 0
test_transaction | 506,691 | 393 | 379 | 14 | 0
test_identity | 141,907 | 41 | 24 | 17 | 0

`sample_submission.csv` has 506,691 rows and columns: `TransactionID, isFraud`.

### Train/test compatibility

- Train-only columns: `isFraud`. This should be only the label.
- Test-only columns: `None`.
- Use an identical feature-engineering pipeline for train and test; remove `isFraud` from the training feature matrix.

## 2. Merge analysis

The transaction and identity tables share `TransactionID`. `TransactionID` is unique in `train_transaction` (590,540/590,540) and in `train_identity` (144,233/144,233).

Identity available | Transactions | Fraud cases | Fraud rate
--- | --- | --- | ---
True | 144,233 | 11,318 | 7.85%
False | 446,307 | 9,345 | 2.09%

The identity table itself has 40 usable feature columns after excluding the join key, and its average per-column missing rate is 36.47%.

## 3. Target distribution and imbalance

Class | Meaning | Transactions | Share
--- | --- | --- | ---
0 | Legitimate | 569,877 | 96.50%
1 | Fraud | 20,663 | 3.50%

A class-weight starting point for a tree model is approximately **27.58** (`negative / positive`). Tune this value on chronological validation data.

## 4. Transaction amount and time

isFraud | Rows | Mean amount | Median amount | Minimum | Maximum
--- | --- | --- | --- | --- | ---
0 | 569,877 | $134.51 | $68.50 | $0.25 | $31,937.39
1 | 20,663 | $149.24 | $75.00 | $0.29 | $5,191.00

`TransactionDT` spans 86,400 to 15,811,131 seconds, or approximately 1 to 182 relative days (182 observed day buckets). Daily fraud rate ranges from 1.10% to 6.99%; this confirms time variation and supports chronological validation.

## 5. Product-code fraud rates

ProductCD | Transactions | Fraud cases | Fraud rate
--- | --- | --- | ---
C | 68,519 | 8,008 | 11.69%
S | 11,628 | 686 | 5.90%
H | 33,024 | 1,574 | 4.77%
R | 37,699 | 1,426 | 3.78%
W | 439,670 | 8,969 | 2.04%

ProductCD has materially different fraud rates by category, making it an important categorical input. The relationship must be learned on training partitions only.

## 6. Missing data

Training transaction data alone contains 95,566,686 missing cells (41.07% average cell missingness); the merged table contains 115,523,073 missing cells.

Column | Missing % | Data type | Unique non-null values
--- | --- | --- | ---
id_24 | 99.20% | float64 | 12
id_25 | 99.13% | float64 | 341
id_08 | 99.13% | float64 | 94
id_07 | 99.13% | float64 | 84
id_21 | 99.13% | float64 | 490
id_26 | 99.13% | float64 | 95
id_23 | 99.12% | object | 3
id_22 | 99.12% | float64 | 25
id_27 | 99.12% | object | 2
dist2 | 93.63% | float64 | 1,751
D7 | 93.41% | float64 | 597
id_18 | 92.36% | float64 | 18
D13 | 89.51% | float64 | 577
D14 | 89.47% | float64 | 802
D12 | 89.04% | float64 | 635
id_03 | 88.77% | float64 | 24
id_04 | 88.77% | float64 | 15
D6 | 87.61% | float64 | 829
id_33 | 87.59% | object | 260
D9 | 87.31% | float64 | 24
D8 | 87.31% | float64 | 12,353
id_09 | 87.31% | float64 | 46
id_10 | 87.31% | float64 | 62
id_30 | 86.87% | object | 75
id_32 | 86.86% | float64 | 4

Recommended handling: preserve an explicit `MISSING` category for categorical fields; use a robust numeric imputation strategy or a model with native missing-value handling; and add missingness indicators for key fields. Do not drop every sparse column blindly—absence of device/identity information can carry signal.

## 7. Categorical cardinality

Column | Unique observed values | Missing %
--- | --- | ---
R_emaildomain | 60.0 | 76.75%
P_emaildomain | 59.0 | 15.99%
ProductCD | 5.0 | 0.00%
card4 | 4.0 | 0.27%
card6 | 4.0 | 0.27%
M4 | 3.0 | 47.66%
M1 | 2.0 | 45.91%
M2 | 2.0 | 45.91%
M3 | 2.0 | 45.91%
M5 | 2.0 | 59.35%
M6 | 2.0 | 28.68%
M7 | 2.0 | 58.64%
M8 | 2.0 | 58.63%
M9 | 2.0 | 58.63%

High-cardinality columns should not be blindly one-hot encoded. Prefer CatBoost native categorical handling, or training-only frequency encoding / carefully out-of-fold target encoding. Group rare categories as `OTHER` when appropriate.

## 8. Numerical association screen

The following is an absolute Pearson-correlation screen with the target. It is diagnostic only: fraud patterns are nonlinear, and a low linear correlation does not mean a feature is unhelpful.

Feature | Absolute correlation with isFraud
--- | ---
V257 | 0.3831
V246 | 0.3669
V244 | 0.3641
V242 | 0.3606
V201 | 0.3280
V200 | 0.3188
V189 | 0.3082
V188 | 0.3036
V258 | 0.2972
V45 | 0.2818
V158 | 0.2781
V156 | 0.2760
V149 | 0.2733
V228 | 0.2689
V44 | 0.2604
V86 | 0.2518
V87 | 0.2517
V170 | 0.2498
V147 | 0.2429
V52 | 0.2395

## 9. Modelling recommendations from the EDA

1. Start with CatBoost (native categoricals) or LightGBM (encoded categoricals) as the baseline model.
2. Left-join identities and create `has_identity`; never inner-join the tables.
3. Use `TransactionDT` to split earliest 70% for training, next 15% for validation, latest 15% for final testing.
4. Use class weights; begin near the calculated negative-to-positive ratio and tune against PR-AUC and reviewer capacity.
5. Engineer amount, time, card/address/email/device composite, frequency, and historical features. Historical aggregates must use earlier rows only.
6. Save the entire preprocessing schema with the model so API inputs receive exactly the training-time transformation.
7. Select a threshold based on business trade-offs: e.g., block very-high scores and route medium scores to an analyst queue.

## 10. Leakage and deployment checklist

- Never random-split this time-ordered data for the final claim.
- Fit imputers, category mappings, scalers, and frequency maps on the training fold only.
- For online scoring, ensure every historical feature is computed using data available before the transaction being scored.
- Do not expose `isFraud` in API input; it is a training label only.
- Keep Kaggle files and credential files out of Git (already covered by `.gitignore`).

## Reproducibility

The calculations in this report are generated by `src/eda.py` from the supplied files in `data/raw/ieee-fraud-detection/`. Run it with the project Python environment once it is created. The raw data and extracted CSVs are intentionally ignored by Git.
