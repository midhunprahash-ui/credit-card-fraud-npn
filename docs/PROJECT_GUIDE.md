# Project Guide and Team Handover

This document explains the whole project in simple terms. Keep it updated as the project evolves.

## 1. What we are building

We are building a cloud-hosted application that helps fraud analysts prioritize suspicious online payment transactions. A user can score one transaction or upload a batch. The same input is sent through four independently trained models, and the system displays four probabilities, classifications, thresholds, and explanations side by side.

This is a demonstration system trained on anonymized historical data. The dashboard's live activity is simulated; it is not connected to a bank payment network.

## 2. Inputs and outputs

### Input

The original data has two tables:

- **Transaction table:** payment amount, card-related fields, addresses, email domains, and anonymous `V`/`C`/`D` variables.
- **Identity table:** device type, browser, operating system, screen information, and anonymous `id_` variables.

The common identifier is `TransactionID`. In the deployed form, omitted optional fields are normalized as missing; each saved model preprocessor then applies its own training-fitted missing-value behavior.

### Output

The API returns a JSON response with all four fraud probabilities. Simplified example:

```json
{
  "transaction_id": "demo-001",
  "models": {
    "logistic_regression": {"fraud_probability": 0.61, "prediction": 0},
    "lightgbm": {"fraud_probability": 0.84, "prediction": 1},
    "catboost": {"fraud_probability": 0.91, "prediction": 1},
    "neural_network": {"fraud_probability": 0.78, "prediction": 1}
  },
  "agreement": "STRONG_FRAUD_AGREEMENT"
}
```

The React dashboard translates this into model cards and a prioritized analyst queue.

## 3. Data pipeline

1. Download the Kaggle files into `data/raw/`.
2. Validate expected columns and duplicate `TransactionID` values.
3. Left-join identity data to transaction data using `TransactionID`.
4. Mark whether identity data is present (`has_identity`).
5. Preserve missingness and apply model-specific handling:
   - Logistic/Neural numeric values: training median plus missing indicator;
   - LightGBM/CatBoost numeric values: retain `NaN`;
   - categorical values: explicit `MISSING` category.
6. Drop empty, constant, and proven-unhelpful duplicate columns.
7. Write reusable processed data to `data/processed/`.

### Why left join matters

Only some transactions have identity records. An inner join would drop every transaction without one, losing useful training examples and giving the model an unrealistic view of production traffic.

## 4. Feature engineering plan

Features should be generated in `src/features.py` and used identically during training and prediction.

The complete current implementation and explanation is in [FEATURE_ENGINEERING_GUIDE.md](FEATURE_ENGINEERING_GUIDE.md). It distinguishes features already implemented in Notebook 01 from planned improvements, so team members do not mistake future work for completed work.

