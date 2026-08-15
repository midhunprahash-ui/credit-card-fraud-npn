# Model artifact and eight-pipeline inference contract

The final application accepts one common raw transaction and sends it through
any selection of eight independently trained pipelines. The raw input is
common; V1/V2 feature engineering and model preprocessing are versioned.

```text
Common transaction
        ↓
Schema normalization; remove isFraud
        ├── V1 feature engineering
        │     └── each V1 model's saved preprocessor + model + threshold
        └── V2 chronological feature engineering
              └── each V2 model's saved preprocessor + model + threshold
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

`manifest.json` deliberately does not checksum itself. A file cannot contain a
stable checksum of its own final contents. Every other file in the run bundle is
covered by the manifest.

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

Deployment objects use immutable version/model/run keys:

```text
models/v1/<model-key>/<run-id>/...
models/v2/<model-key>/<run-id>/...
models/runtime/v2/behavioral_reference.joblib
```

`config/deployment_artifacts.json` pins every remote manifest SHA-256 and the
target-free V2 reference SHA-256. A private bucket alone is not treated as a
trust boundary: downloaded bytes must match this Git-reviewed contract.

The backend loads only requested approved models and will later keep them in a
bounded least-recently-used cache. It never downloads or deserializes an
artifact supplied by an application user. The manifest and registry threshold
are checked before a bundle is used.

The approved run IDs and measured results are frozen in
[`../config/model_registry.json`](../config/model_registry.json). The human-readable
selection rationale is in
[`FINAL_MODEL_SELECTION.md`](FINAL_MODEL_SELECTION.md).

## Common adapter output

Each wrapper returns:

```json
{
  "model_identifier": "catboost.v2",
  "model_name": "CatBoost.V2",
  "model_version": "V2",
  "run_id": "20260815T121042Z",
  "risk_score": 0.91,
  "decision": true,
  "threshold": 0.019238112237044917,
  "latency_ms": 14.2,
  "champion": true,
  "processing_status": "completed"
}
```

Scores are fraud-risk scores, not guaranteed calibrated probabilities. The API
may summarize agreement across selected models, but does not call that summary
an ensemble. A future ensemble must be fitted using validation predictions only.

The raw boundary null-fills absent optional fields and rejects invalid IDs,
negative amounts, duplicate identifiers, and unknown fields. It always drops
`isFraud`. V2 additionally requires a target-free reference whose recorded
history cutoff is strictly earlier than the transaction being scored.
