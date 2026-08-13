"""Generate a data dictionary from the supplied IEEE-CIS source CSV files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/raw/ieee-fraud-detection"
OUTPUT = ROOT / "docs/DATA_DICTIONARY.md"


def group_and_description(column: str) -> tuple[str, str]:
    if column == "TransactionID":
        return "Identifier", "Unique transaction identifier and join key. Do not use as a deployment feature."
    if column == "isFraud":
        return "Target", "Training label: 1 means fraud and 0 means legitimate. Not available for future scoring."
    known = {
        "TransactionDT": ("Transaction", "Relative time in seconds from a reference point; not a real calendar timestamp."),
        "TransactionAmt": ("Transaction", "Transaction amount."),
        "ProductCD": ("Transaction", "Anonymized product/payment category code."),
        "card1": ("Payment card", "Anonymized payment-card attribute 1; identifier-like numeric field."),
        "card2": ("Payment card", "Anonymized payment-card attribute 2."),
        "card3": ("Payment card", "Anonymized payment-card attribute 3."),
        "card4": ("Payment card", "Card network/category, e.g. visa, mastercard, american express, discover."),
        "card5": ("Payment card", "Anonymized payment-card attribute 5."),
        "card6": ("Payment card", "Card type/category, e.g. credit, debit, charge card."),
        "addr1": ("Address", "Anonymized billing/address attribute 1."),
        "addr2": ("Address", "Anonymized billing/address attribute 2."),
        "dist1": ("Distance", "Anonymized distance attribute 1."),
        "dist2": ("Distance", "Anonymized distance attribute 2."),
        "P_emaildomain": ("Email", "Purchaser email-domain category."),
        "R_emaildomain": ("Email", "Recipient email-domain category."),
        "DeviceType": ("Device identity", "Device class, commonly desktop or mobile."),
        "DeviceInfo": ("Device identity", "Anonymized/raw device-information string, often device family or model."),
    }
    if column in known:
        return known[column]
    if column.startswith("C") and column[1:].isdigit():
        return "Count feature", "Anonymized count-like transaction feature; exact business meaning is not disclosed."
    if column.startswith("D") and column[1:].isdigit():
        return "Time delta", "Anonymized time-delta feature; exact business meaning is not disclosed."
    if column.startswith("M") and column[1:].isdigit():
        return "Match flag", "Anonymized yes/no match-style feature; exact business meaning is not disclosed."
    if column.startswith("V") and column[1:].isdigit():
        return "Vesta engineered", "Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed."
    if column.startswith("id_"):
        return "Device identity", "Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples."
    return "Other", "Anonymized competition field; consult Kaggle documentation if a precise definition is required."


def examples(series: pd.Series) -> str:
    values = series.dropna().unique()[:5]
    if len(values) == 0:
        return "No non-null values"
    return ", ".join(str(value).replace("|", "/")[:45] for value in values)


def main() -> None:
    tx = pd.read_csv(DATA / "train_transaction.csv")
    identity = pd.read_csv(DATA / "train_identity.csv")
    merged = tx.merge(identity, on="TransactionID", how="left")
    rows: list[str] = []
    for column in merged.columns:
        group, description = group_and_description(column)
        series = merged[column]
        values = series.nunique(dropna=True)
        rows.append(
            f"| `{column}` | {group} | `{series.dtype}` | {series.isna().mean():.2%} | {values:,} | {examples(series)} | {description} |"
        )
    header = [
        "# IEEE-CIS Merged Data Dictionary",
        "",
        "> Generated from the supplied training CSV files by `src/generate_data_dictionary.py`. The left-joined table contains 590,540 rows and 434 feature/input columns plus the `isFraud` target (435 columns total).",
        "",
        "## How to read this guide",
        "",
        "- **Value examples** are real examples from the supplied training data, limited to five values per feature.",
        "- Many fields are intentionally anonymized by the competition. For these (`V*`, `C*`, `D*`, `M*`, and most `id_*`), their precise business meaning is not public. Their group describes the available dataset convention; it does not guess a meaning.",
        "- Missing values are expected. A missing value does not mean the row should be removed; it can be informative for fraud detection.",
        "- `TransactionID` is the join key and should not be a predictive deployment input. `isFraud` is the target label and must never be supplied to the prediction API.",
        "",
        "## Complete column list",
        "",
        "| Feature | Group | Stored type | Missing | Unique non-null values | Example values | Meaning / interpretation |",
        "| --- | --- | --- | ---: | ---: | --- | --- |",
        *rows,
        "",
        "## Features added later by our pipeline",
        "",
        "Lightning notebook 00 adds row-level derived features after this source-data dictionary: `has_identity`, amount transforms, missingness-family counts, relative time phases, `card_1_2`, `address_1_2`, and `email_pair`. Their exact definitions and model-specific representations are in [FEATURE_ENGINEERING_GUIDE.md](FEATURE_ENGINEERING_GUIDE.md).",
    ]
    OUTPUT.write_text("\n".join(header) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT} ({len(merged.columns)} columns)")


if __name__ == "__main__":
    main()
