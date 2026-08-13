# Model artifact and four-model inference contract

The final application accepts one common raw transaction and sends it through
four independently trained pipelines. The raw input is common; internal
representations are model-specific.

```text
Common transaction
        ↓
Schema normalization + shared row features
        ├── Logistic pipeline → probability
        ├── LightGBM preprocessor + model → probability
        ├── CatBoost preprocessor + model → probability
        └── Neural preprocessor + network → probability
```

## Native formats

| Model | Model file | Preprocessing file |
| --- | --- | --- |
| Logistic Regression | `model.joblib` containing the full sklearn pipeline | Included in `model.joblib` |
| LightGBM | `model.txt` | `preprocessor.joblib` |
| CatBoost | `model.cbm` | `preprocessor.joblib` |
| Neural network | `model.pt` state dictionary | `numeric_and_categorical_preprocessor.joblib` plus `model_config.json` |

`preprocessor.joblib` contains transformations learned from training data: for
example medians, scales, frequency maps, category levels, feature order, and
reserved unknown-value behavior. It is not interchangeable across models.

Joblib uses pickle-based serialization. Load only project-generated artifacts
from the private R2 bucket and verify their manifest checksums.

## Shared files in every bundle

- `feature_schema.json`: exact input feature groups and order.
- `threshold.json`: validation-selected decision threshold and selection method.
- `metrics.json`: validation and chronological holdout results.
- `training_config.json`: parameters, random seed, timing, and library versions.
- `manifest.json`: file sizes and SHA-256 checksums.
- validation/test predictions: enables fair comparison and a later validated ensemble.

## Versioned storage

Training runs are immutable:

```text
<model>/<UTC-run-id>/...
```

After comparison, a registry points to one approved run per model:

```json
{
  "schema_version": "1.0",
  "models": {
    "logistic_regression": {"run_id": "...", "enabled": true},
    "lightgbm": {"run_id": "...", "enabled": true},
    "catboost": {"run_id": "...", "enabled": true},
    "neural_network": {"run_id": "...", "enabled": true}
  }
}
```

The backend loads all four at startup. It never downloads or deserializes an
artifact supplied by an application user.

## Common API output

Each wrapper returns:

```json
{
  "model": "catboost",
  "fraud_probability": 0.91,
  "prediction": 1,
  "threshold": 0.75,
  "risk_level": "HIGH",
  "latency_ms": 14.2,
  "model_version": "20260813T120000Z"
}
```

The API combines all four results but does not claim that their unvalidated
average is a superior ensemble. A future ensemble must be fitted using
validation predictions only.
