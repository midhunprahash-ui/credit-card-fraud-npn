# Eight-model verification gate

The analyst UI must not consume real predictions until all eight selected V1/V2
pipelines pass this gate.

## What the command checks

For every approved model, the verifier:

1. resolves the selected run from the V1 or V2 registry;
2. verifies every artifact size and SHA-256 checksum before loading it;
3. reads a chronological sample from the labelled held-out test partition;
4. creates the V1 `has_identity` flag from membership in `train_identity.csv`;
5. removes `isFraud` and `TransactionID` before calling the model;
6. loads the saved model and its saved training-only preprocessor;
7. compares new scores with that run's stored held-out predictions; and
8. fails if any score is outside the numerical tolerance.

Each model runs in a separate subprocess. This avoids accumulating all eight
large native runtimes in one process and gives each pipeline an independent
pass/fail result.

## Run it

The datasets and artifacts are local, Git-ignored prerequisites:

```bash
.venv/bin/python scripts/verify_selected_models.py
```

Use JSON for CI logs or a deployment report:

```bash
.venv/bin/python scripts/verify_selected_models.py --json
```

The default sample contains the earliest 32 held-out rows in chronological
order. Increase it when measuring inference performance, but do not use the
holdout result to tune a model or threshold.

## Passing condition

The final line must say:

```text
Verification gate: PASS (8/8 models)
```

Only after that result is recorded may the frontend add Single Transaction, CSV
Upload or Real-time prediction workflows.

## Recorded result

On 15 August 2026, all eight selected runs passed on the earliest 32 held-out
transactions. All artifact manifests matched, `isFraud` was absent from every
model input, and the largest score difference was `6.71e-08` (Neural
Network.V1), within the defined numerical tolerance.
