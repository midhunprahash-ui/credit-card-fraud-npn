# IEEE-CIS Merged Data Dictionary

> Generated from the supplied training CSV files by `src/generate_data_dictionary.py`. The left-joined table contains 590,540 rows and 434 feature/input columns plus the `isFraud` target (435 columns total).

## How to read this guide

- **Value examples** are real examples from the supplied training data, limited to five values per feature.
- Many fields are intentionally anonymized by the competition. For these (`V*`, `C*`, `D*`, `M*`, and most `id_*`), their precise business meaning is not public. Their group describes the available dataset convention; it does not guess a meaning.
- Missing values are expected. A missing value does not mean the row should be removed; it can be informative for fraud detection.
- `TransactionID` is the join key and should not be a predictive deployment input. `isFraud` is the target label and must never be supplied to the prediction API.

## Complete column list

| Feature | Group | Stored type | Missing | Unique non-null values | Example values | Meaning / interpretation |
| --- | --- | --- | ---: | ---: | --- | --- |
| `TransactionID` | Identifier | `int64` | 0.00% | 590,540 | 2987000, 2987001, 2987002, 2987003, 2987004 | Unique transaction identifier and join key. Do not use as a deployment feature. |
| `isFraud` | Target | `int64` | 0.00% | 2 | 0, 1 | Training label: 1 means fraud and 0 means legitimate. Not available for future scoring. |
| `TransactionDT` | Transaction | `int64` | 0.00% | 573,349 | 86400, 86401, 86469, 86499, 86506 | Relative time in seconds from a reference point; not a real calendar timestamp. |
| `TransactionAmt` | Transaction | `float64` | 0.00% | 20,902 | 68.5, 29.0, 59.0, 50.0, 49.0 | Transaction amount. |
| `ProductCD` | Transaction | `object` | 0.00% | 5 | W, H, C, S, R | Anonymized product/payment category code. |
| `card1` | Payment card | `int64` | 0.00% | 13,553 | 13926, 2755, 4663, 18132, 4497 | Anonymized payment-card attribute 1; identifier-like numeric field. |
| `card2` | Payment card | `float64` | 1.51% | 500 | 404.0, 490.0, 567.0, 514.0, 555.0 | Anonymized payment-card attribute 2. |
| `card3` | Payment card | `float64` | 0.27% | 114 | 150.0, 117.0, 185.0, 143.0, 144.0 | Anonymized payment-card attribute 3. |
| `card4` | Payment card | `object` | 0.27% | 4 | discover, mastercard, visa, american express | Card network/category, e.g. visa, mastercard, american express, discover. |
| `card5` | Payment card | `float64` | 0.72% | 119 | 142.0, 102.0, 166.0, 117.0, 226.0 | Anonymized payment-card attribute 5. |
| `card6` | Payment card | `object` | 0.27% | 4 | credit, debit, debit or credit, charge card | Card type/category, e.g. credit, debit, charge card. |
| `addr1` | Address | `float64` | 11.13% | 332 | 315.0, 325.0, 330.0, 476.0, 420.0 | Anonymized billing/address attribute 1. |
| `addr2` | Address | `float64` | 11.13% | 74 | 87.0, 96.0, 35.0, 60.0, 98.0 | Anonymized billing/address attribute 2. |
| `dist1` | Distance | `float64` | 59.65% | 2,651 | 19.0, 287.0, 36.0, 0.0, 3.0 | Anonymized distance attribute 1. |
| `dist2` | Distance | `float64` | 93.63% | 1,751 | 30.0, 98.0, 149.0, 84.0, 100.0 | Anonymized distance attribute 2. |
| `P_emaildomain` | Email | `object` | 15.99% | 59 | gmail.com, outlook.com, yahoo.com, mail.com, anonymous.com | Purchaser email-domain category. |
| `R_emaildomain` | Email | `object` | 76.75% | 60 | gmail.com, hotmail.com, outlook.com, anonymous.com, charter.net | Recipient email-domain category. |
| `C1` | Count feature | `float64` | 0.00% | 1,657 | 1.0, 2.0, 4.0, 6.0, 127.0 | Anonymized count-like transaction feature; exact business meaning is not disclosed. |
| `C2` | Count feature | `float64` | 0.00% | 1,216 | 1.0, 5.0, 2.0, 4.0, 120.0 | Anonymized count-like transaction feature; exact business meaning is not disclosed. |
| `C3` | Count feature | `float64` | 0.00% | 27 | 0.0, 1.0, 8.0, 3.0, 2.0 | Anonymized count-like transaction feature; exact business meaning is not disclosed. |
| `C4` | Count feature | `float64` | 0.00% | 1,260 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized count-like transaction feature; exact business meaning is not disclosed. |
| `C5` | Count feature | `float64` | 0.00% | 319 | 0.0, 2.0, 1.0, 168.0, 3.0 | Anonymized count-like transaction feature; exact business meaning is not disclosed. |
| `C6` | Count feature | `float64` | 0.00% | 1,328 | 1.0, 4.0, 3.0, 5.0, 7.0 | Anonymized count-like transaction feature; exact business meaning is not disclosed. |
| `C7` | Count feature | `float64` | 0.00% | 1,103 | 0.0, 1.0, 2.0, 4.0, 46.0 | Anonymized count-like transaction feature; exact business meaning is not disclosed. |
| `C8` | Count feature | `float64` | 0.00% | 1,253 | 0.0, 1.0, 6.0, 2.0, 5.0 | Anonymized count-like transaction feature; exact business meaning is not disclosed. |
| `C9` | Count feature | `float64` | 0.00% | 205 | 1.0, 0.0, 3.0, 2.0, 81.0 | Anonymized count-like transaction feature; exact business meaning is not disclosed. |
| `C10` | Count feature | `float64` | 0.00% | 1,231 | 0.0, 1.0, 93.0, 2.0, 11.0 | Anonymized count-like transaction feature; exact business meaning is not disclosed. |
| `C11` | Count feature | `float64` | 0.00% | 1,476 | 2.0, 1.0, 5.0, 3.0, 80.0 | Anonymized count-like transaction feature; exact business meaning is not disclosed. |
| `C12` | Count feature | `float64` | 0.00% | 1,199 | 0.0, 2.0, 1.0, 4.0, 3.0 | Anonymized count-like transaction feature; exact business meaning is not disclosed. |
| `C13` | Count feature | `float64` | 0.00% | 1,597 | 1.0, 25.0, 12.0, 2.0, 6.0 | Anonymized count-like transaction feature; exact business meaning is not disclosed. |
| `C14` | Count feature | `float64` | 0.00% | 1,108 | 1.0, 2.0, 3.0, 6.0, 111.0 | Anonymized count-like transaction feature; exact business meaning is not disclosed. |
| `D1` | Time delta | `float64` | 0.21% | 641 | 14.0, 0.0, 112.0, 61.0, 1.0 | Anonymized time-delta feature; exact business meaning is not disclosed. |
| `D2` | Time delta | `float64` | 47.55% | 641 | 112.0, 61.0, 1.0, 72.0, 46.0 | Anonymized time-delta feature; exact business meaning is not disclosed. |
| `D3` | Time delta | `float64` | 44.51% | 649 | 13.0, 0.0, 30.0, 11.0, 10.0 | Anonymized time-delta feature; exact business meaning is not disclosed. |
| `D4` | Time delta | `float64` | 28.60% | 808 | 0.0, 94.0, 318.0, 107.0, 45.0 | Anonymized time-delta feature; exact business meaning is not disclosed. |
| `D5` | Time delta | `float64` | 52.47% | 688 | 0.0, 30.0, 11.0, 10.0, 2.0 | Anonymized time-delta feature; exact business meaning is not disclosed. |
| `D6` | Time delta | `float64` | 87.61% | 829 | 0.0, 537.0, 35.0, 216.0, 163.0 | Anonymized time-delta feature; exact business meaning is not disclosed. |
| `D7` | Time delta | `float64` | 93.41% | 597 | 0.0, 4.0, 8.0, 163.0, 48.0 | Anonymized time-delta feature; exact business meaning is not disclosed. |
| `D8` | Time delta | `float64` | 87.31% | 12,353 | 83.0, 26.0, 21.0, 29.0, 189.0 | Anonymized time-delta feature; exact business meaning is not disclosed. |
| `D9` | Time delta | `float64` | 87.31% | 24 | 0.0, 0.0416660010814666, 0.0833330005407333, 0.125, 0.1666660010814666 | Anonymized time-delta feature; exact business meaning is not disclosed. |
| `D10` | Time delta | `float64` | 12.87% | 818 | 13.0, 0.0, 84.0, 40.0, 107.0 | Anonymized time-delta feature; exact business meaning is not disclosed. |
| `D11` | Time delta | `float64` | 47.29% | 676 | 13.0, 315.0, 0.0, 302.0, 423.0 | Anonymized time-delta feature; exact business meaning is not disclosed. |
| `D12` | Time delta | `float64` | 89.04% | 635 | 0.0, 35.0, 163.0, 398.0, 24.0 | Anonymized time-delta feature; exact business meaning is not disclosed. |
| `D13` | Time delta | `float64` | 89.51% | 577 | 0.0, 24.0, 18.0, 21.0, 58.0 | Anonymized time-delta feature; exact business meaning is not disclosed. |
| `D14` | Time delta | `float64` | 89.47% | 802 | 0.0, 98.0, 97.0, 2.0, 18.0 | Anonymized time-delta feature; exact business meaning is not disclosed. |
| `D15` | Time delta | `float64` | 15.09% | 859 | 0.0, 315.0, 111.0, 318.0, 107.0 | Anonymized time-delta feature; exact business meaning is not disclosed. |
| `M1` | Match flag | `object` | 45.91% | 2 | T, F | Anonymized yes/no match-style feature; exact business meaning is not disclosed. |
| `M2` | Match flag | `object` | 45.91% | 2 | T, F | Anonymized yes/no match-style feature; exact business meaning is not disclosed. |
| `M3` | Match flag | `object` | 45.91% | 2 | T, F | Anonymized yes/no match-style feature; exact business meaning is not disclosed. |
| `M4` | Match flag | `object` | 47.66% | 3 | M2, M0, M1 | Anonymized yes/no match-style feature; exact business meaning is not disclosed. |
| `M5` | Match flag | `object` | 59.35% | 2 | F, T | Anonymized yes/no match-style feature; exact business meaning is not disclosed. |
| `M6` | Match flag | `object` | 28.68% | 2 | T, F | Anonymized yes/no match-style feature; exact business meaning is not disclosed. |
| `M7` | Match flag | `object` | 58.64% | 2 | F, T | Anonymized yes/no match-style feature; exact business meaning is not disclosed. |
| `M8` | Match flag | `object` | 58.63% | 2 | F, T | Anonymized yes/no match-style feature; exact business meaning is not disclosed. |
| `M9` | Match flag | `object` | 58.63% | 2 | F, T | Anonymized yes/no match-style feature; exact business meaning is not disclosed. |
| `V1` | Vesta engineered | `float64` | 47.29% | 2 | 1.0, 0.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V2` | Vesta engineered | `float64` | 47.29% | 9 | 1.0, 2.0, 3.0, 0.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V3` | Vesta engineered | `float64` | 47.29% | 10 | 1.0, 2.0, 3.0, 0.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V4` | Vesta engineered | `float64` | 47.29% | 7 | 1.0, 2.0, 0.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V5` | Vesta engineered | `float64` | 47.29% | 7 | 1.0, 2.0, 0.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V6` | Vesta engineered | `float64` | 47.29% | 10 | 1.0, 2.0, 3.0, 0.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V7` | Vesta engineered | `float64` | 47.29% | 10 | 1.0, 2.0, 3.0, 0.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V8` | Vesta engineered | `float64` | 47.29% | 9 | 1.0, 2.0, 3.0, 0.0, 6.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V9` | Vesta engineered | `float64` | 47.29% | 9 | 1.0, 2.0, 3.0, 0.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V10` | Vesta engineered | `float64` | 47.29% | 5 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V11` | Vesta engineered | `float64` | 47.29% | 6 | 0.0, 1.0, 2.0, 4.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V12` | Vesta engineered | `float64` | 12.88% | 4 | 1.0, 0.0, 2.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V13` | Vesta engineered | `float64` | 12.88% | 7 | 1.0, 0.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V14` | Vesta engineered | `float64` | 12.88% | 2 | 1.0, 0.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V15` | Vesta engineered | `float64` | 12.88% | 8 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V16` | Vesta engineered | `float64` | 12.88% | 15 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V17` | Vesta engineered | `float64` | 12.88% | 16 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V18` | Vesta engineered | `float64` | 12.88% | 16 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V19` | Vesta engineered | `float64` | 12.88% | 8 | 1.0, 0.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V20` | Vesta engineered | `float64` | 12.88% | 15 | 1.0, 2.0, 0.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V21` | Vesta engineered | `float64` | 12.88% | 6 | 0.0, 1.0, 2.0, 3.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V22` | Vesta engineered | `float64` | 12.88% | 9 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V23` | Vesta engineered | `float64` | 12.88% | 14 | 1.0, 2.0, 3.0, 0.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V24` | Vesta engineered | `float64` | 12.88% | 14 | 1.0, 3.0, 2.0, 0.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V25` | Vesta engineered | `float64` | 12.88% | 7 | 1.0, 2.0, 0.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V26` | Vesta engineered | `float64` | 12.88% | 13 | 1.0, 2.0, 0.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V27` | Vesta engineered | `float64` | 12.88% | 4 | 0.0, 1.0, 2.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V28` | Vesta engineered | `float64` | 12.88% | 4 | 0.0, 1.0, 2.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V29` | Vesta engineered | `float64` | 12.88% | 6 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V30` | Vesta engineered | `float64` | 12.88% | 8 | 0.0, 1.0, 2.0, 4.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V31` | Vesta engineered | `float64` | 12.88% | 8 | 0.0, 1.0, 3.0, 2.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V32` | Vesta engineered | `float64` | 12.88% | 15 | 0.0, 1.0, 3.0, 2.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V33` | Vesta engineered | `float64` | 12.88% | 7 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V34` | Vesta engineered | `float64` | 12.88% | 13 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V35` | Vesta engineered | `float64` | 28.61% | 4 | 0.0, 1.0, 2.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V36` | Vesta engineered | `float64` | 28.61% | 6 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V37` | Vesta engineered | `float64` | 28.61% | 55 | 1.0, 4.0, 5.0, 2.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V38` | Vesta engineered | `float64` | 28.61% | 55 | 1.0, 4.0, 2.0, 5.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V39` | Vesta engineered | `float64` | 28.61% | 16 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V40` | Vesta engineered | `float64` | 28.61% | 18 | 0.0, 1.0, 2.0, 7.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V41` | Vesta engineered | `float64` | 28.61% | 2 | 1.0, 0.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V42` | Vesta engineered | `float64` | 28.61% | 9 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V43` | Vesta engineered | `float64` | 28.61% | 9 | 0.0, 1.0, 2.0, 3.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V44` | Vesta engineered | `float64` | 28.61% | 49 | 1.0, 2.0, 3.0, 4.0, 0.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V45` | Vesta engineered | `float64` | 28.61% | 49 | 1.0, 2.0, 3.0, 4.0, 0.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V46` | Vesta engineered | `float64` | 28.61% | 7 | 1.0, 2.0, 0.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V47` | Vesta engineered | `float64` | 28.61% | 9 | 1.0, 2.0, 3.0, 0.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V48` | Vesta engineered | `float64` | 28.61% | 6 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V49` | Vesta engineered | `float64` | 28.61% | 6 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V50` | Vesta engineered | `float64` | 28.61% | 6 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V51` | Vesta engineered | `float64` | 28.61% | 7 | 0.0, 2.0, 1.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V52` | Vesta engineered | `float64` | 28.61% | 9 | 0.0, 2.0, 1.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V53` | Vesta engineered | `float64` | 13.06% | 6 | 1.0, 0.0, 2.0, 3.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V54` | Vesta engineered | `float64` | 13.06% | 7 | 1.0, 0.0, 2.0, 3.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V55` | Vesta engineered | `float64` | 13.06% | 18 | 1.0, 4.0, 2.0, 3.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V56` | Vesta engineered | `float64` | 13.06% | 52 | 1.0, 4.0, 2.0, 3.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V57` | Vesta engineered | `float64` | 13.06% | 7 | 0.0, 1.0, 2.0, 6.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V58` | Vesta engineered | `float64` | 13.06% | 11 | 0.0, 1.0, 2.0, 6.0, 7.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V59` | Vesta engineered | `float64` | 13.06% | 17 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V60` | Vesta engineered | `float64` | 13.06% | 17 | 0.0, 1.0, 2.0, 3.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V61` | Vesta engineered | `float64` | 13.06% | 7 | 1.0, 0.0, 2.0, 3.0, 6.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V62` | Vesta engineered | `float64` | 13.06% | 11 | 1.0, 2.0, 0.0, 3.0, 6.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V63` | Vesta engineered | `float64` | 13.06% | 8 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V64` | Vesta engineered | `float64` | 13.06% | 8 | 0.0, 1.0, 2.0, 4.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V65` | Vesta engineered | `float64` | 13.06% | 2 | 1.0, 0.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V66` | Vesta engineered | `float64` | 13.06% | 8 | 1.0, 2.0, 0.0, 5.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V67` | Vesta engineered | `float64` | 13.06% | 9 | 1.0, 2.0, 0.0, 3.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V68` | Vesta engineered | `float64` | 13.06% | 3 | 0.0, 1.0, 2.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V69` | Vesta engineered | `float64` | 13.06% | 6 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V70` | Vesta engineered | `float64` | 13.06% | 7 | 0.0, 1.0, 2.0, 4.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V71` | Vesta engineered | `float64` | 13.06% | 7 | 0.0, 1.0, 2.0, 6.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V72` | Vesta engineered | `float64` | 13.06% | 11 | 0.0, 1.0, 2.0, 6.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V73` | Vesta engineered | `float64` | 13.06% | 8 | 0.0, 2.0, 1.0, 5.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V74` | Vesta engineered | `float64` | 13.06% | 9 | 0.0, 2.0, 1.0, 3.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V75` | Vesta engineered | `float64` | 15.10% | 5 | 1.0, 0.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V76` | Vesta engineered | `float64` | 15.10% | 7 | 1.0, 0.0, 3.0, 2.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V77` | Vesta engineered | `float64` | 15.10% | 31 | 1.0, 3.0, 4.0, 2.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V78` | Vesta engineered | `float64` | 15.10% | 32 | 1.0, 3.0, 2.0, 4.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V79` | Vesta engineered | `float64` | 15.10% | 8 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V80` | Vesta engineered | `float64` | 15.10% | 20 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V81` | Vesta engineered | `float64` | 15.10% | 20 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V82` | Vesta engineered | `float64` | 15.10% | 8 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V83` | Vesta engineered | `float64` | 15.10% | 8 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V84` | Vesta engineered | `float64` | 15.10% | 8 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V85` | Vesta engineered | `float64` | 15.10% | 8 | 0.0, 1.0, 2.0, 3.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V86` | Vesta engineered | `float64` | 15.10% | 31 | 1.0, 2.0, 3.0, 0.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V87` | Vesta engineered | `float64` | 15.10% | 31 | 1.0, 3.0, 2.0, 4.0, 0.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V88` | Vesta engineered | `float64` | 15.10% | 2 | 1.0, 0.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V89` | Vesta engineered | `float64` | 15.10% | 3 | 0.0, 1.0, 2.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V90` | Vesta engineered | `float64` | 15.10% | 6 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V91` | Vesta engineered | `float64` | 15.10% | 7 | 0.0, 1.0, 2.0, 4.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V92` | Vesta engineered | `float64` | 15.10% | 8 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V93` | Vesta engineered | `float64` | 15.10% | 8 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V94` | Vesta engineered | `float64` | 15.10% | 3 | 0.0, 1.0, 2.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V95` | Vesta engineered | `float64` | 0.05% | 881 | 0.0, 1.0, 2.0, 3.0, 8.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V96` | Vesta engineered | `float64` | 0.05% | 1,410 | 1.0, 0.0, 48.0, 2.0, 7.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V97` | Vesta engineered | `float64` | 0.05% | 976 | 0.0, 28.0, 2.0, 1.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V98` | Vesta engineered | `float64` | 0.05% | 13 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V99` | Vesta engineered | `float64` | 0.05% | 89 | 0.0, 10.0, 1.0, 2.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V100` | Vesta engineered | `float64` | 0.05% | 29 | 0.0, 4.0, 1.0, 2.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V101` | Vesta engineered | `float64` | 0.05% | 870 | 0.0, 1.0, 2.0, 3.0, 8.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V102` | Vesta engineered | `float64` | 0.05% | 1,285 | 1.0, 0.0, 38.0, 3.0, 15.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V103` | Vesta engineered | `float64` | 0.05% | 928 | 0.0, 24.0, 1.0, 2.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V104` | Vesta engineered | `float64` | 0.05% | 16 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V105` | Vesta engineered | `float64` | 0.05% | 100 | 0.0, 1.0, 2.0, 4.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V106` | Vesta engineered | `float64` | 0.05% | 56 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V107` | Vesta engineered | `float64` | 0.05% | 2 | 1.0, 0.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V108` | Vesta engineered | `float64` | 0.05% | 8 | 1.0, 2.0, 3.0, 4.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V109` | Vesta engineered | `float64` | 0.05% | 8 | 1.0, 2.0, 3.0, 4.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V110` | Vesta engineered | `float64` | 0.05% | 8 | 1.0, 2.0, 3.0, 4.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V111` | Vesta engineered | `float64` | 0.05% | 10 | 1.0, 2.0, 3.0, 4.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V112` | Vesta engineered | `float64` | 0.05% | 10 | 1.0, 2.0, 3.0, 4.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V113` | Vesta engineered | `float64` | 0.05% | 10 | 1.0, 2.0, 3.0, 4.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V114` | Vesta engineered | `float64` | 0.05% | 7 | 1.0, 2.0, 3.0, 4.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V115` | Vesta engineered | `float64` | 0.05% | 7 | 1.0, 2.0, 3.0, 4.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V116` | Vesta engineered | `float64` | 0.05% | 7 | 1.0, 2.0, 3.0, 4.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V117` | Vesta engineered | `float64` | 0.05% | 4 | 1.0, 2.0, 3.0, 0.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V118` | Vesta engineered | `float64` | 0.05% | 4 | 1.0, 2.0, 3.0, 0.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V119` | Vesta engineered | `float64` | 0.05% | 4 | 1.0, 2.0, 3.0, 0.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V120` | Vesta engineered | `float64` | 0.05% | 4 | 1.0, 2.0, 3.0, 0.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V121` | Vesta engineered | `float64` | 0.05% | 4 | 1.0, 2.0, 3.0, 0.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V122` | Vesta engineered | `float64` | 0.05% | 4 | 1.0, 2.0, 3.0, 0.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V123` | Vesta engineered | `float64` | 0.05% | 14 | 1.0, 2.0, 3.0, 4.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V124` | Vesta engineered | `float64` | 0.05% | 14 | 1.0, 4.0, 2.0, 3.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V125` | Vesta engineered | `float64` | 0.05% | 14 | 1.0, 3.0, 2.0, 4.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V126` | Vesta engineered | `float64` | 0.05% | 10,299 | 0.0, 50.0, 209.9499969482422, 29.0, 774.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V127` | Vesta engineered | `float64` | 0.05% | 24,414 | 117.0, 0.0, 1758.0, 60.0, 100.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V128` | Vesta engineered | `float64` | 0.05% | 14,507 | 0.0, 925.0, 102.5, 27.96999931335449, 417.8999938964844 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V129` | Vesta engineered | `float64` | 0.05% | 1,968 | 0.0, 209.9499969482422, 29.0, 58.95000076293945, 1054.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V130` | Vesta engineered | `float64` | 0.05% | 12,332 | 0.0, 354.0, 60.0, 100.0, 425.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V131` | Vesta engineered | `float64` | 0.05% | 4,444 | 0.0, 135.0, 34.0, 27.96999931335449, 209.9499969482422 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V132` | Vesta engineered | `float64` | 0.05% | 6,560 | 0.0, 50.0, 200.0, 530.0, 77.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V133` | Vesta engineered | `float64` | 0.05% | 9,949 | 117.0, 0.0, 1404.0, 68.5, 417.8999938964844 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V134` | Vesta engineered | `float64` | 0.05% | 8,178 | 0.0, 790.0, 68.5, 207.9499969482422, 1472.5 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V135` | Vesta engineered | `float64` | 0.05% | 3,724 | 0.0, 774.0, 50.0, 107.9499969482422, 200.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V136` | Vesta engineered | `float64` | 0.05% | 4,852 | 0.0, 24.0, 107.9499969482422, 774.0, 210.9499969482422 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V137` | Vesta engineered | `float64` | 0.05% | 4,252 | 0.0, 774.0, 50.0, 107.9499969482422, 200.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V138` | Vesta engineered | `float64` | 86.12% | 23 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V139` | Vesta engineered | `float64` | 86.12% | 34 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V140` | Vesta engineered | `float64` | 86.12% | 34 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V141` | Vesta engineered | `float64` | 86.12% | 6 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V142` | Vesta engineered | `float64` | 86.12% | 10 | 0.0, 1.0, 3.0, 4.0, 2.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V143` | Vesta engineered | `float64` | 86.12% | 870 | 6.0, 0.0, 5.0, 1.0, 7.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V144` | Vesta engineered | `float64` | 86.12% | 63 | 18.0, 0.0, 17.0, 1.0, 19.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V145` | Vesta engineered | `float64` | 86.12% | 260 | 140.0, 0.0, 141.0, 1.0, 142.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V146` | Vesta engineered | `float64` | 86.12% | 25 | 0.0, 1.0, 2.0, 3.0, 7.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V147` | Vesta engineered | `float64` | 86.12% | 27 | 0.0, 1.0, 2.0, 3.0, 7.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V148` | Vesta engineered | `float64` | 86.12% | 21 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V149` | Vesta engineered | `float64` | 86.12% | 21 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V150` | Vesta engineered | `float64` | 86.12% | 1,996 | 1803.0, 1804.0, 1805.0, 1806.0, 1.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V151` | Vesta engineered | `float64` | 86.12% | 56 | 49.0, 1.0, 4.0, 50.0, 51.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V152` | Vesta engineered | `float64` | 86.12% | 39 | 64.0, 1.0, 4.0, 2.0, 7.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V153` | Vesta engineered | `float64` | 86.12% | 19 | 0.0, 1.0, 6.0, 2.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V154` | Vesta engineered | `float64` | 86.12% | 19 | 0.0, 1.0, 7.0, 2.0, 8.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V155` | Vesta engineered | `float64` | 86.12% | 25 | 0.0, 1.0, 2.0, 7.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V156` | Vesta engineered | `float64` | 86.12% | 25 | 0.0, 1.0, 2.0, 8.0, 9.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V157` | Vesta engineered | `float64` | 86.12% | 25 | 0.0, 1.0, 2.0, 7.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V158` | Vesta engineered | `float64` | 86.12% | 25 | 0.0, 1.0, 2.0, 8.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V159` | Vesta engineered | `float64` | 86.12% | 6,663 | 15557.990234375, 15607.990234375, 15622.990234375, 15652.990234375, 15672.990234375 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V160` | Vesta engineered | `float64` | 86.12% | 9,621 | 169690.796875, 169740.796875, 169755.796875, 169785.796875, 169885.796875 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V161` | Vesta engineered | `float64` | 86.12% | 79 | 0.0, 500.0, 30.0, 50.0, 20.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V162` | Vesta engineered | `float64` | 86.12% | 185 | 0.0, 500.0, 70.0, 50.0, 130.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V163` | Vesta engineered | `float64` | 86.12% | 106 | 0.0, 500.0, 70.0, 50.0, 100.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V164` | Vesta engineered | `float64` | 86.12% | 1,978 | 515.0, 0.0, 475.0, 575.0, 50.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V165` | Vesta engineered | `float64` | 86.12% | 2,547 | 5155.0, 0.0, 5255.0, 50.0, 250.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V166` | Vesta engineered | `float64` | 86.12% | 987 | 2840.0, 0.0, 2740.0, 2790.0, 2490.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V167` | Vesta engineered | `float64` | 76.36% | 873 | 0.0, 3.0, 4.0, 1.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V168` | Vesta engineered | `float64` | 76.36% | 965 | 0.0, 3.0, 1.0, 4.0, 2.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V169` | Vesta engineered | `float64` | 76.32% | 20 | 0.0, 3.0, 4.0, 5.0, 1.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V170` | Vesta engineered | `float64` | 76.32% | 49 | 1.0, 4.0, 5.0, 2.0, 6.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V171` | Vesta engineered | `float64` | 76.32% | 62 | 1.0, 4.0, 5.0, 2.0, 6.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V172` | Vesta engineered | `float64` | 76.36% | 32 | 0.0, 2.0, 3.0, 1.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V173` | Vesta engineered | `float64` | 76.36% | 8 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V174` | Vesta engineered | `float64` | 76.32% | 9 | 0.0, 2.0, 1.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V175` | Vesta engineered | `float64` | 76.32% | 15 | 0.0, 2.0, 1.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V176` | Vesta engineered | `float64` | 76.36% | 49 | 1.0, 4.0, 5.0, 6.0, 2.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V177` | Vesta engineered | `float64` | 76.36% | 862 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V178` | Vesta engineered | `float64` | 76.36% | 1,236 | 0.0, 1.0, 2.0, 6.0, 7.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V179` | Vesta engineered | `float64` | 76.36% | 921 | 0.0, 1.0, 2.0, 7.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V180` | Vesta engineered | `float64` | 76.32% | 84 | 0.0, 1.0, 2.0, 8.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V181` | Vesta engineered | `float64` | 76.36% | 25 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V182` | Vesta engineered | `float64` | 76.36% | 84 | 0.0, 1.0, 2.0, 4.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V183` | Vesta engineered | `float64` | 76.36% | 42 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V184` | Vesta engineered | `float64` | 76.32% | 17 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V185` | Vesta engineered | `float64` | 76.32% | 32 | 0.0, 1.0, 2.0, 3.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V186` | Vesta engineered | `float64` | 76.36% | 39 | 1.0, 2.0, 4.0, 5.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V187` | Vesta engineered | `float64` | 76.36% | 215 | 1.0, 2.0, 4.0, 3.0, 85.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V188` | Vesta engineered | `float64` | 76.32% | 31 | 1.0, 2.0, 0.0, 4.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V189` | Vesta engineered | `float64` | 76.32% | 31 | 1.0, 2.0, 0.0, 4.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V190` | Vesta engineered | `float64` | 76.36% | 43 | 1.0, 2.0, 4.0, 3.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V191` | Vesta engineered | `float64` | 76.36% | 22 | 1.0, 4.0, 2.0, 5.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V192` | Vesta engineered | `float64` | 76.36% | 45 | 1.0, 4.0, 2.0, 30.0, 16.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V193` | Vesta engineered | `float64` | 76.36% | 38 | 1.0, 4.0, 2.0, 18.0, 14.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V194` | Vesta engineered | `float64` | 76.32% | 8 | 1.0, 0.0, 4.0, 2.0, 6.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V195` | Vesta engineered | `float64` | 76.32% | 17 | 1.0, 0.0, 4.0, 2.0, 7.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V196` | Vesta engineered | `float64` | 76.36% | 39 | 1.0, 4.0, 2.0, 5.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V197` | Vesta engineered | `float64` | 76.32% | 15 | 1.0, 0.0, 4.0, 2.0, 7.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V198` | Vesta engineered | `float64` | 76.32% | 22 | 1.0, 0.0, 4.0, 2.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V199` | Vesta engineered | `float64` | 76.36% | 46 | 1.0, 2.0, 3.0, 4.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V200` | Vesta engineered | `float64` | 76.32% | 46 | 1.0, 2.0, 0.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V201` | Vesta engineered | `float64` | 76.32% | 56 | 1.0, 2.0, 0.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V202` | Vesta engineered | `float64` | 76.36% | 10,970 | 0.0, 166.21539306640625, 242.1029052734375, 100.0, 50.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V203` | Vesta engineered | `float64` | 76.36% | 14,951 | 0.0, 166.21539306640625, 125.0, 242.1029052734375, 140.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V204` | Vesta engineered | `float64` | 76.36% | 12,858 | 0.0, 166.21539306640625, 25.0, 242.1029052734375, 40.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V205` | Vesta engineered | `float64` | 76.36% | 2,240 | 0.0, 90.3279037475586, 166.21539306640625, 30.0, 8.640600204467772 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V206` | Vesta engineered | `float64` | 76.36% | 1,780 | 0.0, 31.84129905700684, 107.72879791259766, 8.640600204467772, 500.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V207` | Vesta engineered | `float64` | 76.36% | 3,246 | 0.0, 90.3279037475586, 25.0, 40.0, 166.21539306640625 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V208` | Vesta engineered | `float64` | 76.32% | 2,552 | 0.0, 90.3279037475586, 30.0, 50.0, 125.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V209` | Vesta engineered | `float64` | 76.32% | 3,451 | 0.0, 90.3279037475586, 125.0, 140.0, 166.21539306640625 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V210` | Vesta engineered | `float64` | 76.32% | 2,836 | 0.0, 90.3279037475586, 30.0, 50.0, 125.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V211` | Vesta engineered | `float64` | 76.36% | 7,624 | 0.0, 100.0, 37.097900390625, 74.19580078125, 48.63809967041016 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V212` | Vesta engineered | `float64` | 76.36% | 8,868 | 0.0, 100.0, 37.097900390625, 74.19580078125, 48.63809967041016 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V213` | Vesta engineered | `float64` | 76.36% | 8,317 | 0.0, 100.0, 37.097900390625, 74.19580078125, 48.63809967041016 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V214` | Vesta engineered | `float64` | 76.36% | 2,282 | 0.0, 75.88749694824219, 151.77499389648438, 50.0, 200.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V215` | Vesta engineered | `float64` | 76.36% | 2,747 | 0.0, 75.88749694824219, 151.77499389648438, 50.0, 200.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V216` | Vesta engineered | `float64` | 76.36% | 2,532 | 0.0, 75.88749694824219, 151.77499389648438, 50.0, 200.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V217` | Vesta engineered | `float64` | 77.91% | 304 | 0.0, 3.0, 4.0, 1.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V218` | Vesta engineered | `float64` | 77.91% | 401 | 0.0, 3.0, 4.0, 2.0, 1.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V219` | Vesta engineered | `float64` | 77.91% | 379 | 0.0, 3.0, 4.0, 1.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V220` | Vesta engineered | `float64` | 76.05% | 26 | 0.0, 3.0, 4.0, 5.0, 1.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V221` | Vesta engineered | `float64` | 76.05% | 77 | 1.0, 4.0, 5.0, 0.0, 2.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V222` | Vesta engineered | `float64` | 76.05% | 76 | 1.0, 4.0, 5.0, 0.0, 2.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V223` | Vesta engineered | `float64` | 77.91% | 17 | 0.0, 2.0, 3.0, 1.0, 6.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V224` | Vesta engineered | `float64` | 77.91% | 79 | 0.0, 2.0, 3.0, 1.0, 107.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V225` | Vesta engineered | `float64` | 77.91% | 35 | 0.0, 2.0, 3.0, 1.0, 42.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V226` | Vesta engineered | `float64` | 77.91% | 81 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V227` | Vesta engineered | `float64` | 76.05% | 50 | 0.0, 2.0, 3.0, 1.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V228` | Vesta engineered | `float64` | 77.91% | 55 | 1.0, 4.0, 5.0, 6.0, 2.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V229` | Vesta engineered | `float64` | 77.91% | 91 | 1.0, 4.0, 5.0, 2.0, 6.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V230` | Vesta engineered | `float64` | 77.91% | 66 | 1.0, 4.0, 5.0, 6.0, 2.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V231` | Vesta engineered | `float64` | 77.91% | 294 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V232` | Vesta engineered | `float64` | 77.91% | 338 | 0.0, 2.0, 1.0, 3.0, 33.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V233` | Vesta engineered | `float64` | 77.91% | 333 | 0.0, 1.0, 2.0, 3.0, 18.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V234` | Vesta engineered | `float64` | 76.05% | 122 | 0.0, 1.0, 2.0, 35.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V235` | Vesta engineered | `float64` | 77.91% | 24 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V236` | Vesta engineered | `float64` | 77.91% | 46 | 0.0, 1.0, 2.0, 29.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V237` | Vesta engineered | `float64` | 77.91% | 40 | 0.0, 1.0, 2.0, 13.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V238` | Vesta engineered | `float64` | 76.05% | 24 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V239` | Vesta engineered | `float64` | 76.05% | 24 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V240` | Vesta engineered | `float64` | 77.91% | 6 | 1.0, 2.0, 5.0, 6.0, 7.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V241` | Vesta engineered | `float64` | 77.91% | 5 | 1.0, 2.0, 4.0, 5.0, 0.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V242` | Vesta engineered | `float64` | 77.91% | 21 | 1.0, 2.0, 7.0, 4.0, 8.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V243` | Vesta engineered | `float64` | 77.91% | 43 | 1.0, 2.0, 49.0, 4.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V244` | Vesta engineered | `float64` | 77.91% | 23 | 1.0, 2.0, 7.0, 4.0, 8.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V245` | Vesta engineered | `float64` | 76.05% | 58 | 1.0, 2.0, 0.0, 3.0, 7.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V246` | Vesta engineered | `float64` | 77.91% | 46 | 1.0, 2.0, 7.0, 4.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V247` | Vesta engineered | `float64` | 77.91% | 19 | 1.0, 6.0, 4.0, 2.0, 7.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V248` | Vesta engineered | `float64` | 77.91% | 23 | 1.0, 2.0, 35.0, 4.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V249` | Vesta engineered | `float64` | 77.91% | 23 | 1.0, 21.0, 4.0, 3.0, 2.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V250` | Vesta engineered | `float64` | 76.05% | 19 | 1.0, 0.0, 2.0, 6.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V251` | Vesta engineered | `float64` | 76.05% | 19 | 1.0, 0.0, 2.0, 7.0, 8.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V252` | Vesta engineered | `float64` | 77.91% | 25 | 1.0, 7.0, 4.0, 2.0, 8.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V253` | Vesta engineered | `float64` | 77.91% | 66 | 1.0, 2.0, 131.0, 4.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V254` | Vesta engineered | `float64` | 77.91% | 45 | 1.0, 2.0, 54.0, 4.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V255` | Vesta engineered | `float64` | 76.05% | 46 | 1.0, 0.0, 2.0, 7.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V256` | Vesta engineered | `float64` | 76.05% | 48 | 1.0, 0.0, 2.0, 8.0, 9.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V257` | Vesta engineered | `float64` | 77.91% | 49 | 1.0, 2.0, 3.0, 7.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V258` | Vesta engineered | `float64` | 77.91% | 67 | 1.0, 2.0, 3.0, 60.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V259` | Vesta engineered | `float64` | 76.05% | 68 | 1.0, 2.0, 0.0, 3.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V260` | Vesta engineered | `float64` | 77.91% | 9 | 1.0, 0.0, 2.0, 4.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V261` | Vesta engineered | `float64` | 77.91% | 41 | 1.0, 0.0, 2.0, 3.0, 37.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V262` | Vesta engineered | `float64` | 77.91% | 21 | 1.0, 0.0, 17.0, 4.0, 2.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V263` | Vesta engineered | `float64` | 77.91% | 10,422 | 0.0, 166.21539306640625, 242.1029052734375, 100.0, 50.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V264` | Vesta engineered | `float64` | 77.91% | 13,358 | 0.0, 166.21539306640625, 242.1029052734375, 50.0, 100.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V265` | Vesta engineered | `float64` | 77.91% | 11,757 | 0.0, 166.21539306640625, 242.1029052734375, 100.0, 50.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V266` | Vesta engineered | `float64` | 77.91% | 2,178 | 0.0, 90.3279037475586, 166.21539306640625, 8.640600204467772, 750.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V267` | Vesta engineered | `float64` | 77.91% | 3,616 | 0.0, 90.3279037475586, 166.21539306640625, 8.640600204467772, 17.703100204467773 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V268` | Vesta engineered | `float64` | 77.91% | 2,756 | 0.0, 90.3279037475586, 166.21539306640625, 8.640600204467772, 10875.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V269` | Vesta engineered | `float64` | 77.91% | 151 | 0.0, 750.0, 500.0, 6.0, 950.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V270` | Vesta engineered | `float64` | 76.05% | 2,340 | 0.0, 90.3279037475586, 166.21539306640625, 16.857200622558597, 500.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V271` | Vesta engineered | `float64` | 76.05% | 2,787 | 0.0, 90.3279037475586, 166.21539306640625, 8.640600204467772, 16.857200622558597 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V272` | Vesta engineered | `float64` | 76.05% | 2,507 | 0.0, 90.3279037475586, 166.21539306640625, 8.640600204467772, 16.857200622558597 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V273` | Vesta engineered | `float64` | 77.91% | 7,177 | 0.0, 100.0, 37.097900390625, 74.19580078125, 48.63809967041016 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V274` | Vesta engineered | `float64` | 77.91% | 8,315 | 0.0, 50.0, 100.0, 70.08719635009766, 37.097900390625 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V275` | Vesta engineered | `float64` | 77.91% | 7,776 | 0.0, 100.0, 70.08719635009766, 37.097900390625, 74.19580078125 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V276` | Vesta engineered | `float64` | 77.91% | 2,263 | 0.0, 75.88749694824219, 151.77499389648438, 50.0, 200.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V277` | Vesta engineered | `float64` | 77.91% | 2,540 | 0.0, 75.88749694824219, 151.77499389648438, 50.0, 200.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V278` | Vesta engineered | `float64` | 77.91% | 2,398 | 0.0, 75.88749694824219, 151.77499389648438, 50.0, 200.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V279` | Vesta engineered | `float64` | 0.00% | 881 | 0.0, 1.0, 3.0, 2.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V280` | Vesta engineered | `float64` | 0.00% | 975 | 0.0, 28.0, 3.0, 2.0, 1.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V281` | Vesta engineered | `float64` | 0.21% | 23 | 0.0, 3.0, 1.0, 2.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V282` | Vesta engineered | `float64` | 0.21% | 33 | 1.0, 0.0, 4.0, 2.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V283` | Vesta engineered | `float64` | 0.21% | 62 | 1.0, 0.0, 4.0, 2.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V284` | Vesta engineered | `float64` | 0.00% | 13 | 0.0, 2.0, 1.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V285` | Vesta engineered | `float64` | 0.00% | 96 | 0.0, 10.0, 2.0, 1.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V286` | Vesta engineered | `float64` | 0.00% | 9 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V287` | Vesta engineered | `float64` | 0.00% | 32 | 0.0, 4.0, 2.0, 1.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V288` | Vesta engineered | `float64` | 0.21% | 11 | 0.0, 2.0, 1.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V289` | Vesta engineered | `float64` | 0.21% | 13 | 0.0, 2.0, 1.0, 4.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V290` | Vesta engineered | `float64` | 0.00% | 58 | 1.0, 4.0, 2.0, 3.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V291` | Vesta engineered | `float64` | 0.00% | 219 | 1.0, 4.0, 2.0, 3.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V292` | Vesta engineered | `float64` | 0.00% | 173 | 1.0, 4.0, 2.0, 3.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V293` | Vesta engineered | `float64` | 0.00% | 870 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V294` | Vesta engineered | `float64` | 0.00% | 1,286 | 1.0, 0.0, 38.0, 17.0, 18.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V295` | Vesta engineered | `float64` | 0.00% | 928 | 0.0, 24.0, 1.0, 4.0, 5.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V296` | Vesta engineered | `float64` | 0.21% | 94 | 0.0, 1.0, 3.0, 2.0, 6.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V297` | Vesta engineered | `float64` | 0.00% | 13 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V298` | Vesta engineered | `float64` | 0.00% | 94 | 0.0, 1.0, 2.0, 6.0, 3.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V299` | Vesta engineered | `float64` | 0.00% | 50 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V300` | Vesta engineered | `float64` | 0.21% | 12 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V301` | Vesta engineered | `float64` | 0.21% | 14 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V302` | Vesta engineered | `float64` | 0.00% | 17 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V303` | Vesta engineered | `float64` | 0.00% | 21 | 0.0, 1.0, 2.0, 7.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V304` | Vesta engineered | `float64` | 0.00% | 17 | 0.0, 1.0, 2.0, 3.0, 7.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V305` | Vesta engineered | `float64` | 0.00% | 2 | 1.0, 2.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V306` | Vesta engineered | `float64` | 0.00% | 16,210 | 0.0, 50.0, 166.21539306640625, 29.0, 774.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V307` | Vesta engineered | `float64` | 0.00% | 37,367 | 117.0, 0.0, 1758.0, 166.21539306640625, 60.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V308` | Vesta engineered | `float64` | 0.00% | 23,064 | 0.0, 925.0, 166.21539306640625, 102.5, 27.96999931335449 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V309` | Vesta engineered | `float64` | 0.00% | 4,236 | 0.0, 90.3279037475586, 29.0, 58.95000076293945, 1054.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V310` | Vesta engineered | `float64` | 0.00% | 19,136 | 0.0, 354.0, 90.3279037475586, 60.0, 100.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V311` | Vesta engineered | `float64` | 0.00% | 3,098 | 0.0, 31.84129905700684, 29.0, 42.596099853515625, 75.88749694824219 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V312` | Vesta engineered | `float64` | 0.00% | 8,068 | 0.0, 135.0, 90.3279037475586, 34.0, 27.96999931335449 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V313` | Vesta engineered | `float64` | 0.21% | 5,529 | 0.0, 90.3279037475586, 29.0, 226.0, 49.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V314` | Vesta engineered | `float64` | 0.21% | 11,377 | 0.0, 495.0, 90.3279037475586, 50.0, 93.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V315` | Vesta engineered | `float64` | 0.21% | 6,973 | 0.0, 90.3279037475586, 29.0, 926.0, 49.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V316` | Vesta engineered | `float64` | 0.00% | 9,814 | 0.0, 50.0, 200.0, 530.0, 500.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V317` | Vesta engineered | `float64` | 0.00% | 15,184 | 117.0, 0.0, 1404.0, 68.5, 7013.5 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V318` | Vesta engineered | `float64` | 0.00% | 12,309 | 0.0, 790.0, 68.5, 1472.5, 1672.5 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V319` | Vesta engineered | `float64` | 0.00% | 4,799 | 0.0, 75.88749694824219, 774.0, 50.0, 107.9499969482422 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V320` | Vesta engineered | `float64` | 0.00% | 6,439 | 0.0, 75.88749694824219, 170.0, 774.0, 210.9499969482422 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V321` | Vesta engineered | `float64` | 0.00% | 5,560 | 0.0, 75.88749694824219, 774.0, 50.0, 107.9499969482422 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V322` | Vesta engineered | `float64` | 86.05% | 881 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V323` | Vesta engineered | `float64` | 86.05% | 1,411 | 0.0, 6.0, 4.0, 1.0, 2.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V324` | Vesta engineered | `float64` | 86.05% | 976 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V325` | Vesta engineered | `float64` | 86.05% | 13 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V326` | Vesta engineered | `float64` | 86.05% | 45 | 0.0, 6.0, 4.0, 1.0, 26.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V327` | Vesta engineered | `float64` | 86.05% | 19 | 0.0, 1.0, 2.0, 10.0, 6.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V328` | Vesta engineered | `float64` | 86.05% | 16 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V329` | Vesta engineered | `float64` | 86.05% | 100 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V330` | Vesta engineered | `float64` | 86.05% | 56 | 0.0, 1.0, 2.0, 3.0, 4.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V331` | Vesta engineered | `float64` | 86.05% | 1,758 | 0.0, 100.0, 50.0, 200.0, 300.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V332` | Vesta engineered | `float64` | 86.05% | 2,453 | 0.0, 145.0, 140.0, 125.0, 100.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V333` | Vesta engineered | `float64` | 86.05% | 1,971 | 0.0, 25.0, 40.0, 100.0, 50.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V334` | Vesta engineered | `float64` | 86.05% | 143 | 0.0, 35.0, 6.0, 50.0, 30.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V335` | Vesta engineered | `float64` | 86.05% | 672 | 0.0, 145.0, 140.0, 125.0, 30.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V336` | Vesta engineered | `float64` | 86.05% | 356 | 0.0, 25.0, 40.0, 35.0, 22.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V337` | Vesta engineered | `float64` | 86.05% | 254 | 0.0, 50.0, 200.0, 100.0, 300.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V338` | Vesta engineered | `float64` | 86.05% | 380 | 0.0, 50.0, 200.0, 100.0, 300.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `V339` | Vesta engineered | `float64` | 86.05% | 334 | 0.0, 50.0, 200.0, 100.0, 300.0 | Anonymized Vesta engineered numerical feature; exact business meaning is not disclosed. |
| `id_01` | Device identity | `float64` | 75.58% | 77 | 0.0, -5.0, -15.0, -10.0, -20.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_02` | Device identity | `float64` | 76.15% | 115,655 | 70787.0, 98945.0, 191631.0, 221832.0, 7460.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_03` | Device identity | `float64` | 88.77% | 24 | 0.0, 3.0, 2.0, 5.0, 1.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_04` | Device identity | `float64` | 88.77% | 15 | 0.0, -11.0, -5.0, -8.0, -1.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_05` | Device identity | `float64` | 76.82% | 93 | 0.0, 1.0, 3.0, 2.0, 9.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_06` | Device identity | `float64` | 76.82% | 101 | -5.0, 0.0, -6.0, -10.0, -11.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_07` | Device identity | `float64` | 99.13% | 84 | 22.0, 6.0, -1.0, 4.0, 2.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_08` | Device identity | `float64` | 99.13% | 94 | -34.0, -55.0, -100.0, -15.0, -33.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_09` | Device identity | `float64` | 87.31% | 46 | 0.0, 3.0, 2.0, 1.0, 5.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_10` | Device identity | `float64` | 87.31% | 62 | 0.0, -9.0, -42.0, -6.0, -29.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_11` | Device identity | `float64` | 76.13% | 365 | 100.0, 93.75, 95.08000183105467, 95.6500015258789, 94.29000091552734 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_12` | Device identity | `object` | 75.58% | 2 | NotFound, Found | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_13` | Device identity | `float64` | 78.44% | 54 | 49.0, 52.0, 14.0, 20.0, 55.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_14` | Device identity | `float64` | 86.45% | 25 | -480.0, -300.0, -360.0, -420.0, -540.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_15` | Device identity | `object` | 76.13% | 3 | New, Found, Unknown | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_16` | Device identity | `object` | 78.10% | 2 | NotFound, Found | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_17` | Device identity | `float64` | 76.40% | 104 | 166.0, 121.0, 225.0, 102.0, 148.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_18` | Device identity | `float64` | 92.36% | 18 | 15.0, 18.0, 13.0, 12.0, 20.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_19` | Device identity | `float64` | 76.41% | 522 | 542.0, 621.0, 410.0, 176.0, 529.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_20` | Device identity | `float64` | 76.42% | 394 | 144.0, 500.0, 142.0, 507.0, 575.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_21` | Device identity | `float64` | 99.13% | 490 | 252.0, 657.0, 724.0, 228.0, 369.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_22` | Device identity | `float64` | 99.12% | 25 | 14.0, 41.0, 21.0, 33.0, 35.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_23` | Device identity | `object` | 99.12% | 3 | IP_PROXY:TRANSPARENT, IP_PROXY:ANONYMOUS, IP_PROXY:HIDDEN | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_24` | Device identity | `float64` | 99.20% | 12 | 11.0, 15.0, 16.0, 12.0, 21.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_25` | Device identity | `float64` | 99.13% | 341 | 321.0, 161.0, 460.0, 426.0, 205.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_26` | Device identity | `float64` | 99.13% | 95 | 184.0, 102.0, 159.0, 142.0, 117.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_27` | Device identity | `object` | 99.12% | 2 | Found, NotFound | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_28` | Device identity | `object` | 76.13% | 2 | New, Found | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_29` | Device identity | `object` | 76.13% | 2 | NotFound, Found | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_30` | Device identity | `object` | 86.87% | 75 | Android 7.0, iOS 11.1.2, Mac OS X 10_11_6, Windows 10, Android | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_31` | Device identity | `object` | 76.25% | 130 | samsung browser 6.2, mobile safari 11.0, chrome 62.0, chrome 62.0 for android, edge 15.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_32` | Device identity | `float64` | 86.86% | 4 | 32.0, 24.0, 16.0, 0.0 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_33` | Device identity | `object` | 87.59% | 260 | 2220x1080, 1334x750, 1280x800, 1366x768, 1920x1080 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_34` | Device identity | `object` | 86.82% | 4 | match_status:2, match_status:1, match_status:0, match_status:-1 | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_35` | Device identity | `object` | 76.13% | 2 | T, F | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_36` | Device identity | `object` | 76.13% | 2 | F, T | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_37` | Device identity | `object` | 76.13% | 2 | T, F | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `id_38` | Device identity | `object` | 76.13% | 2 | T, F | Anonymized device/identity feature; exact business meaning is not disclosed except for documented string examples. |
| `DeviceType` | Device identity | `object` | 76.16% | 2 | mobile, desktop | Device class, commonly desktop or mobile. |
| `DeviceInfo` | Device identity | `object` | 79.91% | 1,786 | SAMSUNG SM-G892A Build/NRD90M, iOS Device, Windows, MacOS, SM-G930V Build/NRD90M | Anonymized/raw device-information string, often device family or model. |

## Features added later by our pipeline

Notebook 01 adds the following derived features after this source-data dictionary: `has_identity`, `log_TransactionAmt`, `transaction_day`, `transaction_week`, `transaction_hour`, `is_weekend`, selected `<column>_missing` flags, `card1_card2`, `addr1_addr2`, and `email_pair`. Their detailed explanation is in [FEATURE_ENGINEERING_GUIDE.md](FEATURE_ENGINEERING_GUIDE.md).
