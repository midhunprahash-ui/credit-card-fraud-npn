# Project Guide and Team Handover

This document explains the whole project in simple terms. Keep it updated as the project evolves.

## 1. What we are building

We are building a cloud-hosted application that helps fraud analysts prioritize suspicious online payment transactions. A user can score one transaction or upload a batch. The system returns a risk score, a risk category, a recommended action, and the main signals that influenced the result.

This is a demonstration system trained on anonymized historical data. The dashboard's live activity is simulated; it is not connected to a bank payment network.

## 2. Inputs and outputs

### Input

The original data has two tables:

- **Transaction table:** payment amount, card-related fields, addresses, email domains, and anonymous `V`/`C`/`D` variables.
- **Identity table:** device type, browser, operating system, screen information, and anonymous `id_` variables.

The common identifier is `TransactionID`. In the deployed form, fields not supplied by an analyst are filled with the training-time missing-value defaults.

### Output

The API returns a JSON response with the fraud probability and action. Example:

```json
{
  "transaction_id": "demo-001",
  "fraud_probability": 0.82,
  "prediction": "FRAUD",
  "risk_level": "HIGH",
  "recommended_action": "MANUAL_REVIEW",
  "model_version": "v1.0.0"
}
```

The dashboard translates this into a prioritized queue for an analyst.

## 3. Data pipeline

1. Download the Kaggle files into `data/raw/`.
2. Validate expected columns and duplicate `TransactionID` values.
3. Left-join identity data to transaction data using `TransactionID`.
4. Mark whether identity data is present (`has_identity`).
5. Handle missing values consistently:
   - numeric values: median imputation;
   - categorical values: `MISSING` category.
6. Drop empty, constant, and proven-unhelpful duplicate columns.
7. Write reusable processed data to `data/processed/`.

### Why left join matters

Only some transactions have identity records. An inner join would drop every transaction without one, losing useful training examples and giving the model an unrealistic view of production traffic.

## 4. Feature engineering plan

Features should be generated in `src/features.py` and used identically during training and prediction.

The complete current implementation and explanation is in [FEATURE_ENGINEERING_GUIDE.md](FEATURE_ENGINEERING_GUIDE.md). It distinguishes features already implemented in Notebook 01 from planned improvements, so team members do not mistake future work for completed work.

- Amount features: `log1p(TransactionAmt)`, amount bands, decimal component.
- Time features: relative day, week, approximate hour, and weekend indicator from `TransactionDT`.
- Device features: normalized device/browser strings and rare-category grouping.
- Composite features: card combinations, address combinations, and payer/receiver email pairs.
- Frequency encoding: occurrence count of high-cardinality values such as cards, device, address, and email domain.
- Missingness indicators: features that show whether important information was absent.
- Historical behavior features: only use transactions earlier in time; never use future data.

## 5. Model and validation

### Classification technique

We use **supervised binary classification**. Gradient-boosted decision trees (CatBoost or LightGBM) are the planned main models because they are strong on wide tabular data, handle nonlinear relationships, and can work with missing values and categorical variables.

### Class imbalance

Fraud is a small share of transactions. The model will use class weights (`scale_pos_weight` for LightGBM or `class_weights` for CatBoost) instead of trusting accuracy or oversampling by default.

### Preventing data leakage

Split data by transaction time:

```text
Earliest 70% → model training
Next 15%     → model validation and threshold selection
Latest 15%   → final untouched evaluation
```

Any frequency or historical feature must be fitted using training data only before it is applied to validation and test rows.

### Google Colab notebook run order

Use the Colab notebooks in the following order:

| Notebook | Purpose | Output |
| --- | --- | --- |
| `01_colab_data_preparation.ipynb` | Kaggle API download, data join, common features, chronological split | Google Drive processed parquet files and metadata |
| `02_logistic_regression_baseline.ipynb` | Simple linear benchmark | Baseline metric JSON |
| `03_lightgbm.ipynb` | Gradient-boosting benchmark | Metric JSON and LightGBM model |
| `04_catboost.ipynb` | Categorical-aware candidate | Metric JSON, CatBoost model, feature schema |

Before notebook 01, accept the Kaggle competition rules and create an API token in Kaggle Settings → API Tokens. In Colab, store it as a `KAGGLE_API_TOKEN` secret (key icon in the left sidebar) and allow the notebook access to that secret. Never add the token to Google Drive, the repository, a code cell, or a screenshot.

## 6. Application components

### FastAPI (`api/`)

Responsibilities:

- Load the saved model once at startup.
- Validate request data.
- Generate features using the same logic as training.
- Return a fraud score, risk band, and action.
- Expose `/health`, `/predict`, `/predict-batch`, and `/model-metrics`.

### Streamlit (`dashboard/`)

Responsibilities:

- Single-transaction scoring form.
- Batch upload and prioritized fraud queue.
- Key performance metrics and score distributions.
- Transaction explanation / top risk signals.

## 7. Cloud deployment plan

We plan to use Render from this Git repository:

- FastAPI is a Render web service.
- Streamlit is a second Render web service.
- Both use environment variables for configuration.
- An optional Postgres database can store reviewer decisions and audit events.

Before deployment, the model file must be available to the API service. For the hackathon, a versioned model artifact can be included if its size permits, or retrieved from secure object storage during build/deploy.

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
| Dashboard | Analyst can score and review transactions locally |
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
