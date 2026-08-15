# Eight-model verification gate

The analyst UI must not consume real predictions until all eight selected V1/V2
pipelines pass this gate.

## What the command checks

For every approved model, the verifier:

1. resolves the selected run from the V1 or V2 registry;
2. verifies every artifact size and SHA-256 checksum before loading it;
3. reads a chronological sample from the labelled held-out test partition;
4. reconstructs one common raw transaction using the saved raw-input schema;
5. builds V2 history from train and validation rows only;
6. proves the raw V1 and V2 feature frames match their saved held-out features;
7. removes `isFraud` and `TransactionID` before calling every model;
8. loads the saved model and its own saved training-only preprocessor;
9. reproduces the first saved score from the common raw transaction;
10. compares the default 32 scores with stored held-out predictions; and
11. fails if either comparison is outside numerical tolerance.

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
transactions. The same real raw `TransactionID` entered both version paths,
all artifact manifests matched, and `isFraud` was absent from every model
input. Small neural-network differences are accepted only within the defined
floating-point tolerance.

The command intentionally rebuilds a safe V2 reference from pre-test history.
Do not use an old reference that has no chronological cutoff metadata.
