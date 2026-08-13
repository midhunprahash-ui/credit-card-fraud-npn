"""Reproducible exploratory analysis for the IEEE-CIS fraud data.

Run from the repository root:
    <bundled-python> src/eda.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/raw/ieee-fraud-detection"
OUTPUT = ROOT / "docs/EDA_REPORT.md"


def table_line(items: list[str]) -> str:
    return " | ".join(items)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    result = [table_line(headers), table_line(["---"] * len(headers))]
    result.extend(table_line([str(value) for value in row]) for row in rows)
    return "\n".join(result)


def profile(name: str, frame: pd.DataFrame) -> dict[str, object]:
    null_rate = frame.isna().mean()
    nunique = frame.nunique(dropna=True)
    return {
        "name": name,
        "rows": len(frame),
        "columns": frame.shape[1],
        "numeric": frame.select_dtypes(include=np.number).shape[1],
        "categorical": frame.select_dtypes(exclude=np.number).shape[1],
        "duplicates": int(frame.duplicated().sum()),
        "all_missing": int((null_rate == 1).sum()),
        "constant": int((nunique <= 1).sum()),
        "missing_cells": int(frame.isna().sum().sum()),
        "missing_rate": float(frame.isna().mean().mean()),
        "null_rate": null_rate,
        "nunique": nunique,
    }


def main() -> None:
    train_tx = pd.read_csv(DATA / "train_transaction.csv")
    train_id = pd.read_csv(DATA / "train_identity.csv")
    test_tx = pd.read_csv(DATA / "test_transaction.csv")
    test_id = pd.read_csv(DATA / "test_identity.csv")
    submission = pd.read_csv(DATA / "sample_submission.csv")

    tx_profile = profile("train_transaction", train_tx)
    id_profile = profile("train_identity", train_id)
    test_tx_profile = profile("test_transaction", test_tx)
    test_id_profile = profile("test_identity", test_id)

    merged = train_tx.merge(train_id, on="TransactionID", how="left", indicator=True)
    target = train_tx["isFraud"]
    fraud_rate = target.mean()

    numeric = train_tx.select_dtypes(include=np.number)
    fraud_by_product = (
        train_tx.groupby("ProductCD", observed=True)["isFraud"]
        .agg(["count", "sum", "mean"])
        .sort_values("mean", ascending=False)
    )
    identity_coverage = (
        merged.assign(has_identity=merged["_merge"].eq("both"))
        .groupby("has_identity", observed=True)["isFraud"]
        .agg(["count", "sum", "mean"])
        .sort_index(ascending=False)
    )
    amount_by_label = train_tx.groupby("isFraud")["TransactionAmt"].agg(
        ["count", "mean", "median", "min", "max"]
    )
    day = (train_tx["TransactionDT"] // 86_400).astype("int32")
    temporal = (
        pd.DataFrame({"day": day, "isFraud": target})
        .groupby("day", observed=True)["isFraud"]
        .agg(["count", "mean"])
    )

    missing_top = pd.DataFrame(
        {
            "missing_pct": merged.isna().mean() * 100,
            "dtype": merged.dtypes.astype(str),
            "unique_values": merged.nunique(dropna=True),
        }
    ).sort_values("missing_pct", ascending=False)
    missing_top = missing_top[missing_top["missing_pct"] > 0].head(25)

    categorical = train_tx.select_dtypes(exclude=np.number).columns.tolist()
    cardinality = pd.DataFrame(
        {
            "unique_values": train_tx[categorical].nunique(dropna=True),
            "missing_pct": train_tx[categorical].isna().mean() * 100,
        }
    ).sort_values("unique_values", ascending=False)

    corr = numeric.corrwith(target).drop("isFraud").abs().sort_values(ascending=False)
    id_columns = [column for column in train_id.columns if column != "TransactionID"]
    id_null = train_id[id_columns].isna().mean().mean() * 100
    unseen_test_columns = sorted(set(test_tx.columns) - set(train_tx.columns))
    train_only_columns = sorted(set(train_tx.columns) - set(test_tx.columns))

    lines = [
        "# IEEE-CIS Fraud Detection: Exploratory Data Analysis",
        "",
        "> Generated from the supplied Kaggle files on 2026-08-13. Re-run `src/eda.py` after data or analysis changes.",
        "",
        "## Executive summary",
        "",
        f"- The labelled training transaction table has **{len(train_tx):,} rows** and **{train_tx.shape[1]:,} columns**; fraud prevalence is **{fraud_rate:.2%}** ({int(target.sum()):,} fraud vs. {int((1-target).sum()):,} non-fraud).",
        f"- Only **{len(train_id) / len(train_tx):.2%}** of training transactions have an identity-table row. The correct integration is therefore a left join on `TransactionID`, retaining all {len(train_tx):,} transactions.",
        f"- The joined training data has **{merged.shape[1]:,} columns** and is highly sparse: **{merged.isna().mean().mean():.2%}** of all cells are missing. Missingness is itself a useful fraud signal and must be modelled carefully.",
        "- This is an imbalanced binary-classification problem. Do not use accuracy as the headline metric; prioritize ROC-AUC, PR-AUC, precision/recall, and recall at a fixed review capacity.",
        "- `TransactionDT` is a relative timestamp. Use chronological splits and fit encoders/features only on earlier training rows to avoid leakage.",
        "",
        "## 1. Source files and schema",
        "",
        markdown_table(
            ["File", "Rows", "Columns", "Numeric", "Categorical", "Exact duplicate rows"],
            [
                [p["name"], f'{p["rows"]:,}', p["columns"], p["numeric"], p["categorical"], f'{p["duplicates"]:,}']
                for p in [tx_profile, id_profile, test_tx_profile, test_id_profile]
            ],
        ),
        "",
        f"`sample_submission.csv` has {len(submission):,} rows and columns: `{', '.join(submission.columns)}`.",
        "",
        "### Train/test compatibility",
        "",
        f"- Train-only columns: `{', '.join(train_only_columns)}`. This should be only the label.",
        f"- Test-only columns: `{', '.join(unseen_test_columns) if unseen_test_columns else 'None'}`.",
        "- Use an identical feature-engineering pipeline for train and test; remove `isFraud` from the training feature matrix.",
        "",
        "## 2. Merge analysis",
        "",
        f"The transaction and identity tables share `TransactionID`. `TransactionID` is unique in `train_transaction` ({train_tx.TransactionID.nunique():,}/{len(train_tx):,}) and in `train_identity` ({train_id.TransactionID.nunique():,}/{len(train_id):,}).",
        "",
        markdown_table(
            ["Identity available", "Transactions", "Fraud cases", "Fraud rate"],
            [[str(index), f'{row["count"]:,.0f}', f'{row["sum"]:,.0f}', f'{row["mean"]:.2%}'] for index, row in identity_coverage.iterrows()],
        ),
        "",
        f"The identity table itself has {len(id_columns):,} usable feature columns after excluding the join key, and its average per-column missing rate is {id_null:.2f}%.",
        "",
        "## 3. Target distribution and imbalance",
        "",
        markdown_table(
            ["Class", "Meaning", "Transactions", "Share"],
            [
                ["0", "Legitimate", f'{int((target == 0).sum()):,}', f'{(target == 0).mean():.2%}'],
                ["1", "Fraud", f'{int((target == 1).sum()):,}', f'{fraud_rate:.2%}'],
            ],
        ),
        "",
        f"A class-weight starting point for a tree model is approximately **{(target.eq(0).sum() / target.eq(1).sum()):.2f}** (`negative / positive`). Tune this value on chronological validation data.",
        "",
        "## 4. Transaction amount and time",
        "",
        markdown_table(
            ["isFraud", "Rows", "Mean amount", "Median amount", "Minimum", "Maximum"],
            [[int(index), f'{row["count"]:,.0f}', f'${row["mean"]:,.2f}', f'${row["median"]:,.2f}', f'${row["min"]:,.2f}', f'${row["max"]:,.2f}'] for index, row in amount_by_label.iterrows()],
        ),
        "",
        f"`TransactionDT` spans {train_tx.TransactionDT.min():,} to {train_tx.TransactionDT.max():,} seconds, or approximately {day.min()} to {day.max()} relative days ({len(temporal):,} observed day buckets). Daily fraud rate ranges from {temporal['mean'].min():.2%} to {temporal['mean'].max():.2%}; this confirms time variation and supports chronological validation.",
        "",
        "## 5. Product-code fraud rates",
        "",
        markdown_table(
            ["ProductCD", "Transactions", "Fraud cases", "Fraud rate"],
            [[index, f'{row["count"]:,.0f}', f'{row["sum"]:,.0f}', f'{row["mean"]:.2%}'] for index, row in fraud_by_product.iterrows()],
        ),
        "",
        "ProductCD has materially different fraud rates by category, making it an important categorical input. The relationship must be learned on training partitions only.",
        "",
        "## 6. Missing data",
        "",
        f"Training transaction data alone contains {tx_profile['missing_cells']:,} missing cells ({tx_profile['missing_rate']:.2%} average cell missingness); the merged table contains {merged.isna().sum().sum():,} missing cells.",
        "",
        markdown_table(
            ["Column", "Missing %", "Data type", "Unique non-null values"],
            [[index, f'{row["missing_pct"]:.2f}%', row["dtype"], f'{row["unique_values"]:,}'] for index, row in missing_top.iterrows()],
        ),
        "",
        "Recommended handling: preserve an explicit `MISSING` category for categorical fields; use a robust numeric imputation strategy or a model with native missing-value handling; and add missingness indicators for key fields. Do not drop every sparse column blindly—absence of device/identity information can carry signal.",
        "",
        "## 7. Categorical cardinality",
        "",
        markdown_table(
            ["Column", "Unique observed values", "Missing %"],
            [[index, f'{row["unique_values"]:,}', f'{row["missing_pct"]:.2f}%'] for index, row in cardinality.head(20).iterrows()],
        ),
        "",
        "High-cardinality columns should not be blindly one-hot encoded. Prefer CatBoost native categorical handling, or training-only frequency encoding / carefully out-of-fold target encoding. Group rare categories as `OTHER` when appropriate.",
        "",
        "## 8. Numerical association screen",
        "",
        "The following is an absolute Pearson-correlation screen with the target. It is diagnostic only: fraud patterns are nonlinear, and a low linear correlation does not mean a feature is unhelpful.",
        "",
        markdown_table(
            ["Feature", "Absolute correlation with isFraud"], [[index, f'{value:.4f}'] for index, value in corr.head(20).items()]),
        "",
        "## 9. Modelling recommendations from the EDA",
        "",
        "1. Start with CatBoost (native categoricals) or LightGBM (encoded categoricals) as the baseline model.",
        "2. Left-join identities and create `has_identity`; never inner-join the tables.",
        "3. Use `TransactionDT` to split earliest 70% for training, next 15% for validation, latest 15% for final testing.",
        "4. Use class weights; begin near the calculated negative-to-positive ratio and tune against PR-AUC and reviewer capacity.",
        "5. Engineer amount, time, card/address/email/device composite, frequency, and historical features. Historical aggregates must use earlier rows only.",
        "6. Save the entire preprocessing schema with the model so API inputs receive exactly the training-time transformation.",
        "7. Select a threshold based on business trade-offs: e.g., block very-high scores and route medium scores to an analyst queue.",
        "",
        "## 10. Leakage and deployment checklist",
        "",
        "- Never random-split this time-ordered data for the final claim.",
        "- Fit imputers, category mappings, scalers, and frequency maps on the training fold only.",
        "- For online scoring, ensure every historical feature is computed using data available before the transaction being scored.",
        "- Do not expose `isFraud` in API input; it is a training label only.",
        "- Keep Kaggle files and credential files out of Git (already covered by `.gitignore`).",
        "",
        "## Reproducibility",
        "",
        "The calculations in this report are generated by `src/eda.py` from the supplied files in `data/raw/ieee-fraud-detection/`. Run it with the project Python environment once it is created. The raw data and extracted CSVs are intentionally ignored by Git.",
    ]
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
