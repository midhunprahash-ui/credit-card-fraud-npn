# Credit Card Fraud Detection — NPN Hackathon

An end-to-end fraud-risk scoring application built with the IEEE-CIS Fraud Detection dataset. The project combines transaction information with device and identity signals, predicts the probability of fraud, and presents the result in an analyst-friendly dashboard.

## Project goal

Banks need to identify suspicious e-commerce payments quickly while avoiding unnecessary blocks of genuine customers. This application uses **supervised binary classification** to assign every transaction a fraud probability.

| Item | Meaning |
| --- | --- |
| Input | Transaction, card, email, address, device, browser, and identity attributes |
| Target | `isFraud` (`1` fraudulent, `0` legitimate) |
| Output | Fraud probability, risk level, recommended action, and model explanation |
| Primary model | CatBoost or LightGBM gradient-boosted decision-tree classifier |
| Deployment target | Cloud-hosted FastAPI prediction API and Streamlit analyst dashboard |

## Solution flow

```text
Kaggle source files
        ↓
Data validation and left join on TransactionID
        ↓
Cleaning and feature engineering
        ↓
Time-based train / validation / test split
        ↓
Class-weighted fraud classifier
        ↓
Saved model and feature schema
        ↓
FastAPI scoring service → Streamlit analyst dashboard → Cloud deployment
```

## Repository structure

```text
credit-card-fraud-npn/
├── data/                 # Local datasets only; ignored by Git
│   ├── raw/              # Kaggle download ZIP/CSV files
│   └── processed/        # Validated, engineered datasets
├── docs/                 # Plain-language project documentation
├── notebooks/            # Exploration and experiments
├── src/                  # Reusable data, features, training, evaluation code
├── api/                  # FastAPI service
├── dashboard/            # Streamlit analyst dashboard
├── models/               # Exported model artifacts; normally ignored by Git
├── tests/                # Automated checks
├── requirements.txt      # Python dependencies
├── render.yaml           # Cloud deployment definition (when added)
└── README.md             # This project entry point
```

## Dataset

The data comes from the [IEEE-CIS Fraud Detection Kaggle competition](https://www.kaggle.com/competitions/ieee-fraud-detection). Download it only after accepting the competition rules with your Kaggle account.

Expected files:

```text
train_transaction.csv     # Training transactions and isFraud label
train_identity.csv        # Optional device and identity signals for some transactions
test_transaction.csv      # Kaggle test transactions
test_identity.csv         # Kaggle test identity signals
sample_submission.csv     # Submission format example
```

`train_transaction` and `train_identity` are joined using `TransactionID` with a **left join**. A left join retains every transaction, including those that do not have identity information.

## Model decision

The project is a binary classifier. Instead of returning only fraud/not fraud, it first produces a probability such as `0.82`.

| Probability | Risk level | Suggested action |
| ---: | --- | --- |
| ≥ 0.85 | High | Block or urgently investigate |
| 0.60–0.85 | Medium | Send to manual review |
| < 0.60 | Low | Approve and monitor |

Thresholds are configurable. They will be selected based on alert capacity and fraud loss, not assumed to be `0.50`.

## Evaluation approach

Fraud is rare, so accuracy can be misleading. We will use:

- ROC-AUC for ranking quality and Kaggle alignment.
- PR-AUC / Average Precision for rare-fraud performance.
- Recall at a fixed alert rate to show fraud captured within analyst capacity.
- Precision at top K to measure the quality of the highest-risk queue.

Data will be split chronologically using `TransactionDT`, not randomly, to prevent future transaction patterns leaking into training.

## Team workflow

1. Keep all implementation work inside this repository.
2. Work on `develop`; reserve `main` for finalized, tested milestones only.
3. When a milestone is complete, document it, commit it on `develop`, merge it into `main`, and push both branches to GitHub.
4. Immediately switch back to `develop` after the merge before beginning the next task.
5. Do not commit Kaggle data, large model binaries, API keys, or `.env` files.
6. Update the relevant document in `docs/` whenever you make a meaningful data, model, API, dashboard, or deployment decision.
7. Run tests before committing changes and record experiment settings and metrics so results can be reproduced.

See [docs/PROJECT_GUIDE.md](docs/PROJECT_GUIDE.md) for the detailed project plan and handover guide.

For a simple explanation of every feature, preprocessing rule, high-cardinality handling method, and model-specific difference, see [docs/FEATURE_ENGINEERING_GUIDE.md](docs/FEATURE_ENGINEERING_GUIDE.md).

For the complete source-column list after the transaction/identity left join—including real example values, missingness, data types, and the honest interpretation available for anonymized fields—see [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md).

The committed interactive report is available at [reports/eda/ieee_cis_train_left_join_profile.html](reports/eda/ieee_cis_train_left_join_profile.html). For its reproducible `ydata-profiling` workflow, memory-safe full-row command, and optional deeper sample report, see [docs/YDATA_PROFILING_GUIDE.md](docs/YDATA_PROFILING_GUIDE.md).

The project is being built against the hackathon expectations captured in [docs/HACKATHON_EVALUATION_CHECKLIST.md](docs/HACKATHON_EVALUATION_CHECKLIST.md). The fixed four-model machine-learning lifecycle is in [docs/FOUR_MODEL_EXPERIMENT_PLAN.md](docs/FOUR_MODEL_EXPERIMENT_PLAN.md).

## Google Colab training notebooks

Run the notebooks in this order after opening them in Google Colab:

1. `notebooks/01_colab_data_preparation.ipynb` — Kaggle API download, left join, shared features, and chronological splits.
2. `notebooks/02_logistic_regression_baseline.ipynb` — interpretable baseline.
3. `notebooks/03_lightgbm.ipynb` — boosted-tree benchmark.
4. `notebooks/04_catboost.ipynb` — categorical-aware candidate for deployment.

The first notebook saves processed data to Google Drive under `MyDrive/ieee_fraud/processed`. The three model notebooks read it from there and save metrics/models under `MyDrive/ieee_fraud/artifacts`.
