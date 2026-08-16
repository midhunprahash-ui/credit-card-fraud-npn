# Project asset inventory

Last audited: 16 August 2026 (Asia/Kolkata)

This file explains where every important training and deployment asset is kept.
Large datasets and trained models are intentionally ignored by Git. The source
notebooks, pipeline code, configuration and documentation remain versioned.

## Project structure

```text
credit-card-fraud-npn/
├── api/                             # FastAPI prediction, explanation and FIFO API
├── artifacts/
│   ├── catboost/                   # Version 1 CatBoost runs
│   ├── lightgbm/                   # Version 1 LightGBM runs
│   ├── logistic_regression/        # Version 1 Logistic Regression run
│   ├── neural_network/             # Version 1 neural-network runs
│   ├── team_deliveries/
│   │   ├── archives/               # Original Version 1 team archives
│   │   └── notebooks/
│   │       ├── v1/                 # Executed Version 1 notebooks
│   │       └── v2/                 # Executed Version 2 notebooks
│   └── v2/
│       ├── data/                   # Version 2 processed-data package
│       ├── lightgbm/               # Extracted run and original archive
│       ├── catboost/               # Selected run, replicate and archives
│       ├── logistic_regression/     # Extracted Version 2 run and archive
│       └── neural_network/          # Extracted run and original archive
├── config/
│   ├── model_registry.json         # Approved Version 1 runs
│   └── model_registry_v2.json      # Current Version 2 run status
├── data/
│   ├── raw/                        # Kaggle files; not committed
│   ├── processed/                  # Re-creatable processed data; not committed
│   └── samples/
│       └── kaggle_inference_sample_100.csv # Safe 100-row, 433-column upload sample
├── docs/                           # Human-readable project documentation
├── frontend/                       # React/Vite CYPHER application
├── notebooks/
│   └── lightning_ai/
│       ├── 00...04                 # Clean Version 1 training notebooks
│       └── v2/10...15              # Clean Version 2 notebooks
├── src/fraud_pipeline/             # Shared preprocessing/training code
└── tests/                          # Pipeline and artifact tests
```

## Version 1 status

All four Version 1 approaches are complete and saved.

| Model | Selected run | Model file | Status |
| --- | --- | --- | --- |
| Logistic Regression | `20260814T044445Z` | `model.joblib` | Complete |
| LightGBM | `20260814T050814Z` | `model.txt` | Complete; V1 champion |
| CatBoost | `20260814T043639Z` | `model.cbm` | Complete |
| Neural network | `20260814T051404Z` | `model.pt` | Complete |

The original archives are retained in `artifacts/team_deliveries/archives/`.
The selected runs are declared in `config/model_registry.json`.

## Version 2 status

| Model | Current run | Validation PR-AUC | Test PR-AUC | Status |
| --- | --- | ---: | ---: | --- |
| LightGBM | `20260815T061730Z` | 0.653215 | 0.570442 | Complete |
| CatBoost | `20260815T121042Z` | 0.725072 | 0.607110 | Complete; current V2 champion |
| Neural network | `20260815T130503Z` | 0.517591 | 0.391322 | Complete |
| Logistic Regression | `20260815T133526Z` | 0.397775 | 0.171740 | Complete |
| LightGBM + CatBoost ensemble | — | — | — | Deferred by decision; not required now |

CatBoost run `20260815T134805Z` is retained as a valid replicate. It was not
selected because its validation PR-AUC (0.722845) is slightly below the selected
run. Model selection uses validation results, not the final test period.

## Notebook status

- All clean Version 1 source notebooks are in `notebooks/lightning_ai/`.
- All clean Version 2 source notebooks are in `notebooks/lightning_ai/v2/`.
- Successfully executed notebooks received from training are retained under
  `artifacts/team_deliveries/notebooks/v1/` and `/v2/`.
- The V2 ensemble notebook exists as reproducible source code but has not been
  executed because ensemble training is deferred.

## Required contents of a deployable run

Each run must contain its model, preprocessing object, `feature_schema.json`,
`metrics.json`, `threshold.json`, `training_config.json`, predictions and
`manifest.json`. Neural-network runs additionally require `model_config.json`.
Every currently saved completed run passed the manifest size and SHA-256 audit.

## Items not yet available

1. A trained V2 LightGBM–CatBoost ensemble artifact, intentionally deferred.

This missing optional item does not affect the already completed V1 system or
the four completed standalone V2 models.

## Current deployment and demonstration assets

- `data/samples/kaggle_inference_sample_100.csv` contains 100 real official
  Kaggle test transactions, all 433 raw input columns, and no `isFraud` label.
- `config/deployment_artifacts.json` pins the R2 object prefixes, manifests,
  counts, sizes, and SHA-256 values used by the lazy model manager.
- `config/model_catalog.json` contains safe display metrics that do not require
  loading model binaries.
- `frontend/dist/` is generated and not the source of truth. Cloudflare Pages
  must be rebuilt from `frontend/src/` with the production `VITE_API_URL`.
- Full labelled held-out data and all model binaries remain Git-ignored. The
  600-row labelled replay is retained for controlled evaluation but is not
  offered by the simplified public UI.
