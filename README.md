# Credit Card Fraud Detection — NPN Hackathon

An end-to-end fraud-risk scoring application built with the IEEE-CIS Fraud Detection dataset. The project combines transaction information with device and identity signals, produces a fraud-risk score, and presents the result in an analyst-friendly dashboard.

## Project goal

Banks need to identify suspicious e-commerce payments quickly while avoiding unnecessary blocks of genuine customers. This application uses **supervised binary classification** to assign every transaction a fraud-risk score.

| Item | Meaning |
| --- | --- |
| Input | Transaction, card, email, address, device, browser, and identity attributes |
| Target | `isFraud` (`1` fraudulent, `0` legitimate) |
| Output | Fraud-risk score, model-specific decision, latency, and model explanation |
| Models shown | Logistic Regression, LightGBM, CatBoost, and tabular neural network |
| Deployment target | FastAPI multi-model API on Render and React analyst dashboard on Cloudflare |

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
Four class-weighted fraud classifiers
        ↓
Eight approved V1/V2 model bundles and feature schemas
        ↓
FastAPI eight-pipeline scoring service → React analyst dashboard → Cloud deployment
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
├── frontend/             # React/Vite analyst dashboard for Cloudflare Pages
├── artifacts/            # Versioned model bundles; ignored by Git and uploaded to R2
├── tests/                # Automated checks
├── requirements-training.txt # Lightning AI training dependencies
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

The project is a binary classifier. Instead of returning only fraud/not fraud,
each selected model first produces a fraud-risk score. These scores are not
described as calibrated probabilities unless calibration is verified.

| Example score band | Risk level | Suggested action |
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

For the implemented class-imbalance strategy, chronological leakage controls, model-by-model safeguards, acceptance checklist, and interview explanation, see [docs/CLASS_IMBALANCE_AND_DATA_LEAKAGE.md](docs/CLASS_IMBALANCE_AND_DATA_LEAKAGE.md).

For the complete source-column list after the transaction/identity left join—including real example values, missingness, data types, and the honest interpretation available for anonymized fields—see [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md).

The interactive profiling HTML is kept as a local, Git-ignored generated artifact. For its reproducible `ydata-profiling` workflow, memory-safe full-row command, and optional deeper sample report, see [docs/YDATA_PROFILING_GUIDE.md](docs/YDATA_PROFILING_GUIDE.md).

The project is being built against the hackathon expectations captured in [docs/HACKATHON_EVALUATION_CHECKLIST.md](docs/HACKATHON_EVALUATION_CHECKLIST.md). The fixed four-model machine-learning lifecycle is in [docs/FOUR_MODEL_EXPERIMENT_PLAN.md](docs/FOUR_MODEL_EXPERIMENT_PLAN.md). Model bundle formats and the common four-model inference contract are defined in [docs/MODEL_ARTIFACT_CONTRACT.md](docs/MODEL_ARTIFACT_CONTRACT.md).

The finalized four-model results and champion rationale are in [docs/FINAL_MODEL_SELECTION.md](docs/FINAL_MODEL_SELECTION.md). Machine-readable approved run IDs are frozen in [config/model_registry.json](config/model_registry.json).

## Lightning AI training notebooks

The original notebooks below remain the fixed Version 1 baseline. The additive
behavioral Version 2 suite, teammate assignments, run order, and result packaging are
documented in [notebooks/lightning_ai/v2/README.md](notebooks/lightning_ai/v2/README.md)
and [docs/VERSION_2_TRAINING_GUIDE.md](docs/VERSION_2_TRAINING_GUIDE.md).

Run the notebooks in this order inside a persistent Lightning AI Studio:

1. `notebooks/lightning_ai/00_shared_data_preparation.ipynb` — Kaggle API download, memory-safe left join, feature audit, and frozen chronological partitions.
2. `notebooks/lightning_ai/01_logistic_regression_nanda_khishan.ipynb` — Nanda / Khishan.
3. `notebooks/lightning_ai/02_lightgbm_saravana_nebal.ipynb` — Saravana / Nebal.
4. `notebooks/lightning_ai/03_catboost_midhun_ajmeer.ipynb` — Midhun / Ajmeer.
5. `notebooks/lightning_ai/04_tabular_neural_network_mirdula_hashvitha.ipynb` — Mirdula / Hashvitha.

The first notebook saves Git-ignored Parquet files under `data/processed/`. Each training notebook creates a versioned, Git-ignored bundle under `artifacts/<model>/<UTC-run-id>/`, performs a mandatory save/reload prediction test, and can optionally upload the run to private Cloudflare R2 storage.

Share [docs/TEAMMATE_TRAINING_GUIDE.md](docs/TEAMMATE_TRAINING_GUIDE.md) with model owners. See [docs/LIGHTNING_TRAINING_GUIDE.md](docs/LIGHTNING_TRAINING_GUIDE.md) for the complete training guide. The browser-friendly HTML export is kept locally and ignored by Git.

## Cloud architecture

- **Training:** Lightning AI.
- **Model storage:** private Cloudflare R2 bucket.
- **Backend:** FastAPI on Render; lazily loads requested approved models and scores one common input independently.
- **Frontend:** React/Vite on Cloudflare Pages; compares selected V1/V2 outputs side by side.

See [docs/DEPLOYMENT_ARCHITECTURE.md](docs/DEPLOYMENT_ARCHITECTURE.md).

The checked-in Supabase migration, Render Blueprint, Cloudflare Pages build
settings, secret boundaries and local verification commands are explained in
[docs/INTEGRATION_SETUP.md](docs/INTEGRATION_SETUP.md).

Before adding prediction workflows to the React application, run the required
eight-pipeline check in
[docs/MODEL_VERIFICATION_GATE.md](docs/MODEL_VERIFICATION_GATE.md).
The completed local inference foundation and its known boundaries are recorded
in [docs/MILESTONE_1_INFERENCE_REPORT.md](docs/MILESTONE_1_INFERENCE_REPORT.md).
The typed manual prediction, one-row CSV, batch CSV, model-cache, and API error
contracts are documented in
[docs/MILESTONE_2_API_GUIDE.md](docs/MILESTONE_2_API_GUIDE.md).
The strict FIFO held-out replay, Supabase schema, hidden-label boundary, SSE
contract, reproducible dataset upload, and stream tests are documented in
[docs/MILESTONE_3_STREAMING_GUIDE.md](docs/MILESTONE_3_STREAMING_GUIDE.md).
The current one-page CYPHER application keeps Single JSON, CSV Upload, and
strict FIFO Real-time prediction while removing analyst case-management
complexity. Its workflow is documented in
[docs/SIMPLIFIED_APPLICATION_GUIDE.md](docs/SIMPLIFIED_APPLICATION_GUIDE.md).
The original Milestone 4 implementation remains documented in
[docs/MILESTONE_4_FRONTEND_GUIDE.md](docs/MILESTONE_4_FRONTEND_GUIDE.md).
The private R2 layout, lazy verified model cache, Render runtime, Cloudflare
Pages release, Supabase cloud dataset, and deployment checklist are documented
in [docs/MILESTONE_5_CLOUD_DEPLOYMENT.md](docs/MILESTONE_5_CLOUD_DEPLOYMENT.md).
