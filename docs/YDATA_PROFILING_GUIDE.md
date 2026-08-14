# Interactive EDA HTML report

This project includes a reproducible `ydata-profiling` report for the labelled
IEEE-CIS training data after the required left join.

## Exactly which data is analyzed?

The report uses only:

- `train_transaction.csv` — 590,540 labelled transactions.
- `train_identity.csv` — optional device and identity data for 144,233 of those
  transactions.

They are joined as follows:

```text
train_transaction LEFT JOIN train_identity USING (TransactionID)
```

This retains all 590,540 training transactions. It does **not** load either
Kaggle competition test file. The report also adds `has_identity`, which is `1`
when an identity record exists and `0` otherwise.

## Why the default report is memory-safe

The joined table contains 435 columns after adding `has_identity`, and almost
45% of its cells are missing. Calculating every pairwise correlation and
interaction for 590,540 rows can exhaust notebook memory and produce an
unmanageably large HTML file.

The default command therefore profiles **all rows and all columns**, while
using YData's `minimal=True` mode. It includes the overview, data types,
descriptive statistics, distributions, unique values, missing values, alerts,
duplicates, and sample rows. It avoids the most expensive pairwise analyses.
The existing `docs/EDA_REPORT.md` contains the targeted fraud relationships and
correlation screen needed for modelling decisions.

## Generate the full-row report in Lightning AI

From a terminal opened at the repository root:

```bash
python -m pip install -r requirements-eda.txt
python src/generate_ydata_profile.py
```

The output is:

```text
reports/generated/ieee_cis_train_left_join_profile.html
```

A local reference copy may also be kept at:

```text
reports/eda/ieee_cis_train_left_join_profile.html
```

Open that file in Lightning Studio's file browser and download it, or serve it
temporarily from the repository root:

```bash
python -m http.server 8000
```

Then open the Studio port URL and navigate to the report. Both generated and
local reference HTML reports are ignored by Git because they are large and can
always be recreated from the script.

## Optional deeper report on a representative sample

For pairwise analysis, generate a standard YData report using a deterministic,
class-stratified 50,000-row sample:

```bash
python src/generate_ydata_profile.py \
  --sample-rows 50000 \
  --standard \
  --output reports/generated/ieee_cis_train_deep_sample_profile.html
```

The sample preserves the legitimate/fraud class proportions and is sorted back
into `TransactionDT` order. Sampling is used only to make interactive pairwise
analysis practical; it is not used to train or evaluate the final models.

## What to look for in the page

1. Confirm 590,540 rows remain after the left join.
2. Inspect the `isFraud` imbalance: roughly 3.5% fraud.
3. Review missingness, especially identity fields and the V/D groups.
4. Review categorical cardinality before selecting an encoding method.
5. Look for constant, near-constant, duplicate, highly skewed, and highly
   missing columns in the Alerts section.
6. Use this page to form hypotheses. Final feature selection must still be
   validated with chronological train/validation data, because univariate EDA
   cannot reveal every nonlinear or interaction-based fraud signal.

## Common failure: the process is killed or the kernel restarts

This indicates insufficient RAM. Use the deep sample command first, reduce
`--sample-rows` to `25000`, or select a Lightning machine with more CPU RAM.
The T4 GPU does not accelerate YData profiling; this stage mainly uses CPU and
system memory. GPU becomes useful during neural-network and supported
gradient-boosting training.
