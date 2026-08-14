# Lightning AI notebook runbook

Run `00_shared_data_preparation.ipynb` once. Then notebooks `01`–`04` may be
run independently by their assigned teams because they read the same frozen
Parquet partitions.

| Notebook | Owners | Recommended machine |
| --- | --- | --- |
| `00_shared_data_preparation.ipynb` | Entire team | CPU, 24–32 GB RAM preferred |
| `01_logistic_regression_nanda_khishan.ipynb` | Nanda / Khishan | CPU, high RAM |
| `02_lightgbm_saravana_nebal.ipynb` | Saravana / Nebal | CPU first; GPU optional |
| `03_catboost_midhun_ajmeer.ipynb` | Midhun / Ajmeer | T4 GPU or CPU |
| `04_tabular_neural_network_mirdula_hashvitha.ipynb` | Mirdula / Hashvitha | T4 GPU, high RAM |

Before running, accept the Kaggle competition rules and add
`KAGGLE_API_TOKEN` as a Lightning secret. In Lightning AI, open the profile
menu, choose **Global settings → Secrets → New Secret**, use
`KAGGLE_API_TOKEN` as the name, and paste the token as the value. Restart the
Studio terminal and notebook kernel after saving it. Do not paste the token
into a cell.

Each model notebook has `FAST_RUN = False`. A teammate may temporarily set it
to `True` to check that code runs, but fast-run metrics must never be presented
as final results.

The shareable instructions are in `docs/TEAMMATE_TRAINING_GUIDE.md`.
A browser-friendly HTML export may be kept locally, but it is intentionally
ignored by Git.
Complete technical instructions are in `docs/LIGHTNING_TRAINING_GUIDE.md`.