The detailed source-column reference generated from the supplied files is in [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

- Amount features: `log1p(TransactionAmt)`, amount bands, decimal component.
- Time features: relative day, week, and periodic hour phase from `TransactionDT`; the undisclosed origin does not justify a real weekend label.
- Device features: normalized device/browser strings and rare-category grouping.
- Composite features: card combinations, address combinations, and payer/receiver email pairs.
- Frequency encoding: occurrence count of high-cardinality values such as cards, device, address, and email domain.
- Missingness indicators: features that show whether important information was absent.
- Historical behavior features: only use transactions earlier in time; never use future data.

## 5. Model and validation

### Classification technique

We use **supervised binary classification**. We compare Logistic Regression, LightGBM, CatBoost, and an embedding-based tabular neural network. Gradient-boosted trees are the planned main deployment candidates because they are strong on wide tabular data, handle nonlinear relationships, and can work with missing values and categorical variables. The complete experiment design is in [FOUR_MODEL_EXPERIMENT_PLAN.md](FOUR_MODEL_EXPERIMENT_PLAN.md).

### Class imbalance

Fraud is a small share of transactions. The model will use class weights (`scale_pos_weight` for LightGBM or `class_weights` for CatBoost) instead of trusting accuracy or oversampling by default.

All four implemented treatments and the reasoning for avoiding synthetic SMOTE
rows are documented in
[`CLASS_IMBALANCE_AND_DATA_LEAKAGE.md`](CLASS_IMBALANCE_AND_DATA_LEAKAGE.md).

### Preventing data leakage

Split data by transaction time:

```text
Earliest 70% → model training
Next 15%     → model validation and threshold selection
Latest 15%   → final untouched evaluation
```

Any frequency or historical feature must be fitted using training data only before it is applied to validation and test rows.

Use the acceptance checklist in
[`CLASS_IMBALANCE_AND_DATA_LEAKAGE.md`](CLASS_IMBALANCE_AND_DATA_LEAKAGE.md)
before approving any model bundle.

### Lightning AI notebook run order

Use the finalized notebooks in the following order:

| Notebook | Purpose | Output |
| --- | --- | --- |
| `notebooks/lightning_ai/00_shared_data_preparation.ipynb` | Kaggle download, left join, feature audit, chronological split | Processed Parquet and shared schemas |
| `notebooks/lightning_ai/01_logistic_regression_nanda_khishan.ipynb` | Nanda / Khishan linear baseline | Complete Joblib pipeline and metrics |
| `notebooks/lightning_ai/02_lightgbm_saravana_nebal.ipynb` | Saravana / Nebal tree benchmark | Native LightGBM model, preprocessor, metrics |
| `notebooks/lightning_ai/03_catboost_midhun_ajmeer.ipynb` | Midhun / Ajmeer categorical model | Native CatBoost model, preprocessor, metrics |
| `notebooks/lightning_ai/04_tabular_neural_network_mirdula_hashvitha.ipynb` | Mirdula / Hashvitha embedding model | PyTorch state dictionary, preprocessor, metrics |

Before notebook 00, accept the Kaggle competition rules and create an API token. Store it as a Lightning secret named `KAGGLE_API_TOKEN`. Never add the token to the repository, a code cell, or a screenshot. See [LIGHTNING_TRAINING_GUIDE.md](LIGHTNING_TRAINING_GUIDE.md).

## 6. Application components

### FastAPI (`api/`)

Responsibilities:

- Verify and lazily load only requested approved V1/V2 model bundles.
- Validate request data.
- Generate features using the same logic as training.
- Return independent fraud-risk scores and saved thresholds.
- Replay labelled held-out transactions through one strict FIFO consumer.
- Publish live results over SSE and batch durable results to Supabase.
- Expose health, manual, batch, stream-control, SSE, and metrics endpoints.

### React/Vite frontend (`frontend/`)

Responsibilities:

- Single-transaction scoring form.
- Batch upload and prioritized fraud queue.
- Four side-by-side model probabilities and decisions.
- Key performance metrics, input completeness, and explanations.

## 7. Cloud deployment plan

The finalized platform split is:

- Lightning AI trains the four models.
- Private Cloudflare R2 stores approved versioned model bundles.
- FastAPI runs as a Render web service and lazily loads requested V1/V2 models.
- React/Vite is deployed to Cloudflare Pages.
- GitHub `main` triggers finalized deployments.

See [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md) and [MODEL_ARTIFACT_CONTRACT.md](MODEL_ARTIFACT_CONTRACT.md).

## 8. Security and responsible-demo rules

- Never add Kaggle credentials, cloud tokens, `.env` files, or datasets to Git.
- Use anonymized dataset fields only; do not represent this as production banking data.
- Validate API input and limit batch file sizes.
- Log only non-sensitive demo identifiers and operational metrics.
- Keep a model version and threshold in every prediction response for traceability.

## 9. Suggested milestones

| Milestone | Done when |
| --- | --- |
| Data readiness | Source data is downloaded, joined, validated, and documented |
| Baseline | A reproducible model has time-based ROC-AUC and PR-AUC metrics |
| Improved model | Feature engineering and tuned model outperform baseline |
| API | Local `/health` and `/predict` work against saved model |
| Frontend | Analyst can score and compare all four model results locally |
| Deployment | Public cloud URLs work and deployment is documented |
| Handover | README, setup guide, model metrics, and demo flow are current |

## 10. Git branching and release rule

This repository uses two long-lived branches:

- **`main`**: stable, finalized milestones only. It must always be suitable for a teammate to clone and run using the documented setup.
- **`develop`**: the active development branch. All new work starts and continues here.

### Required workflow for every finalized task

1. Confirm the work and documentation are complete on `develop`.
2. Run the relevant validation/tests.
3. Commit the changes to `develop` with a clear message.
4. Merge `develop` into `main` using a non-destructive merge.
5. Push both `main` and `develop` to `origin`.
6. Switch back to `develop` before starting the next task.

Example commands:

```bash
git switch develop
git add <files>
git commit -m "feat: describe completed change"
git push origin develop

git switch main
git merge --no-ff develop -m "merge: finalized milestone"
git push origin main

git switch develop
```

Do not force-push, rewrite shared history, commit generated data/models, or merge incomplete work into `main`.

## 11. Demo script

1. Open the cloud dashboard.
2. Submit a transaction or upload the demo batch.
3. Sort the queue by fraud probability.
4. Select one high-risk transaction and show its risk signals.
5. Explain the selected review threshold and analyst action.
6. Show model metrics, then the API health endpoint.

## 12. Change log

| Date | Change | Owner |
| --- | --- | --- |
| 2026-08-13 | Repository initialized and project plan documented | Codex / team |
| 2026-08-13 | Two-branch Git workflow adopted | Codex / team |
