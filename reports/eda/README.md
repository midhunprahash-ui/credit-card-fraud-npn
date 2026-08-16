# Interactive EDA report

`ieee_cis_train_left_join_profile.html`, when generated locally, is the
self-contained YData Profiling report for the IEEE-CIS labelled training data.
The large HTML file is intentionally ignored by Git and can be regenerated.

It was generated from all 590,540 rows after:

```text
train_transaction LEFT JOIN train_identity USING (TransactionID)
```

The report contains 435 columns, including the derived `has_identity` flag.
It does not use `test_transaction.csv` or `test_identity.csv`.

Open the HTML file in a web browser. To regenerate it from the repository root:

```bash
python -m pip install -r requirements-eda.txt
python src/generate_ydata_profile.py
```

See [the YData profiling guide](../../docs/YDATA_PROFILING_GUIDE.md) for the
memory rationale and the optional deeper sample-profile command.
