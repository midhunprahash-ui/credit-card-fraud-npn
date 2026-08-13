# Lightning AI notebook runbook

Run `00_shared_data_preparation.ipynb` once. Then notebooks `01`–`04` may be
run independently by their assigned teams because they read the same frozen
Parquet partitions.

| Notebook | Owners | Recommended machine |
| --- | --- | --- |
| `00_shared_data_preparation.ipynb` | Entire team | CPU, 24–32 GB RAM preferred |
| `01_logistic_regression.ipynb` | Nanda / Khishan | CPU, high RAM |
| `02_lightgbm.ipynb` | Nebal / Ajmeer | CPU first; GPU optional |
| `03_catboost.ipynb` | Midhun / Saravana | T4 GPU or CPU |
| `04_tabular_neural_network.ipynb` | Mirdula / Hashvitha | T4 GPU, high RAM |

Before running, accept the Kaggle competition rules and add
`KAGGLE_API_TOKEN` as a Lightning secret. Do not paste the token into a cell.

Each model notebook has `FAST_RUN = False`. A teammate may temporarily set it
to `True` to check that code runs, but fast-run metrics must never be presented
as final results.

Complete instructions are in `docs/LIGHTNING_TRAINING_GUIDE.md`.
