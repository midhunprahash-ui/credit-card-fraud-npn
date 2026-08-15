# Milestone 1: trusted local inference foundation

## Outcome

Milestone 1 establishes one safe input boundary and eight independently loaded
model pipelines. It does not add cloud deployment or application screens.

The public model contract is fixed:

| Stable identifier | Display name |
| --- | --- |
| `logistic_regression.v1` | `LogisticRegression.V1` |
| `lightgbm.v1` | `LightGBM.V1` |
| `catboost.v1` | `CatBoost.V1` |
| `neural_network.v1` | `NeuralNetwork.V1` |
| `logistic_regression.v2` | `LogisticRegression.V2` |
| `lightgbm.v2` | `LightGBM.V2` |
| `catboost.v2` | `CatBoost.V2` |
| `neural_network.v2` | `NeuralNetwork.V2` |

## What was already ready

- The V1 and V2 registries each selected four enabled model runs.
- Every selected run had a model, feature schema, saved threshold, stored
  held-out predictions, and a SHA-256 manifest.
- All prediction files contained 88,581 unique chronological held-out
  TransactionIDs and valid scores.
- The existing verifier could reproduce saved scores from already engineered
  held-out rows.

## What Milestone 1 added

- A strict registry loader that requires exactly eight canonical pipelines.
- A raw joined-transaction contract that removes `isFraud`, validates identifiers
  and amounts, rejects unknown fields, and null-fills optional fields.
- Separate V1 and V2 feature preparation.
- Four loaded-model adapters. Every adapter aligns to its own saved feature
  schema and uses its own saved preprocessor and threshold.
- A common single-transaction inference engine and a visual-agreement data
  contract. Agreement is not an ensemble.
- Manifest, threshold, score-range, label-exclusion, and schema checks.
- Golden verification beginning with one real raw held-out transaction, plus
  the existing chronological stored-prediction comparison.

## V2 issue found and corrected

The original saved deployment reference was built from the entire joined
dataset. It therefore included the held-out period that the replay is meant to
simulate. Its standard-deviation calculation also differed from the causal
training calculation.

The model training and stored held-out scores remain valid: those features were
created row by row using strictly earlier transactions. The unsafe reference was
not used to calculate the reported model metrics.

The repaired reference builder now:

1. uses population standard deviation, matching training;
2. records its final `TransactionDT` and `TransactionID`;
3. is generated from train and validation history only for held-out replay; and
4. is rejected when its cutoff is absent or overlaps the transaction being
   scored.

The local ignored `data/processed/v2/behavioral_reference.joblib` predates this
fix and must be regenerated with the corrected V2 preparation notebook before
it is used by the application. The golden verifier builds a safe reference in
memory from the local train and validation partitions.

## Verification result

Run:

```bash
PYTHONPATH=. .venv/bin/pytest -q
PYTHONPATH=. .venv/bin/python scripts/verify_selected_models.py
```

Passing means:

- all eight manifests and thresholds match;
- all eight artifacts load independently;
- V1 and V2 engineered inputs reproduce the saved schemas;
- the same real raw held-out transaction reproduces every model's saved score;
- the default 32 chronological scores match within numerical tolerance; and
- `isFraud` and `TransactionID` never reach an adapter.

## Boundaries for later milestones

- Adapters load one requested model. A bounded LRU model manager belongs to the
  backend milestone and must not preload the roughly 494 MB CatBoost.V2 model
  together with every other pipeline.
- Multi-row V2 processing must update behavioral state in strict chronological
  order. A frozen reference alone is valid only as the starting state; FIFO state
  updates will be implemented with streaming.
- Model outputs are labelled fraud-risk scores. Calibration has not been proven.
- The frontend, FastAPI prediction endpoints, Supabase repository, SSE stream,
  R2 transfer tools, and deployment work are deliberately outside Milestone 1.
