# Simple teammate guide: train one fraud model in Lightning AI

Follow these steps in order. One person from each pair should perform the
official final run and share the result ZIP with Midhun.

## 1. Find your notebook

| Team | Notebook | Machine |
| --- | --- | --- |
| Nanda / Khishan | `01_logistic_regression_nanda_khishan.ipynb` | High-memory CPU |
| Saravana / Nebal | `02_lightgbm_saravana_nebal.ipynb` | High-memory CPU |
| Midhun / Ajmeer | `03_catboost_midhun_ajmeer.ipynb` | T4 GPU |
| Mirdula / Hashvitha | `04_tabular_neural_network_mirdula_hashvitha.ipynb` | T4 GPU |

All notebooks are inside `notebooks/lightning_ai/`.

## 2. Create a Lightning AI Studio

1. Sign in to Lightning AI.
2. Create a new persistent Studio.
3. Give it a simple name such as `fraud-lightgbm` or `fraud-catboost`.
4. Keep this Studio until the final result ZIP has been downloaded.

## 3. Clone the project

Open the Lightning terminal and run:

```bash
git clone https://github.com/midhunprahash-ui/credit-card-fraud-npn.git
cd credit-card-fraud-npn
git switch main
git pull origin main
pip install -r requirements-training.txt
```

Use `main` for official training. Do not train from `develop`.

## 4. Create a Kaggle API token

1. Sign in to Kaggle.
2. Open the IEEE-CIS Fraud Detection competition page.
3. Join the competition and accept its rules.
4. Open your Kaggle account **Settings** page.
5. Find **API Tokens** and select **Generate New Token**.
6. Copy the new token immediately and keep it private.

Never send the token in chat, place it in a screenshot, paste it into a
notebook cell, or commit it to GitHub.

## 5. Add the Kaggle token to Lightning AI Secrets

1. In Lightning AI, select your profile picture in the top-right corner.
2. Open **Global settings**.
3. Select **Secrets**.
4. Select **New Secret**.
5. In the secret name field, enter exactly:

```text
KAGGLE_API_TOKEN
```

6. Paste the Kaggle token into the secret value field.
7. Save the secret.
8. Close and reopen the Studio terminal.
9. Restart the Jupyter notebook kernel.

Do not print the token to test it. Notebook `00` will safely check whether the
secret is available.

## 6. Prepare the data

Open:

```text
notebooks/lightning_ai/00_shared_data_preparation.ipynb
```

Choose **Kernel → Restart Kernel and Run All Cells**.

This notebook downloads the training data, performs the left join, creates the
shared features, makes the chronological splits, and saves them under:

```text
data/processed/
```

Do not continue until notebook `00` finishes without an error. Use a CPU
machine with 24–32 GB system RAM for this step when available.

## 7. Test your assigned notebook

Open your assigned notebook from the table in Step 1. Find this setting:

```python
FAST_RUN = False
```

Temporarily change it to:

```python
FAST_RUN = True
```

Restart the kernel and run every cell. This is only a quick code check. Do not
use fast-run metrics in the presentation.

## 8. Run the official training

Change the setting back to:

```python
FAST_RUN = False
```

Restart the kernel and run every cell again. Do not independently change the
data split, preprocessing rules, features, metrics, or random seed.

The final reload-test cell must pass. It proves that the saved model can be
loaded and used again.

## 9. Find the result folder

The notebook creates one complete result folder:

```text
artifacts/<model-name>/<run-id>/
```

It contains the model, preprocessing information, input feature schema,
threshold, metrics, predictions, configuration, interpretation output, and a
checksum manifest. Share the whole folder, not only the model file.

## 10. Create the ZIP file

The notebook prints the exact result folder at the end. In the terminal, run:

```bash
zip -r model_results.zip artifacts/<model-name>/<run-id>/
```

Replace `<model-name>` and `<run-id>` with the printed values. Example:

```bash
zip -r catboost_results.zip artifacts/catboost/20260814_143000/
```

Download the ZIP from Lightning AI and send it to Midhun.

## Final checklist

- Notebook `00` completed successfully.
- The correct assigned model notebook was used.
- The official run used `FAST_RUN = False`.
- The reload test passed.
- The complete run folder was zipped.
- No Kaggle or cloud secret is inside the ZIP.
- The final ZIP was sent to Midhun.
