"""Build the committed Lightning AI notebooks from reviewable Python strings.

Run this script after editing notebook content here. It uses only the Python
standard library so notebook generation does not depend on Jupyter locally.
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "lightning_ai"


def md(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": dedent(source).strip() + "\n",
    }


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": dedent(source).strip() + "\n",
    }


def write_notebook(filename: str, cells: list[dict]) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    (OUTPUT / filename).write_text(json.dumps(notebook, indent=1) + "\n")


COMMON_SETUP = r'''
from pathlib import Path
import gc, json, os, sys, time
import numpy as np
import pandas as pd

def locate_project_root(start=None):
    candidate = Path(start or Path.cwd()).resolve()
    for path in [candidate, *candidate.parents]:
        if (path / ".git").exists() and (path / "src").exists():
            return path
    raise FileNotFoundError("Run this notebook from inside the cloned repository")

PROJECT_ROOT = locate_project_root()
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
ARTIFACT_ROOT = PROJECT_ROOT / "artifacts"
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

print("Project root:", PROJECT_ROOT)
print("Processed data:", PROCESSED_DIR)
'''


INSTALL_CELL = r'''
from pathlib import Path
_install_root = Path.cwd().resolve()
for _candidate in [_install_root, *_install_root.parents]:
    if (_candidate / "requirements-training.txt").exists():
        _requirements = _candidate / "requirements-training.txt"
        break
else:
    raise FileNotFoundError("Open this notebook from inside the cloned repository")
%pip install -q -r {_requirements}
'''


LOAD_SPLITS = r'''
required = [
    PROCESSED_DIR / "train.parquet",
    PROCESSED_DIR / "validation.parquet",
    PROCESSED_DIR / "test.parquet",
]
missing = [str(path) for path in required if not path.exists()]
if missing:
    raise FileNotFoundError(
        "Run 00_shared_data_preparation.ipynb first. Missing: " + ", ".join(missing)
    )

train = pd.read_parquet(required[0])
validation = pd.read_parquet(required[1])
test = pd.read_parquet(required[2])

def stratified_debug_sample(frame, rows):
    if rows is None or rows >= len(frame):
        return frame
    return (
        frame.groupby("isFraud", group_keys=False)
        .apply(lambda group: group.sample(
            n=max(1, round(rows * len(group) / len(frame))),
            random_state=RANDOM_SEED,
        ), include_groups=True)
        .sort_values(["TransactionDT", "TransactionID"])
        .reset_index(drop=True)
    )

FAST_RUN = False  # Set True only to verify the notebook; never report these metrics.
if FAST_RUN:
    train = stratified_debug_sample(train, 60_000)
    validation = stratified_debug_sample(validation, 20_000)
    test = stratified_debug_sample(test, 20_000)

TARGET = "isFraud"
DROP_FROM_MODEL = ["isFraud", "TransactionID"]
X_train, y_train = train.drop(columns=DROP_FROM_MODEL), train[TARGET].astype("int8")
X_validation, y_validation = validation.drop(columns=DROP_FROM_MODEL), validation[TARGET].astype("int8")
X_test, y_test = test.drop(columns=DROP_FROM_MODEL), test[TARGET].astype("int8")

print("Train:", X_train.shape, "fraud rate:", f"{y_train.mean():.4%}")
print("Validation:", X_validation.shape, "fraud rate:", f"{y_validation.mean():.4%}")
print("Test:", X_test.shape, "fraud rate:", f"{y_test.mean():.4%}")
'''


ARTIFACT_SETUP = r'''
from datetime import datetime, timezone
from src.fraud_pipeline.artifacts import build_manifest, package_versions, write_json
from src.fraud_pipeline.evaluation import evaluate_binary_classifier, select_operating_threshold

RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
RUN_DIR = ARTIFACT_ROOT / MODEL_KEY / RUN_ID
RUN_DIR.mkdir(parents=True, exist_ok=False)
print("This run will be saved to:", RUN_DIR)
'''


R2_UPLOAD = r'''
# Optional promotion step: upload this versioned run to a private Cloudflare R2 bucket.
# Create these as Lightning secrets/environment variables; never paste keys into a cell.
UPLOAD_TO_R2 = False

if UPLOAD_TO_R2:
    import boto3
    required_names = [
        "R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"
    ]
    absent = [name for name in required_names if not os.getenv(name)]
    if absent:
        raise RuntimeError("Missing Lightning secrets: " + ", ".join(absent))
    client = boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    prefix = f"{MODEL_KEY}/{RUN_ID}"
    for local_path in RUN_DIR.rglob("*"):
        if local_path.is_file():
            key = f"{prefix}/{local_path.relative_to(RUN_DIR).as_posix()}"
            client.upload_file(str(local_path), os.environ["R2_BUCKET_NAME"], key)
    print(f"Uploaded to r2://{os.environ['R2_BUCKET_NAME']}/{prefix}/")
else:
    print("R2 upload skipped. Set UPLOAD_TO_R2=True after configuring Lightning secrets.")
'''


def build_shared_notebook() -> None:
    cells = [
        md(r'''
        # 00 — Shared data preparation for Lightning AI

        **Owners:** Entire team  
        **Run once before all model notebooks.**

        This notebook downloads only the labelled training files, performs the required
        left join, creates row-level features available at prediction time, produces one
        chronological 70/15/15 split, and writes the common feature audit. Every model
        must use these exact partitions so the comparison is fair.

        Interview explanation: *“We define the data population and holdout periods once.
        Model-specific notebooks may learn different representations, but they cannot
        change which transactions belong to training, validation, or final testing.”*
        '''),
        md(r'''
        ## Before running

        1. Clone the GitHub repository into a persistent Lightning Studio.
        2. Accept the IEEE-CIS competition rules on Kaggle.
        3. Add the new Kaggle token as a Lightning secret named `KAGGLE_API_TOKEN`.
        4. Use a CPU machine with at least 16 GB RAM; 24–32 GB is safer.

        The GPU does not accelerate CSV loading or this join. Do not load the Kaggle test
        files during model development—the latest 15% of labelled training data is our
        honest holdout test period.
        '''),
        code(INSTALL_CELL),
        code(COMMON_SETUP),
        md(r'''
        ## 1. Download the competition archive safely

        The secret is read from the environment and never printed. Existing CSV files are
        reused, making the notebook restartable.
        '''),
        code(r'''
        import subprocess, zipfile

        RAW_DIR = PROJECT_ROOT / "data" / "raw" / "ieee-fraud-detection"
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        transaction_path = RAW_DIR / "train_transaction.csv"
        identity_path = RAW_DIR / "train_identity.csv"

        if not transaction_path.exists() or not identity_path.exists():
            if not os.getenv("KAGGLE_API_TOKEN"):
                raise RuntimeError(
                    "Add KAGGLE_API_TOKEN in Lightning secrets, restart the kernel, and rerun."
                )
            subprocess.run(
                ["kaggle", "competitions", "download", "-c", "ieee-fraud-detection", "-p", str(RAW_DIR)],
                check=True,
            )
            archive = RAW_DIR / "ieee-fraud-detection.zip"
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(RAW_DIR)

        print("Transaction file:", transaction_path)
        print("Identity file:", identity_path)
        '''),
        md(r'''
        ## 2. Load, validate, and left join

        A left join retains every transaction. Only about 24.42% have an identity row;
        an inner join would discard roughly three quarters of the labelled population.
        Numeric columns are downcast before the join to reduce RAM usage.
        '''),
        code(r'''
        from src.fraud_pipeline.common import reduce_memory_usage

        def memory_mb(frame):
            return frame.memory_usage(index=True, deep=True).sum() / 1024**2

        transactions = reduce_memory_usage(pd.read_csv(transaction_path))
        if not transactions["TransactionID"].is_unique:
            raise ValueError("train_transaction TransactionID must be unique")
        raw_source_columns = [c for c in transactions.columns if c != "isFraud"]
        print("Transactions:", transactions.shape, f"{memory_mb(transactions):,.1f} MB")

        identities = reduce_memory_usage(pd.read_csv(identity_path))
        if not identities["TransactionID"].is_unique:
            raise ValueError("train_identity TransactionID must be unique")
        raw_source_columns += [c for c in identities.columns if c != "TransactionID"]
        print("Identities:", identities.shape, f"{memory_mb(identities):,.1f} MB")

        identity_ids = set(identities["TransactionID"].to_numpy())
        transactions["has_identity"] = transactions["TransactionID"].isin(identity_ids).astype("int8")
        identity_ids.clear()

        joined = transactions.merge(
            identities,
            on="TransactionID",
            how="left",
            validate="one_to_one",
            sort=False,
            copy=False,
        )
        del transactions, identities
        gc.collect()

        assert len(joined) == 590_540
        assert joined["TransactionID"].is_unique
        assert joined["isFraud"].notna().all()
        raw_dtype_map = {column: str(joined[column].dtype) for column in raw_source_columns}
        print("Joined:", joined.shape, f"{memory_mb(joined):,.1f} MB")
        print("Fraud rate:", f"{joined['isFraud'].mean():.4%}")
        print("Identity coverage:", f"{joined['has_identity'].mean():.4%}")
        '''),
        md(r'''
        ## 3. Add shared, real-time-safe features

        These features use only values in the current row: amount transforms,
        missingness summaries, identity availability, relative time phases, and compact
        card/address/email combinations. No fraud labels or future transactions are used.

        `TransactionDT` has an undisclosed origin, so `transaction_relative_hour_phase`
        is a periodic phase—not a claim about the real local clock or weekend.
        '''),
        code(r'''
        from src.fraud_pipeline.common import add_shared_features

        joined = add_shared_features(joined, copy=False)
        print("After shared features:", joined.shape, f"{memory_mb(joined):,.1f} MB")
        display(joined[[
            "TransactionID", "TransactionAmt", "transaction_amount_log1p",
            "transaction_relative_day", "num_missing", "has_identity",
            "card_1_2", "isFraud"
        ]].head())
        '''),
        md(r'''
        ## 4. Freeze the chronological split and usable columns

        Constant/all-null decisions are learned from the training period only. The final
        15% is not used for feature selection, hyperparameter choice, or threshold choice.
        '''),
        code(r'''
        from src.fraud_pipeline.common import build_feature_audit, chronological_split

        train, validation, test, split_metadata = chronological_split(joined)
        del joined
        gc.collect()

        candidate_features = [c for c in train.columns if c not in {"isFraud", "TransactionID"}]
        unusable = [
            c for c in candidate_features
            if train[c].isna().all() or train[c].nunique(dropna=False) <= 1
        ]
        keep_columns = ["TransactionID", *[c for c in candidate_features if c not in unusable], "isFraud"]
        train = train[keep_columns]
        validation = validation[keep_columns]
        test = test[keep_columns]

        assert train["TransactionDT"].max() <= validation["TransactionDT"].min()
        assert validation["TransactionDT"].max() <= test["TransactionDT"].min()
        split_metadata["dropped_all_null_or_constant_from_training"] = unusable
        split_metadata["model_feature_count"] = len(keep_columns) - 2

        for name, frame in {"train": train, "validation": validation, "test": test}.items():
            print(name, frame.shape, f"fraud={frame['isFraud'].mean():.4%}")
        print("Dropped unusable columns:", len(unusable))
        '''),
        md(r'''
        ## 5. Save shared Parquet data, schema, and feature audit

        Parquet is substantially faster and smaller than repeatedly parsing CSV. The audit
        states why each column is numeric, categorical, or identifier-like and gives the
        intended representation for all four approaches.
        '''),
        code(r'''
        from src.fraud_pipeline.artifacts import write_json

        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        train.to_parquet(PROCESSED_DIR / "train.parquet", index=False, compression="zstd")
        validation.to_parquet(PROCESSED_DIR / "validation.parquet", index=False, compression="zstd")
        test.to_parquet(PROCESSED_DIR / "test.parquet", index=False, compression="zstd")

        audit = build_feature_audit(train)
        audit.to_csv(PROCESSED_DIR / "feature_audit.csv", index=False)
        write_json(PROCESSED_DIR / "split_metadata.json", split_metadata)
        write_json(PROCESSED_DIR / "shared_feature_config.json", {
            "version": "1.0",
            "target": "isFraud",
            "identifier": "TransactionID",
            "time_column": "TransactionDT",
            "engineered_features": [
                c for c in train.columns
                if c not in raw_source_columns and c not in {"isFraud"}
            ],
        })
        write_json(PROCESSED_DIR / "raw_input_schema.json", {
            "schema_version": "1.0",
            "columns": raw_source_columns,
            "dtypes_after_memory_reduction": raw_dtype_map,
            "required_for_demo": ["TransactionDT", "TransactionAmt", "ProductCD"],
            "optional_columns": [c for c in raw_source_columns if c not in {"TransactionID", "TransactionDT", "TransactionAmt", "ProductCD"}],
            "target_is_never_an_input": "isFraud",
            "missing_optional_fields": "created as null before shared feature engineering",
        })

        print("Saved:")
        for path in sorted(PROCESSED_DIR.iterdir()):
            print(f"  {path.name}: {path.stat().st_size / 1024**2:,.1f} MB")
        display(audit.head(12))
        '''),
        md(r'''
        ## Completion checklist

        - All 590,540 labelled transactions were retained before splitting.
        - Identity coverage and fraud prevalence were validated.
        - The split is chronological and shared by all teams.
        - No imputer, scaler, category vocabulary, or frequency map was fitted here.
        - Run notebooks `01`–`04` independently after this notebook finishes.
        '''),
    ]
    write_notebook("00_shared_data_preparation.ipynb", cells)


def build_logistic_notebook() -> None:
    cells = [
        md(r'''
        # 01 — Logistic Regression baseline

        **Owners:** Nanda / Khishan  
        **Role:** interpretable linear baseline

        Interview explanation: *“Logistic Regression establishes how much fraud signal can
        be captured by additive linear effects. Its coefficients are interpretable, and it
        provides a justified baseline before adopting more complex nonlinear models.”*
        '''),
        md(r'''
        ## Feature engineering for this approach

        - Real numerical quantities: training median imputation, missing indicators, scaling.
        - Low/medium-cardinality categories: rare grouping through `min_frequency`, then sparse one-hot encoding.
        - High-cardinality categories and numeric codes such as `card1`: training-only frequency encoding.
        - Continuous `V*`, `C*`, `D*`, and numeric `id_*` features are retained; high numerical uniqueness is not a reason to drop continuous measurements.
        - `class_weight="balanced"` addresses the 3.5% fraud prevalence without synthetic SMOTE records.

        Every learned transformation is inside the saved pipeline, preventing training-serving skew.
        '''),
        code(INSTALL_CELL),
        code(COMMON_SETUP),
        code(LOAD_SPLITS),
        code(r'''
        MODEL_KEY = "logistic_regression"
        '''),
        code(ARTIFACT_SETUP),
        md(r'''
        ## Build and train the complete serializable pipeline

        The sparse `saga` solver avoids materializing a huge dense one-hot matrix. A GPU is
        unnecessary for this model.
        '''),
        code(r'''
        import joblib
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from src.fraud_pipeline.preprocessing import build_logistic_preprocessor, infer_feature_groups

        groups = infer_feature_groups(X_train, low_cardinality_max=100)
        print({name: len(columns) for name, columns in groups.items()})
        preprocessor = build_logistic_preprocessor(groups, rare_min_count=20)
        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", LogisticRegression(
                C=0.1,
                penalty="l2",
                solver="saga",
                class_weight="balanced",
                max_iter=300,
                n_jobs=-1,
                random_state=RANDOM_SEED,
                verbose=1,
            )),
        ])

        started = time.perf_counter()
        pipeline.fit(X_train, y_train)
        training_seconds = time.perf_counter() - started
        print(f"Training time: {training_seconds / 60:.1f} minutes")
        '''),
        md(r'''
        ## Select the threshold on validation, evaluate holdout once

        PR-AUC is primary because accuracy is misleading for rare fraud. The threshold
        maximizes recall while satisfying a configurable minimum validation precision.
        '''),
        code(r'''
        validation_probability = pipeline.predict_proba(X_validation)[:, 1]
        threshold_record = select_operating_threshold(
            y_validation.to_numpy(), validation_probability, minimum_precision=0.10
        )
        threshold = float(threshold_record["threshold"])
        validation_metrics = evaluate_binary_classifier(y_validation, validation_probability, threshold)

        started = time.perf_counter()
        test_probability = pipeline.predict_proba(X_test)[:, 1]
        prediction_seconds = time.perf_counter() - started
        test_metrics = evaluate_binary_classifier(y_test, test_probability, threshold)

        display(pd.DataFrame([validation_metrics, test_metrics], index=["validation", "test"])[
            ["pr_auc", "roc_auc", "precision", "recall", "f1", "brier_score"]
        ])
        print("Selected threshold:", threshold_record)
        '''),
        md(r'''
        ## Explain coefficients and save the deployment bundle

        Positive coefficients increase the fraud log-odds; negative coefficients decrease
        them. Association does not prove causality.
        '''),
        code(r'''
        feature_names = pipeline.named_steps["preprocessor"].get_feature_names_out()
        coefficients = pipeline.named_steps["classifier"].coef_[0]
        importance = pd.DataFrame({"feature": feature_names, "coefficient": coefficients})
        importance["absolute_coefficient"] = importance["coefficient"].abs()
        importance.sort_values("absolute_coefficient", ascending=False).head(100).to_csv(
            RUN_DIR / "top_coefficients.csv", index=False
        )

        model_path = RUN_DIR / "model.joblib"
        joblib.dump(pipeline, model_path, compress=3)
        pd.DataFrame({"TransactionID": validation["TransactionID"], "isFraud": y_validation, "probability": validation_probability}).to_parquet(RUN_DIR / "validation_predictions.parquet", index=False)
        pd.DataFrame({"TransactionID": test["TransactionID"], "isFraud": y_test, "probability": test_probability}).to_parquet(RUN_DIR / "test_predictions.parquet", index=False)
        write_json(RUN_DIR / "threshold.json", threshold_record)
        write_json(RUN_DIR / "metrics.json", {"validation": validation_metrics, "test": test_metrics})
        write_json(RUN_DIR / "feature_schema.json", {"model": MODEL_KEY, "groups": groups, "raw_input_contract": "data/processed/raw_input_schema.json"})
        write_json(RUN_DIR / "training_config.json", {
            "model": MODEL_KEY, "run_id": RUN_ID, "random_seed": RANDOM_SEED,
            "fast_run": FAST_RUN, "training_seconds": training_seconds,
            "test_prediction_seconds": prediction_seconds,
            "test_rows_per_second": len(X_test) / prediction_seconds,
            "parameters": pipeline.named_steps["classifier"].get_params(),
            "versions": package_versions(["numpy", "pandas", "scikit-learn", "joblib"]),
        })
        '''),
        md(r'''
        ## Mandatory reload test

        A model is not complete until its disk artifact reproduces the in-memory scores.
        This is the exact operation the future FastAPI backend will perform.
        '''),
        code(r'''
        reloaded = joblib.load(model_path)
        before = pipeline.predict_proba(X_validation.iloc[:5])[:, 1]
        after = reloaded.predict_proba(X_validation.iloc[:5])[:, 1]
        np.testing.assert_allclose(before, after, rtol=1e-7, atol=1e-9)
        write_json(RUN_DIR / "manifest.json", build_manifest(RUN_DIR))
        print("Reload test passed:", after)
        print("Artifact directory:", RUN_DIR)
        '''),
        code(R2_UPLOAD),
        md(r'''
        ## Interview checklist

        Be ready to explain: why scaling is needed, why identifier codes are not quantities,
        why high-cardinality fields are not blindly one-hot encoded, why accuracy is not the
        main metric, and why the validation threshold is reused unchanged on the holdout.
        '''),
    ]
    write_notebook("01_logistic_regression_nanda_khishan.ipynb", cells)


def build_lightgbm_notebook() -> None:
    cells = [
        md(r'''
        # 02 — LightGBM benchmark

        **Owners:** Nebal / Ajmeer  
        **Role:** high-performance nonlinear tree benchmark

        Interview explanation: *“LightGBM learns nonlinear thresholds and interactions in
        wide tabular data. It handles numerical missing values directly and does not require
        scaling, making it both performant and efficient.”*
        '''),
        md(r'''
        ## Feature engineering for this approach

        - Numerical quantities retain `NaN`; trees learn a missing-value branch.
        - Low/medium-cardinality labels use stable training-only categorical levels.
        - Rare training labels become `OTHER`; future unseen labels become `UNKNOWN`.
        - High-cardinality labels and identifier-like numeric codes become frequency features.
        - No standardization is used because split thresholds are invariant to scale.
        - `scale_pos_weight` is calculated from the training partition only.
        '''),
        code(INSTALL_CELL),
        code(COMMON_SETUP),
        code(LOAD_SPLITS),
        code(r'''
        MODEL_KEY = "lightgbm"
        '''),
        code(ARTIFACT_SETUP),
        md(r'''
        ## Fit preprocessing on training only

        The saved preprocessor contains category levels and frequency maps. Validation,
        holdout, API requests, and batch predictions must use this same object.
        '''),
        code(r'''
        import joblib, lightgbm as lgb
        from src.fraud_pipeline.preprocessing import LightGBMPreprocessor

        preprocessor = LightGBMPreprocessor(low_cardinality_max=100, rare_min_count=20).fit(X_train)
        X_train_model = preprocessor.transform(X_train)
        X_validation_model = preprocessor.transform(X_validation)
        print("Model matrix:", X_train_model.shape)
        print("Native categorical columns:", len(preprocessor.categorical_features))
        '''),
        md(r'''
        ## Train with early stopping

        Early stopping chooses the tree count using the validation period. Hyperparameters
        should be changed only after recording this baseline.
        '''),
        code(r'''
        negative, positive = np.bincount(y_train)
        scale_pos_weight = float(negative / positive)
        model = lgb.LGBMClassifier(
            objective="binary",
            n_estimators=5000,
            learning_rate=0.03,
            num_leaves=64,
            max_depth=-1,
            min_child_samples=50,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=1.0,
            scale_pos_weight=scale_pos_weight,
            random_state=RANDOM_SEED,
            n_jobs=-1,
        )
        started = time.perf_counter()
        model.fit(
            X_train_model,
            y_train,
            eval_set=[(X_validation_model, y_validation)],
            eval_metric="average_precision",
            categorical_feature=preprocessor.categorical_features,
            callbacks=[lgb.early_stopping(200), lgb.log_evaluation(100)],
        )
        training_seconds = time.perf_counter() - started
        print("Best iteration:", model.best_iteration_)
        '''),
        md(r'''
        ## Validation threshold and final holdout evaluation
        '''),
        code(r'''
        validation_probability = model.predict_proba(X_validation_model, num_iteration=model.best_iteration_)[:, 1]
        threshold_record = select_operating_threshold(y_validation, validation_probability, minimum_precision=0.10)
        threshold = float(threshold_record["threshold"])
        validation_metrics = evaluate_binary_classifier(y_validation, validation_probability, threshold)

        del X_train_model
        gc.collect()
        X_test_model = preprocessor.transform(X_test)
        started = time.perf_counter()
        test_probability = model.predict_proba(X_test_model, num_iteration=model.best_iteration_)[:, 1]
        prediction_seconds = time.perf_counter() - started
        test_metrics = evaluate_binary_classifier(y_test, test_probability, threshold)
        display(pd.DataFrame([validation_metrics, test_metrics], index=["validation", "test"])[["pr_auc", "roc_auc", "precision", "recall", "f1", "brier_score"]])
        '''),
        md(r'''
        ## Importance and native-format artifact

        Gain importance shows which features reduced training loss most; it does not prove
        causality. SHAP can be added after the baseline if memory permits.
        '''),
        code(r'''
        importance = pd.DataFrame({
            "feature": model.booster_.feature_name(),
            "gain": model.booster_.feature_importance(importance_type="gain"),
            "split": model.booster_.feature_importance(importance_type="split"),
        }).sort_values("gain", ascending=False)
        importance.head(100).to_csv(RUN_DIR / "feature_importance.csv", index=False)

        model_path = RUN_DIR / "model.txt"
        model.booster_.save_model(str(model_path), num_iteration=model.best_iteration_)
        preprocessor_path = RUN_DIR / "preprocessor.joblib"
        joblib.dump(preprocessor, preprocessor_path, compress=3)
        pd.DataFrame({"TransactionID": validation["TransactionID"], "isFraud": y_validation, "probability": validation_probability}).to_parquet(RUN_DIR / "validation_predictions.parquet", index=False)
        pd.DataFrame({"TransactionID": test["TransactionID"], "isFraud": y_test, "probability": test_probability}).to_parquet(RUN_DIR / "test_predictions.parquet", index=False)
        write_json(RUN_DIR / "threshold.json", threshold_record)
        write_json(RUN_DIR / "metrics.json", {"validation": validation_metrics, "test": test_metrics})
        write_json(RUN_DIR / "feature_schema.json", {"model": MODEL_KEY, "groups": preprocessor.groups, "categorical_features": preprocessor.categorical_features})
        write_json(RUN_DIR / "training_config.json", {
            "model": MODEL_KEY, "run_id": RUN_ID, "random_seed": RANDOM_SEED,
            "fast_run": FAST_RUN, "training_seconds": training_seconds,
            "test_prediction_seconds": prediction_seconds,
            "best_iteration": model.best_iteration_, "scale_pos_weight": scale_pos_weight,
            "parameters": model.get_params(),
            "versions": package_versions(["numpy", "pandas", "scikit-learn", "lightgbm", "joblib"]),
        })
        '''),
        md(r'''
        ## Mandatory reload test
        '''),
        code(r'''
        loaded_preprocessor = joblib.load(preprocessor_path)
        loaded_model = lgb.Booster(model_file=str(model_path))
        sample_matrix = loaded_preprocessor.transform(X_validation.iloc[:5])
        before = model.predict_proba(X_validation_model.iloc[:5], num_iteration=model.best_iteration_)[:, 1]
        after = loaded_model.predict(sample_matrix)
        np.testing.assert_allclose(before, after, rtol=1e-6, atol=1e-8)
        write_json(RUN_DIR / "manifest.json", build_manifest(RUN_DIR))
        print("Reload test passed:", after)
        print("Artifact directory:", RUN_DIR)
        '''),
        code(R2_UPLOAD),
        md(r'''
        ## Interview checklist

        Be ready to explain missing-value branches, native categoricals versus frequency
        encoding, boosting, early stopping, `scale_pos_weight`, PR-AUC, and why scaling is
        unnecessary for decision trees.
        '''),
    ]
    write_notebook("02_lightgbm_nebal_ajmeer.ipynb", cells)


def build_catboost_notebook() -> None:
    cells = [
        md(r'''
        # 03 — CatBoost categorical-aware model

        **Owners:** Midhun / Saravana  
        **Role:** primary mixed-type deployment candidate

        Interview explanation: *“CatBoost is designed for categorical tabular data. Its
        ordered categorical statistics reduce target leakage and let us retain card, email,
        device, and address identities without producing a huge one-hot matrix.”*
        '''),
        md(r'''
        ## Feature engineering for this approach

        - Numeric quantities remain numeric with `NaN`; no scaling is needed.
        - Text categories and numeric identifier codes become categorical strings.
        - Missing categorical values become the explicit label `MISSING`.
        - High cardinality is handled natively by CatBoost's ordered categorical statistics.
        - We do not add manual target encoding, avoiding duplicate complexity and leakage risk.
        - Class weights are calculated using the training period only.
        '''),
        code(INSTALL_CELL),
        code(COMMON_SETUP),
        code(LOAD_SPLITS),
        code(r'''
        MODEL_KEY = "catboost"
        '''),
        code(ARTIFACT_SETUP),
        md(r'''
        ## Fit the stable CatBoost input contract

        The transformation records exact feature order and categorical names. This object
        will later transform the same common API input.
        '''),
        code(r'''
        import joblib, torch
        from catboost import CatBoostClassifier, Pool
        from src.fraud_pipeline.preprocessing import CatBoostPreprocessor

        preprocessor = CatBoostPreprocessor().fit(X_train)
        X_train_model = preprocessor.transform(X_train)
        X_validation_model = preprocessor.transform(X_validation)
        print("Features:", X_train_model.shape[1])
        print("Categorical features:", len(preprocessor.categorical_features))
        '''),
        md(r'''
        ## Train with early stopping

        Set `USE_GPU=False` if the Lightning Studio is on CPU. GPU CatBoost is faster but
        can produce very small numerical differences from CPU runs.
        '''),
        code(r'''
        USE_GPU = torch.cuda.is_available()
        negative, positive = np.bincount(y_train)
        class_weight = float(negative / positive)

        train_pool = Pool(X_train_model, y_train, cat_features=preprocessor.categorical_features)
        validation_pool = Pool(X_validation_model, y_validation, cat_features=preprocessor.categorical_features)
        catboost_parameters = dict(
            iterations=4000,
            learning_rate=0.05,
            depth=8,
            loss_function="Logloss",
            eval_metric="AUC",
            class_weights=[1.0, class_weight],
            l2_leaf_reg=5.0,
            random_seed=RANDOM_SEED,
            task_type="GPU" if USE_GPU else "CPU",
            allow_writing_files=False,
            verbose=100,
        )
        if USE_GPU:
            catboost_parameters["devices"] = "0"
        model = CatBoostClassifier(**catboost_parameters)
        started = time.perf_counter()
        model.fit(train_pool, eval_set=validation_pool, early_stopping_rounds=200, use_best_model=True)
        training_seconds = time.perf_counter() - started
        print("Best iteration:", model.get_best_iteration())
        '''),
        md(r'''
        ## Validation threshold and final holdout evaluation
        '''),
        code(r'''
        validation_probability = model.predict_proba(validation_pool)[:, 1]
        threshold_record = select_operating_threshold(y_validation, validation_probability, minimum_precision=0.10)
        threshold = float(threshold_record["threshold"])
        validation_metrics = evaluate_binary_classifier(y_validation, validation_probability, threshold)

        del train_pool, X_train_model
        gc.collect()
        X_test_model = preprocessor.transform(X_test)
        test_pool = Pool(X_test_model, y_test, cat_features=preprocessor.categorical_features)
        started = time.perf_counter()
        test_probability = model.predict_proba(test_pool)[:, 1]
        prediction_seconds = time.perf_counter() - started
        test_metrics = evaluate_binary_classifier(y_test, test_probability, threshold)
        display(pd.DataFrame([validation_metrics, test_metrics], index=["validation", "test"])[["pr_auc", "roc_auc", "precision", "recall", "f1", "brier_score"]])
        '''),
        md(r'''
        ## Importance, native `.cbm` model, and supporting contract
        '''),
        code(r'''
        importance = pd.DataFrame({
            "feature": preprocessor.feature_columns,
            "importance": model.get_feature_importance(validation_pool),
        }).sort_values("importance", ascending=False)
        importance.head(100).to_csv(RUN_DIR / "feature_importance.csv", index=False)

        model_path = RUN_DIR / "model.cbm"
        model.save_model(str(model_path), format="cbm")
        preprocessor_path = RUN_DIR / "preprocessor.joblib"
        joblib.dump(preprocessor, preprocessor_path, compress=3)
        pd.DataFrame({"TransactionID": validation["TransactionID"], "isFraud": y_validation, "probability": validation_probability}).to_parquet(RUN_DIR / "validation_predictions.parquet", index=False)
        pd.DataFrame({"TransactionID": test["TransactionID"], "isFraud": y_test, "probability": test_probability}).to_parquet(RUN_DIR / "test_predictions.parquet", index=False)
        write_json(RUN_DIR / "threshold.json", threshold_record)
        write_json(RUN_DIR / "metrics.json", {"validation": validation_metrics, "test": test_metrics})
        write_json(RUN_DIR / "feature_schema.json", {"model": MODEL_KEY, "feature_columns": preprocessor.feature_columns, "categorical_features": preprocessor.categorical_features})
        write_json(RUN_DIR / "training_config.json", {
            "model": MODEL_KEY, "run_id": RUN_ID, "random_seed": RANDOM_SEED,
            "fast_run": FAST_RUN, "training_seconds": training_seconds,
            "test_prediction_seconds": prediction_seconds, "use_gpu": USE_GPU,
            "best_iteration": model.get_best_iteration(), "class_weight": class_weight,
            "parameters": model.get_params(),
            "versions": package_versions(["numpy", "pandas", "catboost", "joblib"]),
        })
        '''),
        md(r'''
        ## Mandatory reload test
        '''),
        code(r'''
        loaded_preprocessor = joblib.load(preprocessor_path)
        loaded_model = CatBoostClassifier()
        loaded_model.load_model(str(model_path))
        sample = loaded_preprocessor.transform(X_validation.iloc[:5])
        sample_pool = Pool(sample, cat_features=loaded_preprocessor.categorical_features)
        before = model.predict_proba(validation_pool.slice(list(range(5))))[:, 1]
        after = loaded_model.predict_proba(sample_pool)[:, 1]
        np.testing.assert_allclose(before, after, rtol=1e-6, atol=1e-8)
        write_json(RUN_DIR / "manifest.json", build_manifest(RUN_DIR))
        print("Reload test passed:", after)
        print("Artifact directory:", RUN_DIR)
        '''),
        code(R2_UPLOAD),
        md(r'''
        ## Interview checklist

        Be ready to explain ordered categorical statistics, why code-like numeric fields are
        strings here, why missing categories are explicit, why CatBoost does not require
        scaling, and how the native model plus saved preprocessor reaches the API.
        '''),
    ]
    write_notebook("03_catboost_midhun_saravana.ipynb", cells)


def build_neural_notebook() -> None:
    cells = [
        md(r'''
        # 04 — Embedding-based tabular neural network

        **Owners:** Mirdula / Hashvitha  
        **Role:** deep-learning benchmark for mixed numerical and high-cardinality data

        Interview explanation: *“The network learns compact embeddings for categorical
        identities such as cards, emails, and devices, combines them with standardized
        numerical fraud signals, and optimizes a class-weighted binary objective.”*
        '''),
        md(r'''
        ## Feature engineering for this approach

        - Numeric values: training median, missing indicator, standardization.
        - Categories and identifier codes: `MISSING`, `OTHER`, and `UNKNOWN` tokens.
        - Categories seen fewer than 20 times become the `OTHER` embedding during training.
        - Future unseen values receive `UNKNOWN`, not an accidental training category.
        - One embedding table is learned per categorical feature; no huge one-hot matrix.
        - `BCEWithLogitsLoss(pos_weight=...)` addresses class imbalance.
        '''),
        code(INSTALL_CELL),
        code(COMMON_SETUP),
        code(LOAD_SPLITS),
        code(r'''
        MODEL_KEY = "neural_network"
        '''),
        code(ARTIFACT_SETUP),
        md(r'''
        ## Fit preprocessing and create tensors

        The fitted preprocessor is part of the deployment bundle. Array creation uses CPU
        RAM; switch to a Lightning machine with more memory if the kernel is killed.
        '''),
        code(r'''
        import joblib, torch
        from torch import nn
        from torch.utils.data import DataLoader, TensorDataset
        from sklearn.metrics import average_precision_score
        from src.fraud_pipeline.neural import FraudTabularNetwork, embedding_dimension, network_from_config
        from src.fraud_pipeline.preprocessing import NeuralTabularPreprocessor

        preprocessor = NeuralTabularPreprocessor(rare_min_count=20).fit(X_train)
        train_numeric, train_categorical = preprocessor.transform(X_train)
        validation_numeric, validation_categorical = preprocessor.transform(X_validation)
        print("Numerical tensor:", train_numeric.shape)
        print("Categorical tensor:", train_categorical.shape)
        print("Embedding fields:", len(preprocessor.cardinalities))
        '''),
        md(r'''
        ## Define the architecture

        Embedding dimensions grow with vocabulary size but are capped at 32. Dense layers
        use ReLU and dropout to learn nonlinear interactions while controlling overfitting.
        Numeric inputs are already standardized, so batch-dependent normalization is not required.
        '''),
        code(r'''
        embedding_dimensions = [embedding_dimension(c) for c in preprocessor.cardinalities]
        model_config = {
            "numeric_size": preprocessor.numeric_output_size,
            "cardinalities": preprocessor.cardinalities,
            "embedding_dimensions": embedding_dimensions,
            "categorical_columns": preprocessor.categorical_columns,
            "hidden_layers": [256, 128, 64],
            "dropout": [0.30, 0.20, 0.10],
        }
        model = FraudTabularNetwork(**{
            key: model_config[key]
            for key in ["numeric_size", "cardinalities", "embedding_dimensions"]
        })
        print(model)
        '''),
        md(r'''
        ## Train with mixed precision and validation PR-AUC early stopping

        T4 is recommended. The best state is retained, not simply the final epoch.
        '''),
        code(r'''
        BATCH_SIZE = 4096
        MAX_EPOCHS = 20
        PATIENCE = 4
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = model.to(device)

        train_dataset = TensorDataset(
            torch.from_numpy(train_numeric),
            torch.from_numpy(train_categorical),
            torch.from_numpy(y_train.to_numpy(dtype=np.float32)),
        )
        validation_dataset = TensorDataset(
            torch.from_numpy(validation_numeric),
            torch.from_numpy(validation_categorical),
            torch.from_numpy(y_validation.to_numpy(dtype=np.float32)),
        )
        train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=2, pin_memory=device.type == "cuda")
        validation_loader = DataLoader(validation_dataset, batch_size=BATCH_SIZE * 2, shuffle=False, num_workers=2, pin_memory=device.type == "cuda")

        negative, positive = np.bincount(y_train)
        loss_function = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(negative / positive, device=device))
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")

        def predict_loader(model, loader):
            model.eval()
            probabilities, labels = [], []
            with torch.inference_mode():
                for numeric, categorical, target in loader:
                    numeric, categorical = numeric.to(device), categorical.to(device)
                    logits = model(numeric, categorical)
                    probabilities.append(torch.sigmoid(logits).cpu().numpy())
                    labels.append(target.numpy())
            return np.concatenate(probabilities), np.concatenate(labels)

        best_pr_auc = -np.inf
        best_state = None
        epochs_without_improvement = 0
        history = []
        started = time.perf_counter()

        for epoch in range(1, MAX_EPOCHS + 1):
            model.train()
            total_loss = 0.0
            for numeric, categorical, target in train_loader:
                numeric = numeric.to(device, non_blocking=True)
                categorical = categorical.to(device, non_blocking=True)
                target = target.to(device, non_blocking=True)
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == "cuda"):
                    logits = model(numeric, categorical)
                    loss = loss_function(logits, target)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
                total_loss += loss.item() * len(target)

            validation_probability, validation_label = predict_loader(model, validation_loader)
            validation_pr_auc = average_precision_score(validation_label, validation_probability)
            epoch_loss = total_loss / len(train_dataset)
            history.append({"epoch": epoch, "train_loss": epoch_loss, "validation_pr_auc": validation_pr_auc})
            print(f"epoch={epoch:02d} loss={epoch_loss:.5f} validation_pr_auc={validation_pr_auc:.5f}")

            if validation_pr_auc > best_pr_auc + 1e-5:
                best_pr_auc = validation_pr_auc
                best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
                epochs_without_improvement = 0
            else:
                epochs_without_improvement += 1
                if epochs_without_improvement >= PATIENCE:
                    print("Early stopping")
                    break

        training_seconds = time.perf_counter() - started
        model.load_state_dict(best_state)
        model.to(device)
        pd.DataFrame(history).to_csv(RUN_DIR / "training_history.csv", index=False)
        '''),
        md(r'''
        ## Validation threshold and final holdout evaluation
        '''),
        code(r'''
        validation_probability, _ = predict_loader(model, validation_loader)
        threshold_record = select_operating_threshold(y_validation, validation_probability, minimum_precision=0.10)
        threshold = float(threshold_record["threshold"])
        validation_metrics = evaluate_binary_classifier(y_validation, validation_probability, threshold)

        test_numeric, test_categorical = preprocessor.transform(X_test)
        test_dataset = TensorDataset(
            torch.from_numpy(test_numeric), torch.from_numpy(test_categorical),
            torch.from_numpy(y_test.to_numpy(dtype=np.float32)),
        )
        test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE * 2, shuffle=False, num_workers=2, pin_memory=device.type == "cuda")
        started = time.perf_counter()
        test_probability, _ = predict_loader(model, test_loader)
        prediction_seconds = time.perf_counter() - started
        test_metrics = evaluate_binary_classifier(y_test, test_probability, threshold)
        display(pd.DataFrame([validation_metrics, test_metrics], index=["validation", "test"])[["pr_auc", "roc_auc", "precision", "recall", "f1", "brier_score"]])
        '''),
        md(r'''
        ## Save state dictionary, architecture, preprocessing, and predictions

        Saving `state_dict` plus an explicit architecture config is safer and more portable
        than pickling the entire Python model object.
        '''),
        code(r'''
        model_path = RUN_DIR / "model.pt"
        torch.save({
            "model_state_dict": {key: value.cpu() for key, value in model.state_dict().items()},
            "model_config": model_config,
            "best_validation_pr_auc": best_pr_auc,
        }, model_path)
        preprocessor_path = RUN_DIR / "numeric_and_categorical_preprocessor.joblib"
        joblib.dump(preprocessor, preprocessor_path, compress=3)
        write_json(RUN_DIR / "model_config.json", model_config)
        write_json(RUN_DIR / "category_vocabulary_summary.json", {
            column: {"cardinality": len(preprocessor.vocabularies[column]), "reserved": {"MISSING": 0, "UNKNOWN": 1, "OTHER": 2}}
            for column in preprocessor.categorical_columns
        })
        pd.DataFrame({"TransactionID": validation["TransactionID"], "isFraud": y_validation, "probability": validation_probability}).to_parquet(RUN_DIR / "validation_predictions.parquet", index=False)
        pd.DataFrame({"TransactionID": test["TransactionID"], "isFraud": y_test, "probability": test_probability}).to_parquet(RUN_DIR / "test_predictions.parquet", index=False)
        write_json(RUN_DIR / "threshold.json", threshold_record)
        write_json(RUN_DIR / "metrics.json", {"validation": validation_metrics, "test": test_metrics})
        write_json(RUN_DIR / "feature_schema.json", {"model": MODEL_KEY, "groups": preprocessor.groups, "categorical_columns": preprocessor.categorical_columns})
        write_json(RUN_DIR / "training_config.json", {
            "model": MODEL_KEY, "run_id": RUN_ID, "random_seed": RANDOM_SEED,
            "fast_run": FAST_RUN, "training_seconds": training_seconds,
            "test_prediction_seconds": prediction_seconds, "device": str(device),
            "batch_size": BATCH_SIZE, "max_epochs": MAX_EPOCHS,
            "best_validation_pr_auc": best_pr_auc,
            "versions": package_versions(["numpy", "pandas", "scikit-learn", "torch", "joblib"]),
        })
        '''),
        md(r'''
        ## Mandatory reload test
        '''),
        code(r'''
        loaded_preprocessor = joblib.load(preprocessor_path)
        checkpoint = torch.load(model_path, map_location="cpu", weights_only=True)
        loaded_model = network_from_config(checkpoint["model_config"])
        loaded_model.load_state_dict(checkpoint["model_state_dict"])
        loaded_model.eval()
        sample_numeric, sample_categorical = loaded_preprocessor.transform(X_validation.iloc[:5])
        with torch.inference_mode():
            after = torch.sigmoid(loaded_model(torch.from_numpy(sample_numeric), torch.from_numpy(sample_categorical))).numpy()
        before = validation_probability[:5]
        np.testing.assert_allclose(before, after, rtol=1e-5, atol=1e-7)
        write_json(RUN_DIR / "manifest.json", build_manifest(RUN_DIR))
        print("Reload test passed:", after)
        print("Artifact directory:", RUN_DIR)
        '''),
        code(R2_UPLOAD),
        md(r'''
        ## Interview checklist

        Be ready to explain embeddings, reserved category tokens, numeric scaling, missing
        indicators, class-weighted BCE loss, logits versus probabilities, dropout,
        standardized inputs, mixed precision, dropout, and early stopping on validation PR-AUC.
        '''),
    ]
    write_notebook("04_tabular_neural_network_mirdula_hashvitha.ipynb", cells)


def main() -> None:
    build_shared_notebook()
    build_logistic_notebook()
    build_lightgbm_notebook()
    build_catboost_notebook()
    build_neural_notebook()
    print(f"Built 5 notebooks in {OUTPUT}")


if __name__ == "__main__":
    main()
