# Lightning AI four-model training guide

This is the team runbook for producing comparable, deployable artifacts from
the IEEE-CIS labelled training data.

## 1. Team ownership

| Approach | Owners | Purpose |
| --- | --- | --- |
| Shared preparation | Entire team | One join, feature audit, and frozen chronological partitions |
| Logistic Regression | Nanda / Khishan | Interpretable baseline |
| LightGBM | Saravana / Nebal | Efficient nonlinear tree benchmark |
| CatBoost | Midhun / Ajmeer | Native categorical deployment candidate |
| Tabular neural network | Mirdula / Hashvitha | Embedding-based deep-learning benchmark |

Ownership means running the notebook, recording issues, interpreting the
results, and presenting the approach. Shared utilities and input contracts must
not be changed independently by one model team.

## 2. Create the Lightning Studio

1. Create a persistent Lightning AI Studio.
2. Clone the repository and switch to the stable `main` branch.
3. Use Python 3.11 where possible.
4. Accept the IEEE-CIS Kaggle competition rules.
5. In Lightning AI, open the profile menu and choose **Global settings → Secrets → New Secret**.
6. Enter `KAGGLE_API_TOKEN` as the secret name and paste the Kaggle token as its value.
7. Save the secret, then restart the Studio terminal and notebook kernel so it becomes available.
8. Never paste or print the token in a notebook.

Suggested clone commands:

```bash
git clone https://github.com/midhunprahash-ui/credit-card-fraud-npn.git
cd credit-card-fraud-npn
git switch main
git pull origin main
```

## 3. Run order

Run:

```text
00_shared_data_preparation.ipynb
```

It creates:

```text
data/processed/
├── train.parquet
├── validation.parquet
├── test.parquet
├── feature_audit.csv
├── split_metadata.json
├── shared_feature_config.json
└── raw_input_schema.json
```

After that, the four model notebooks can run independently. Do not let each
team create a different split; that would make the comparison invalid.

## 4. Memory expectations

- Shared preparation and Logistic Regression mainly need CPU RAM, not GPU.
- Start preparation with 24–32 GB RAM if available.
- LightGBM can start on CPU.
- CatBoost and the neural network can use a T4 GPU.
- A T4 adds GPU memory but does not automatically increase system RAM.
- If the kernel restarts, use more CPU RAM; do not solve it by dropping random
  rows or silently changing the agreed dataset.

The preparation notebook loads only the two labelled training tables, downcasts
them, joins them once, deletes intermediates, and writes Parquet. Kaggle's
unlabelled competition test tables are deliberately excluded from model
selection.

## 5. Fair-comparison rules

All models must use:

- the same left-joined rows;
- the same shared row-level features;
- earliest 70% for training;
- next 15% for validation and threshold selection;
- latest 15% as the final holdout;
- PR-AUC as the primary metric;
- the same capacity metrics at top 1%, 5%, and 10%;
- training-only imputers, frequency maps, category levels, and vocabularies.

`FAST_RUN=True` exists only for code verification. Any run with that flag must
be labelled experimental and cannot be used in the presentation comparison.

## 6. What every completed run produces

```text
artifacts/<model>/<UTC-run-id>/
├── native model file
├── saved preprocessing contract
├── feature_schema.json
├── threshold.json
├── metrics.json
├── training_config.json
├── validation_predictions.parquet
├── test_predictions.parquet
├── interpretation output
└── manifest.json
```

The manifest records sizes and SHA-256 checksums. Each notebook reloads the
artifact and proves that five validation probabilities match the original
in-memory model.

## 7. Selecting a threshold

The model first returns a probability. The notebook selects a threshold on the
validation period by maximizing recall subject to an initial minimum precision
of 10%. This is an explicit starting policy, not a universal banking rule.

After the first comparison, the team may change the precision floor or select a
threshold based on analyst review capacity. The decision must be made on
validation predictions and recorded in `threshold.json`; it must not be tuned
against the final holdout.

## 8. Uploading a completed run to Cloudflare R2

The last cell of every model notebook is disabled by default. To upload, create
Lightning secrets:

```text
R2_ENDPOINT_URL
R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY
R2_BUCKET_NAME
```

Then change `UPLOAD_TO_R2 = True` only after the reload test passes. The bucket
must be private. Never place R2 credentials or model binaries in normal Git
history.

## 9. Result handover checklist

Each owner pair must provide:

1. Run ID and Lightning machine type.
2. Validation and holdout metric JSON.
3. Threshold selection rationale.
4. Training time and inference throughput.
5. Top features or model explanation.
6. Artifact manifest and successful reload message.
7. R2 object prefix, if uploaded.
8. A short explanation of missing values, cardinality, and class imbalance for
   their model.

## 10. Common errors

- **Missing Parquet files:** run notebook `00` first in the same persistent Studio.
- **Kernel killed:** select more system RAM and rerun preparation from a clean kernel.
- **Kaggle 401/403:** confirm rules are accepted and the token secret is current.
- **CUDA unavailable:** switch to a GPU Studio or set the CatBoost run to CPU.
- **Unknown categories:** do not rebuild mappings; the saved preprocessor maps them to `UNKNOWN`.
- **Joblib load error:** clone the same source version and install versions recorded in `training_config.json`.
- **LightGBM saves only a few trees while validation PR-AUC is still rising:** pull the latest `main` branch. The corrected notebook disables default binary log-loss monitoring and selects the tree count using validation Average Precision only.
