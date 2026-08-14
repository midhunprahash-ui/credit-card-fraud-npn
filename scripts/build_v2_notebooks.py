"""Generate the additive Version 2 training notebooks.

Version 1 notebooks are intentionally not read, edited, renamed, or deleted.
Run: python3 scripts/build_v2_notebooks.py
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "lightning_ai" / "v2"


def md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": dedent(source).strip() + "\n"}


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
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    (OUTPUT / filename).write_text(json.dumps(notebook, indent=1) + "\n")


INSTALL = r'''
from pathlib import Path
_start = Path.cwd().resolve()
for _candidate in [_start, *_start.parents]:
    if (_candidate / "requirements-training.txt").exists():
        _requirements = _candidate / "requirements-training.txt"
        break
else:
    raise FileNotFoundError("Open this notebook from inside the cloned repository")
%pip install -q -r {_requirements}
'''


SETUP = r'''
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

V2_DATA_DIR = PROJECT_ROOT / "data" / "processed" / "v2"
V2_ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "v2"
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
print("Project root:", PROJECT_ROOT)
print("Version 2 data:", V2_DATA_DIR)
print("Version 2 artifacts:", V2_ARTIFACT_ROOT)
'''


LOAD_V2 = r'''
required = [V2_DATA_DIR / name for name in ["train.parquet", "validation.parquet", "test.parquet"]]
missing = [str(path) for path in required if not path.exists()]
if missing:
    raise FileNotFoundError(
        "Run 10_v2_behavioral_data_preparation.ipynb first. Missing: " + ", ".join(missing)
    )

train, validation, test = [pd.read_parquet(path) for path in required]
FAST_RUN = False  # Only for code checks. Never report FAST_RUN metrics.
if FAST_RUN:
    def debug_sample(frame, rows):
        return (frame.groupby("isFraud", group_keys=False)
                .apply(lambda group: group.sample(
                    n=max(1, round(rows * len(group) / len(frame))),
                    random_state=RANDOM_SEED), include_groups=True)
                .sort_values(["TransactionDT", "TransactionID"]).reset_index(drop=True))
    train = debug_sample(train, 60_000)
    validation = debug_sample(validation, 20_000)
    test = debug_sample(test, 20_000)

TARGET = "isFraud"
DROP_FROM_MODEL = ["isFraud", "TransactionID"]
X_train, y_train = train.drop(columns=DROP_FROM_MODEL), train[TARGET].astype("int8")
X_validation, y_validation = validation.drop(columns=DROP_FROM_MODEL), validation[TARGET].astype("int8")
X_test, y_test = test.drop(columns=DROP_FROM_MODEL), test[TARGET].astype("int8")
development = pd.concat([train, validation], ignore_index=True)
print("Train:", X_train.shape, "fraud rate:", f"{y_train.mean():.4%}")
print("Validation:", X_validation.shape, "fraud rate:", f"{y_validation.mean():.4%}")
print("Test:", X_test.shape, "fraud rate:", f"{y_test.mean():.4%}")
'''


ARTIFACT_SETUP = r'''
from datetime import datetime, timezone
from src.fraud_pipeline.artifacts import build_manifest, package_versions, write_json
from src.fraud_pipeline.evaluation import evaluate_binary_classifier, select_operating_threshold

RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
RUN_DIR = V2_ARTIFACT_ROOT / MODEL_KEY / RUN_ID
RUN_DIR.mkdir(parents=True, exist_ok=False)
print("This Version 2 run will be saved to:", RUN_DIR)
'''


PACKAGE_RUN = r'''
import shutil
write_json(RUN_DIR / "manifest.json", build_manifest(RUN_DIR))
archive_base = RUN_DIR.parent / f"{MODEL_KEY}_{RUN_ID}"
archive_path = Path(shutil.make_archive(str(archive_base), "gztar", root_dir=RUN_DIR))
print("Reload check passed.")
print("Artifact folder:", RUN_DIR)
print("Share this archive:", archive_path)
'''


WHY_V2 = r'''
## What Version 2 changes—and why

Version 1 remains our reproducible baseline. Version 2 adds behaviour that the
winning Kaggle solution showed was valuable, but implements it in a stricter
real-time form:

- `D` values are normalized against transaction day to expose stable date anchors.
- a conservative `uid_proxy` describes a possible client without using it as a label;
- counts, time since previous use, amount history and unique-value history describe
  behaviour;
- every historical feature uses only earlier transactions; and
- no feature reads `isFraud`, later rows, validation labels, or test labels.

The newest 15% remains the final test period. It is never used for feature or
hyperparameter selection.
'''


def build_preparation() -> None:
    cells = [
        md(r'''
        # 10 — Version 2 behavioural data preparation

        **Owners:** Entire team  
        **Run once before notebooks 11–15.**

        This creates new files under `data/processed/v2`. It does not modify the
        Version 1 Parquet files or notebooks.
        '''),
        md(WHY_V2),
        code(INSTALL),
        code(SETUP),
        md(r'''
        ## 1. Locate or download the labelled files

        Existing CSVs or the existing competition ZIP are reused. If neither exists,
        set `KAGGLE_API_TOKEN` in the machine's environment. Accept the competition
        rules on Kaggle before running.
        '''),
        code(r'''
        import subprocess, zipfile

        RAW_DIR = PROJECT_ROOT / "data" / "raw" / "ieee-fraud-detection"
        RAW_DIR.mkdir(parents=True, exist_ok=True)

        def discover(name):
            matches = list(RAW_DIR.rglob(name))
            return matches[0] if matches else None

        transaction_path = discover("train_transaction.csv")
        identity_path = discover("train_identity.csv")
        archive = RAW_DIR / "ieee-fraud-detection.zip"

        if transaction_path is None or identity_path is None:
            if archive.exists():
                with zipfile.ZipFile(archive) as source:
                    source.extractall(RAW_DIR)
            elif os.getenv("KAGGLE_API_TOKEN"):
                subprocess.run(
                    ["kaggle", "competitions", "download", "-c", "ieee-fraud-detection", "-p", str(RAW_DIR)],
                    check=True,
                )
                with zipfile.ZipFile(archive) as source:
                    source.extractall(RAW_DIR)
            else:
                raise RuntimeError(
                    "Place ieee-fraud-detection.zip in data/raw/ieee-fraud-detection or set KAGGLE_API_TOKEN."
                )
            transaction_path = discover("train_transaction.csv")
            identity_path = discover("train_identity.csv")

        if transaction_path is None or identity_path is None:
            raise FileNotFoundError("The archive did not contain both labelled training CSV files")
        print(transaction_path)
        print(identity_path)
        '''),
        md(r'''
        ## 2. Load and left join

        The transaction table defines the population. A left join preserves transactions
        without identity/device records; missing identity is itself a useful signal.
        `validate="one_to_one"` prevents accidental row multiplication.
        '''),
        code(r'''
        from src.fraud_pipeline.common import reduce_memory_usage

        transactions = reduce_memory_usage(pd.read_csv(transaction_path))
        identity = reduce_memory_usage(pd.read_csv(identity_path))
        if not transactions["TransactionID"].is_unique:
            raise ValueError("Transaction IDs must be unique in train_transaction")
        if not identity["TransactionID"].is_unique:
            raise ValueError("Transaction IDs must be unique in train_identity")

        raw_columns = list(transactions.columns) + [c for c in identity.columns if c != "TransactionID"]
        joined = transactions.merge(identity, on="TransactionID", how="left", validate="one_to_one")
        if len(joined) != len(transactions):
            raise AssertionError("Left join changed the transaction row count")
        print("Joined shape:", joined.shape)
        del transactions, identity
        gc.collect()
        '''),
        md(r'''
        ## 3. Generate strictly historical features

        The dataframe is sorted by `TransactionDT` and `TransactionID`. Cumulative
        statistics are shifted so the current row is excluded. Validation and test rows
        may use attributes from earlier observed transactions, exactly as an online
        transaction stream would, but never their labels.
        '''),
        code(r'''
        import joblib
        from src.fraud_pipeline.behavioral import (
            BehavioralFeatureContract,
            add_causal_behavioral_features,
            build_behavioral_reference,
        )
        from src.fraud_pipeline.common import build_feature_audit, chronological_split
        from src.fraud_pipeline.artifacts import write_json

        raw_input_schema = {
            "required_columns": [c for c in raw_columns if c != "isFraud"],
            "target": "isFraud",
            "join": {"type": "left", "key": "TransactionID"},
        }
        ordered_features = add_causal_behavioral_features(joined, copy=True)
        if len(ordered_features) != len(joined):
            raise AssertionError("Feature engineering changed the row count")
        if ordered_features["TransactionID"].duplicated().any():
            raise AssertionError("Feature engineering duplicated a transaction")

        # Keep the interactive leakage audit small enough for a 16 GB laptop.
        # The repository unit test checks the same invariants independently.
        leakage_sample = joined.nsmallest(
            min(20_000, len(joined)), ["TransactionDT", "TransactionID"]
        ).copy()
        deployment_reference = build_behavioral_reference(joined)
        del joined
        gc.collect()

        train, validation, test, split_metadata = chronological_split(ordered_features)
        print({name: part.shape for name, part in {
            "train": train, "validation": validation, "test": test}.items()})
        '''),
        md(r'''
        ## 4. Save Version 2 partitions and deployment reference

        The reference contains no fraud labels. It summarizes all labelled history only
        for transactions that arrive after this dataset. The held-out metrics below never
        use this reference; they use the past-only features already generated row by row.
        '''),
        code(r'''
        V2_DATA_DIR.mkdir(parents=True, exist_ok=True)
        train.to_parquet(V2_DATA_DIR / "train.parquet", index=False)
        validation.to_parquet(V2_DATA_DIR / "validation.parquet", index=False)
        test.to_parquet(V2_DATA_DIR / "test.parquet", index=False)
        build_feature_audit(train).to_csv(V2_DATA_DIR / "feature_audit.csv", index=False)
        write_json(V2_DATA_DIR / "split_metadata.json", split_metadata)
        write_json(V2_DATA_DIR / "raw_input_schema.json", raw_input_schema)
        write_json(V2_DATA_DIR / "behavioral_contract.json", BehavioralFeatureContract().to_dict())

        joblib.dump(deployment_reference, V2_DATA_DIR / "behavioral_reference.joblib", compress=3)
        write_json(V2_DATA_DIR / "data_summary.json", {
            "version": "2.0", "joined_rows": len(joined),
            "joined_columns_before_v2": len(joined.columns),
            "columns_after_v2": len(ordered_features.columns),
            "new_columns": [c for c in ordered_features.columns if c not in joined.columns],
        })
        print("Saved Version 2 data to:", V2_DATA_DIR)
        '''),
        md(r'''
        ## 5. Leakage assertions

        These checks make the interview claim testable: the first occurrence of a proxy
        has zero prior count, and changing the target cannot change engineered features.
        '''),
        code(r'''
        sample_features = add_causal_behavioral_features(leakage_sample, copy=True)
        feature_columns = [c for c in sample_features if c != "isFraud"]
        changed_target = leakage_sample.copy()
        changed_target["isFraud"] = 1 - changed_target["isFraud"]
        changed_features = add_causal_behavioral_features(changed_target, copy=True)
        pd.testing.assert_frame_equal(
            sample_features[feature_columns], changed_features[feature_columns], check_dtype=False
        )
        first_for_uid = ordered_features.groupby("uid_proxy", observed=True).head(1)
        assert (first_for_uid["uid_proxy_prior_count"] == 0).all()
        assert train["TransactionDT"].max() <= validation["TransactionDT"].min()
        assert validation["TransactionDT"].max() <= test["TransactionDT"].min()
        print("Leakage and ordering checks passed.")
        '''),
        md(r'''
        ## Output

        The next notebooks read these frozen Version 2 partitions. Share this processed
        folder only if teammates cannot run preparation themselves; never commit raw or
        processed competition data to Git.
        '''),
    ]
    write_notebook("10_v2_behavioral_data_preparation.ipynb", cells)


def build_lightgbm() -> None:
    cells = [
        md(r'''
        # 11 — Version 2 LightGBM

        **Owners:** Saravana / Nebal

        This is the first Version 2 experiment because it is the fastest reliable way to
        validate the new behavioural features. It uses three expanding time folds and
        never selects parameters from the final test period.
        '''),
        md(WHY_V2), code(INSTALL), code(SETUP), code(LOAD_V2),
        code("MODEL_KEY = \"lightgbm\"\n" + ARTIFACT_SETUP),
        md(r'''
        ## Candidate configurations

        We deliberately test a small, explainable search rather than hundreds of trials.
        Class weight is included because full inverse-frequency weighting is not always
        best for ranking rare fraud.
        '''),
        code(r'''
        import joblib, lightgbm as lgb
        from sklearn.metrics import average_precision_score
        from src.fraud_pipeline.preprocessing import LightGBMPreprocessor
        from src.fraud_pipeline.validation_v2 import expanding_time_folds, positive_weight

        candidates = [
            {"name": "balanced_64", "num_leaves": 64, "min_child_samples": 50,
             "weight_mode": "balanced", "reg_alpha": 0.1, "reg_lambda": 1.0},
            {"name": "sqrt_96", "num_leaves": 96, "min_child_samples": 100,
             "weight_mode": "sqrt_balanced", "reg_alpha": 0.2, "reg_lambda": 3.0},
            {"name": "unweighted_48", "num_leaves": 48, "min_child_samples": 100,
             "weight_mode": "none", "reg_alpha": 0.2, "reg_lambda": 5.0},
        ]
        if FAST_RUN:
            candidates = candidates[:1]
        '''),
        md("## Rolling time validation"),
        code(r'''
        development = development.sort_values(["TransactionDT", "TransactionID"]).reset_index(drop=True)
        X_dev = development.drop(columns=DROP_FROM_MODEL)
        y_dev = development[TARGET].astype("int8")
        folds = expanding_time_folds(len(development))
        cv_rows = []

        for candidate in candidates:
            for fold_number, (train_index, valid_index) in enumerate(folds, start=1):
                X_fold_train, y_fold_train = X_dev.iloc[train_index], y_dev.iloc[train_index]
                X_fold_valid, y_fold_valid = X_dev.iloc[valid_index], y_dev.iloc[valid_index]
                preprocessor = LightGBMPreprocessor(rare_min_count=20).fit(X_fold_train)
                fold_train = preprocessor.transform(X_fold_train)
                fold_valid = preprocessor.transform(X_fold_valid)
                weight = positive_weight(y_fold_train, candidate["weight_mode"])
                model = lgb.LGBMClassifier(
                    objective="binary", metric="None", n_estimators=10_000,
                    learning_rate=0.03, num_leaves=candidate["num_leaves"], max_depth=-1,
                    min_child_samples=candidate["min_child_samples"], subsample=0.8,
                    subsample_freq=1, colsample_bytree=0.8,
                    reg_alpha=candidate["reg_alpha"], reg_lambda=candidate["reg_lambda"],
                    scale_pos_weight=weight, random_state=RANDOM_SEED, n_jobs=-1,
                )
                started = time.perf_counter()
                model.fit(
                    fold_train, y_fold_train,
                    eval_set=[(fold_valid, y_fold_valid)], eval_metric="average_precision",
                    categorical_feature=preprocessor.categorical_features,
                    callbacks=[lgb.early_stopping(300, first_metric_only=True), lgb.log_evaluation(250)],
                )
                probability = model.predict_proba(fold_valid, num_iteration=model.best_iteration_)[:, 1]
                cv_rows.append({
                    **candidate, "fold": fold_number, "train_rows": len(train_index),
                    "validation_rows": len(valid_index), "best_iteration": model.best_iteration_,
                    "validation_pr_auc": average_precision_score(y_fold_valid, probability),
                    "seconds": time.perf_counter() - started,
                })
                del preprocessor, model, fold_train, fold_valid, probability
                gc.collect()

        cv_results = pd.DataFrame(cv_rows)
        display(cv_results)
        summary = cv_results.groupby("name")["validation_pr_auc"].agg(["mean", "std"]).sort_values("mean", ascending=False)
        display(summary)
        best_name = summary.index[0]
        best_candidate = next(item for item in candidates if item["name"] == best_name)
        print("Selected from rolling validation:", best_candidate)
        '''),
        md(r'''
        ## Final fit and untouched test evaluation

        Final model training still uses the original earliest 70%, next 15% for early
        stopping, and latest 15% once for reporting.
        '''),
        code(r'''
        preprocessor = LightGBMPreprocessor(rare_min_count=20).fit(X_train)
        X_train_model = preprocessor.transform(X_train)
        X_validation_model = preprocessor.transform(X_validation)
        weight = positive_weight(y_train, best_candidate["weight_mode"])
        model = lgb.LGBMClassifier(
            objective="binary", metric="None", n_estimators=12_000, learning_rate=0.03,
            num_leaves=best_candidate["num_leaves"], max_depth=-1,
            min_child_samples=best_candidate["min_child_samples"], subsample=0.8,
            subsample_freq=1, colsample_bytree=0.8,
            reg_alpha=best_candidate["reg_alpha"], reg_lambda=best_candidate["reg_lambda"],
            scale_pos_weight=weight, random_state=RANDOM_SEED, n_jobs=-1,
        )
        started = time.perf_counter()
        model.fit(
            X_train_model, y_train, eval_set=[(X_validation_model, y_validation)],
            eval_metric="average_precision", categorical_feature=preprocessor.categorical_features,
            callbacks=[lgb.early_stopping(300, first_metric_only=True), lgb.log_evaluation(250)],
        )
        training_seconds = time.perf_counter() - started
        validation_probability = model.predict_proba(X_validation_model, num_iteration=model.best_iteration_)[:, 1]
        threshold_record = select_operating_threshold(y_validation, validation_probability, minimum_precision=0.10)
        threshold = float(threshold_record["threshold"])
        validation_metrics = evaluate_binary_classifier(y_validation, validation_probability, threshold)
        del X_train_model
        gc.collect()
        X_test_model = preprocessor.transform(X_test)
        test_probability = model.predict_proba(X_test_model, num_iteration=model.best_iteration_)[:, 1]
        test_metrics = evaluate_binary_classifier(y_test, test_probability, threshold)
        display(pd.DataFrame([validation_metrics, test_metrics], index=["validation", "test"])[
            ["pr_auc", "roc_auc", "precision", "recall", "f1", "brier_score"]])
        '''),
        md("## Save, reload, and package"),
        code(r'''
        importance = pd.DataFrame({
            "feature": model.booster_.feature_name(),
            "gain": model.booster_.feature_importance(importance_type="gain"),
            "split": model.booster_.feature_importance(importance_type="split"),
        }).sort_values("gain", ascending=False)
        importance.head(150).to_csv(RUN_DIR / "feature_importance.csv", index=False)
        cv_results.to_csv(RUN_DIR / "cv_results.csv", index=False)
        model.booster_.save_model(str(RUN_DIR / "model.txt"), num_iteration=model.best_iteration_)
        joblib.dump(preprocessor, RUN_DIR / "preprocessor.joblib", compress=3)
        pd.DataFrame({"TransactionID": validation.TransactionID, "isFraud": y_validation,
                      "probability": validation_probability}).to_parquet(RUN_DIR / "validation_predictions.parquet", index=False)
        pd.DataFrame({"TransactionID": test.TransactionID, "isFraud": y_test,
                      "probability": test_probability}).to_parquet(RUN_DIR / "test_predictions.parquet", index=False)
        write_json(RUN_DIR / "threshold.json", threshold_record)
        write_json(RUN_DIR / "metrics.json", {"validation": validation_metrics, "test": test_metrics})
        write_json(RUN_DIR / "feature_schema.json", {"groups": preprocessor.groups,
                   "categorical_features": preprocessor.categorical_features,
                   "behavioral_contract": "data/processed/v2/behavioral_contract.json"})
        write_json(RUN_DIR / "training_config.json", {
            "model": "v2_lightgbm", "run_id": RUN_ID, "fast_run": FAST_RUN,
            "random_seed": RANDOM_SEED, "training_seconds": training_seconds,
            "best_iteration": model.best_iteration_, "selected_candidate": best_candidate,
            "scale_pos_weight": weight, "parameters": model.get_params(),
            "versions": package_versions(["numpy", "pandas", "scikit-learn", "lightgbm", "joblib"]),
        })
        loaded_preprocessor = joblib.load(RUN_DIR / "preprocessor.joblib")
        loaded_model = lgb.Booster(model_file=str(RUN_DIR / "model.txt"))
        sample = loaded_preprocessor.transform(X_validation.iloc[:5])
        np.testing.assert_allclose(
            validation_probability[:5], loaded_model.predict(sample), rtol=1e-6, atol=1e-8)
        '''),
        code(PACKAGE_RUN),
    ]
    write_notebook("11_v2_lightgbm_saravana_nebal.ipynb", cells)


def build_catboost() -> None:
    cells = [
        md(r'''
        # 12 — Version 2 CatBoost

        **Owners:** Midhun / Ajmeer

        Version 1 stopped on ROC-AUC although our primary rare-fraud metric is PR-AUC.
        Version 2 selects tree count using unweighted binary PR-AUC and compares three
        explainable class-weight/depth configurations over expanding time folds.
        '''),
        md(WHY_V2), code(INSTALL), code(SETUP), code(LOAD_V2),
        code("MODEL_KEY = \"catboost\"\n" + ARTIFACT_SETUP),
        code(r'''
        import joblib, torch
        from catboost import CatBoostClassifier, Pool
        from sklearn.metrics import average_precision_score
        from src.fraud_pipeline.preprocessing import CatBoostPreprocessor
        from src.fraud_pipeline.validation_v2 import expanding_time_folds, positive_weight

        USE_GPU = torch.cuda.is_available()
        candidates = [
            {"name": "balanced_d8", "depth": 8, "weight_mode": "balanced", "l2_leaf_reg": 5.0},
            {"name": "sqrt_d8", "depth": 8, "weight_mode": "sqrt_balanced", "l2_leaf_reg": 7.0},
            {"name": "sqrt_d10", "depth": 10, "weight_mode": "sqrt_balanced", "l2_leaf_reg": 10.0},
        ]
        if FAST_RUN:
            candidates = candidates[:1]
        '''),
        md("## Rolling time validation"),
        code(r'''
        development = development.sort_values(["TransactionDT", "TransactionID"]).reset_index(drop=True)
        X_dev = development.drop(columns=DROP_FROM_MODEL)
        y_dev = development[TARGET].astype("int8")
        folds = expanding_time_folds(len(development))
        cv_rows = []

        for candidate in candidates:
            for fold_number, (train_index, valid_index) in enumerate(folds, start=1):
                X_fold_train, y_fold_train = X_dev.iloc[train_index], y_dev.iloc[train_index]
                X_fold_valid, y_fold_valid = X_dev.iloc[valid_index], y_dev.iloc[valid_index]
                preprocessor = CatBoostPreprocessor().fit(X_fold_train)
                fold_train = preprocessor.transform(X_fold_train)
                fold_valid = preprocessor.transform(X_fold_valid)
                weight = positive_weight(y_fold_train, candidate["weight_mode"])
                train_pool = Pool(fold_train, y_fold_train, cat_features=preprocessor.categorical_features)
                valid_pool = Pool(fold_valid, y_fold_valid, cat_features=preprocessor.categorical_features)
                params = dict(
                    iterations=5_000, learning_rate=0.04, depth=candidate["depth"],
                    loss_function="Logloss", eval_metric="PRAUC:type=Classic;use_weights=False",
                    class_weights=[1.0, weight], l2_leaf_reg=candidate["l2_leaf_reg"],
                    random_seed=RANDOM_SEED, task_type="GPU" if USE_GPU else "CPU",
                    allow_writing_files=False, verbose=250,
                )
                if USE_GPU:
                    params["devices"] = "0"
                model = CatBoostClassifier(**params)
                started = time.perf_counter()
                model.fit(train_pool, eval_set=valid_pool, early_stopping_rounds=300, use_best_model=True)
                probability = model.predict_proba(valid_pool)[:, 1]
                cv_rows.append({
                    **candidate, "fold": fold_number, "train_rows": len(train_index),
                    "validation_rows": len(valid_index), "best_iteration": model.get_best_iteration(),
                    "validation_pr_auc": average_precision_score(y_fold_valid, probability),
                    "seconds": time.perf_counter() - started,
                })
                del preprocessor, model, fold_train, fold_valid, train_pool, valid_pool, probability
                gc.collect()

        cv_results = pd.DataFrame(cv_rows)
        display(cv_results)
        summary = cv_results.groupby("name")["validation_pr_auc"].agg(["mean", "std"]).sort_values("mean", ascending=False)
        display(summary)
        best_name = summary.index[0]
        best_candidate = next(item for item in candidates if item["name"] == best_name)
        print("Selected from rolling validation:", best_candidate)
        '''),
        md("## Final fit and untouched test evaluation"),
        code(r'''
        preprocessor = CatBoostPreprocessor().fit(X_train)
        X_train_model = preprocessor.transform(X_train)
        X_validation_model = preprocessor.transform(X_validation)
        weight = positive_weight(y_train, best_candidate["weight_mode"])
        train_pool = Pool(X_train_model, y_train, cat_features=preprocessor.categorical_features)
        validation_pool = Pool(X_validation_model, y_validation, cat_features=preprocessor.categorical_features)
        params = dict(
            iterations=6_000, learning_rate=0.04, depth=best_candidate["depth"],
            loss_function="Logloss", eval_metric="PRAUC:type=Classic;use_weights=False",
            class_weights=[1.0, weight], l2_leaf_reg=best_candidate["l2_leaf_reg"],
            random_seed=RANDOM_SEED, task_type="GPU" if USE_GPU else "CPU",
            allow_writing_files=False, verbose=250,
        )
        if USE_GPU:
            params["devices"] = "0"
        model = CatBoostClassifier(**params)
        started = time.perf_counter()
        model.fit(train_pool, eval_set=validation_pool, early_stopping_rounds=300, use_best_model=True)
        training_seconds = time.perf_counter() - started
        validation_probability = model.predict_proba(validation_pool)[:, 1]
        threshold_record = select_operating_threshold(y_validation, validation_probability, minimum_precision=0.10)
        threshold = float(threshold_record["threshold"])
        validation_metrics = evaluate_binary_classifier(y_validation, validation_probability, threshold)
        del train_pool, X_train_model
        gc.collect()
        X_test_model = preprocessor.transform(X_test)
        test_pool = Pool(X_test_model, y_test, cat_features=preprocessor.categorical_features)
        test_probability = model.predict_proba(test_pool)[:, 1]
        test_metrics = evaluate_binary_classifier(y_test, test_probability, threshold)
        display(pd.DataFrame([validation_metrics, test_metrics], index=["validation", "test"])[
            ["pr_auc", "roc_auc", "precision", "recall", "f1", "brier_score"]])
        '''),
        md("## Save, reload, and package"),
        code(r'''
        importance = pd.DataFrame({"feature": preprocessor.feature_columns,
            "importance": model.get_feature_importance(validation_pool)}).sort_values("importance", ascending=False)
        importance.head(150).to_csv(RUN_DIR / "feature_importance.csv", index=False)
        cv_results.to_csv(RUN_DIR / "cv_results.csv", index=False)
        model.save_model(str(RUN_DIR / "model.cbm"), format="cbm")
        joblib.dump(preprocessor, RUN_DIR / "preprocessor.joblib", compress=3)
        pd.DataFrame({"TransactionID": validation.TransactionID, "isFraud": y_validation,
                      "probability": validation_probability}).to_parquet(RUN_DIR / "validation_predictions.parquet", index=False)
        pd.DataFrame({"TransactionID": test.TransactionID, "isFraud": y_test,
                      "probability": test_probability}).to_parquet(RUN_DIR / "test_predictions.parquet", index=False)
        write_json(RUN_DIR / "threshold.json", threshold_record)
        write_json(RUN_DIR / "metrics.json", {"validation": validation_metrics, "test": test_metrics})
        write_json(RUN_DIR / "feature_schema.json", {"feature_columns": preprocessor.feature_columns,
                   "categorical_features": preprocessor.categorical_features,
                   "behavioral_contract": "data/processed/v2/behavioral_contract.json"})
        write_json(RUN_DIR / "training_config.json", {
            "model": "v2_catboost", "run_id": RUN_ID, "fast_run": FAST_RUN,
            "random_seed": RANDOM_SEED, "training_seconds": training_seconds,
            "best_iteration": model.get_best_iteration(), "selected_candidate": best_candidate,
            "class_weight": weight, "use_gpu": USE_GPU, "parameters": model.get_params(),
            "versions": package_versions(["numpy", "pandas", "catboost", "joblib"]),
        })
        loaded_preprocessor = joblib.load(RUN_DIR / "preprocessor.joblib")
        loaded_model = CatBoostClassifier()
        loaded_model.load_model(str(RUN_DIR / "model.cbm"))
        sample = loaded_preprocessor.transform(X_validation.iloc[:5])
        sample_pool = Pool(sample, cat_features=loaded_preprocessor.categorical_features)
        np.testing.assert_allclose(validation_probability[:5], loaded_model.predict_proba(sample_pool)[:, 1], rtol=1e-6, atol=1e-8)
        '''),
        code(PACKAGE_RUN),
    ]
    write_notebook("12_v2_catboost_midhun_ajmeer.ipynb", cells)


def build_logistic() -> None:
    cells = [
        md(r'''
        # 13 — Version 2 Logistic Regression

        **Owners:** Nanda / Khishan

        This remains the transparent linear baseline. It receives the finalized Version 2
        behavioural features but keeps training-only imputation, scaling, rare grouping,
        frequency encoding and balanced loss.
        '''),
        md(WHY_V2), code(INSTALL), code(SETUP), code(LOAD_V2),
        code("MODEL_KEY = \"logistic_regression\"\n" + ARTIFACT_SETUP),
        md(r'''
        ## Fit the sparse pipeline

        Logistic regression cannot learn complex interactions as naturally as boosted
        trees, so its purpose is interpretability and a defensible baseline—not winning
        the leaderboard.
        '''),
        code(r'''
        import joblib
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from src.fraud_pipeline.preprocessing import build_logistic_preprocessor, infer_feature_groups

        groups = infer_feature_groups(X_train, low_cardinality_max=100)
        preprocessor = build_logistic_preprocessor(groups, rare_min_count=20)
        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", LogisticRegression(
                C=0.1, penalty="l2", solver="saga", class_weight="balanced",
                max_iter=800, tol=0.001, n_jobs=-1, random_state=RANDOM_SEED, verbose=1,
            )),
        ])
        started = time.perf_counter()
        pipeline.fit(X_train, y_train)
        training_seconds = time.perf_counter() - started
        classifier = pipeline.named_steps["classifier"]
        if int(classifier.n_iter_[0]) >= classifier.max_iter:
            raise RuntimeError("Logistic Regression reached max_iter; increase it before accepting this run")
        print("Converged at iteration:", int(classifier.n_iter_[0]))
        '''),
        md("## Validation, threshold, and final test"),
        code(r'''
        validation_probability = pipeline.predict_proba(X_validation)[:, 1]
        threshold_record = select_operating_threshold(y_validation, validation_probability, minimum_precision=0.10)
        threshold = float(threshold_record["threshold"])
        validation_metrics = evaluate_binary_classifier(y_validation, validation_probability, threshold)
        started = time.perf_counter()
        test_probability = pipeline.predict_proba(X_test)[:, 1]
        prediction_seconds = time.perf_counter() - started
        test_metrics = evaluate_binary_classifier(y_test, test_probability, threshold)
        display(pd.DataFrame([validation_metrics, test_metrics], index=["validation", "test"])[
            ["pr_auc", "roc_auc", "precision", "recall", "f1", "brier_score"]])
        '''),
        md("## Save, reload, and package"),
        code(r'''
        feature_names = pipeline.named_steps["preprocessor"].get_feature_names_out()
        coefficients = pipeline.named_steps["classifier"].coef_[0]
        importance = pd.DataFrame({"feature": feature_names, "coefficient": coefficients})
        importance["absolute_coefficient"] = importance.coefficient.abs()
        importance.sort_values("absolute_coefficient", ascending=False).head(150).to_csv(
            RUN_DIR / "top_coefficients.csv", index=False)
        joblib.dump(pipeline, RUN_DIR / "model.joblib", compress=3)
        pd.DataFrame({"TransactionID": validation.TransactionID, "isFraud": y_validation,
                      "probability": validation_probability}).to_parquet(RUN_DIR / "validation_predictions.parquet", index=False)
        pd.DataFrame({"TransactionID": test.TransactionID, "isFraud": y_test,
                      "probability": test_probability}).to_parquet(RUN_DIR / "test_predictions.parquet", index=False)
        write_json(RUN_DIR / "threshold.json", threshold_record)
        write_json(RUN_DIR / "metrics.json", {"validation": validation_metrics, "test": test_metrics})
        write_json(RUN_DIR / "feature_schema.json", {"groups": groups,
                   "behavioral_contract": "data/processed/v2/behavioral_contract.json"})
        write_json(RUN_DIR / "training_config.json", {
            "model": "v2_logistic_regression", "run_id": RUN_ID, "fast_run": FAST_RUN,
            "random_seed": RANDOM_SEED, "training_seconds": training_seconds,
            "test_prediction_seconds": prediction_seconds,
            "converged_iteration": int(classifier.n_iter_[0]),
            "parameters": classifier.get_params(),
            "versions": package_versions(["numpy", "pandas", "scikit-learn", "joblib"]),
        })
        loaded = joblib.load(RUN_DIR / "model.joblib")
        np.testing.assert_allclose(validation_probability[:5], loaded.predict_proba(X_validation.iloc[:5])[:, 1], rtol=1e-6, atol=1e-8)
        '''),
        code(PACKAGE_RUN),
    ]
    write_notebook("13_v2_logistic_regression_nanda_khishan.ipynb", cells)


def build_neural() -> None:
    cells = [
        md(r'''
        # 14 — Version 2 tabular neural network

        **Owners:** Mirdula / Hashvitha

        Version 1 was still improving at its final allowed epoch. Version 2 makes the
        recorded architecture genuinely configurable, permits up to 50 epochs, uses a
        learning-rate scheduler, and compares full versus square-root class weighting.
        '''),
        md(WHY_V2), code(INSTALL), code(SETUP), code(LOAD_V2),
        code("MODEL_KEY = \"neural_network\"\n" + ARTIFACT_SETUP),
        code(r'''
        import copy, joblib, torch
        from sklearn.metrics import average_precision_score
        from torch import nn
        from torch.utils.data import DataLoader, TensorDataset
        from src.fraud_pipeline.neural_v2 import (
            FraudTabularNetworkV2, embedding_dimension_v2, network_v2_from_config,
        )
        from src.fraud_pipeline.preprocessing import NeuralTabularPreprocessor
        from src.fraud_pipeline.validation_v2 import positive_weight

        torch.manual_seed(RANDOM_SEED)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(RANDOM_SEED)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        preprocessor = NeuralTabularPreprocessor(rare_min_count=20).fit(X_train)
        train_numeric, train_categorical = preprocessor.transform(X_train)
        validation_numeric, validation_categorical = preprocessor.transform(X_validation)
        embedding_dimensions = [embedding_dimension_v2(value) for value in preprocessor.cardinalities]
        model_config = {
            "numeric_size": preprocessor.numeric_output_size,
            "cardinalities": preprocessor.cardinalities,
            "embedding_dimensions": embedding_dimensions,
            "categorical_columns": preprocessor.categorical_columns,
            "hidden_layers": [384, 192, 96], "dropout": [0.30, 0.20, 0.10],
        }
        print("Device:", device)
        print("Numeric inputs:", model_config["numeric_size"])
        print("Categorical inputs:", len(model_config["cardinalities"]))
        '''),
        md("## Data loaders and reusable training function"),
        code(r'''
        BATCH_SIZE = 4096
        MAX_EPOCHS = 50
        PATIENCE = 7
        train_dataset = TensorDataset(
            torch.from_numpy(train_numeric), torch.from_numpy(train_categorical),
            torch.from_numpy(y_train.to_numpy(dtype=np.float32)))
        validation_dataset = TensorDataset(
            torch.from_numpy(validation_numeric), torch.from_numpy(validation_categorical),
            torch.from_numpy(y_validation.to_numpy(dtype=np.float32)))
        train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True,
            num_workers=2, pin_memory=device.type == "cuda")
        validation_loader = DataLoader(validation_dataset, batch_size=BATCH_SIZE * 2,
            shuffle=False, num_workers=2, pin_memory=device.type == "cuda")

        def predict_loader(model, loader):
            model.eval(); probabilities, labels = [], []
            with torch.inference_mode():
                for numeric, categorical, target in loader:
                    logits = model(numeric.to(device), categorical.to(device))
                    probabilities.append(torch.sigmoid(logits).cpu().numpy())
                    labels.append(target.numpy())
            return np.concatenate(probabilities), np.concatenate(labels)

        def train_candidate(weight_mode):
            torch.manual_seed(RANDOM_SEED)
            model = network_v2_from_config(model_config).to(device)
            weight = positive_weight(y_train, weight_mode)
            loss_function = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(weight, device=device))
            optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=2e-4)
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
                optimizer, mode="max", factor=0.5, patience=2, min_lr=1e-5)
            scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
            best_score, best_state, without_improvement, history = -np.inf, None, 0, []
            for epoch in range(1, MAX_EPOCHS + 1):
                model.train(); total_loss = 0.0
                for numeric, categorical, target in train_loader:
                    numeric = numeric.to(device, non_blocking=True)
                    categorical = categorical.to(device, non_blocking=True)
                    target = target.to(device, non_blocking=True)
                    optimizer.zero_grad(set_to_none=True)
                    with torch.autocast(device_type=device.type, dtype=torch.float16,
                                        enabled=device.type == "cuda"):
                        loss = loss_function(model(numeric, categorical), target)
                    scaler.scale(loss).backward(); scaler.step(optimizer); scaler.update()
                    total_loss += loss.item() * len(target)
                probability, label = predict_loader(model, validation_loader)
                score = average_precision_score(label, probability)
                scheduler.step(score)
                row = {"weight_mode": weight_mode, "epoch": epoch,
                       "train_loss": total_loss / len(train_dataset),
                       "validation_pr_auc": score,
                       "learning_rate": optimizer.param_groups[0]["lr"]}
                history.append(row); print(row)
                if score > best_score + 1e-5:
                    best_score = score
                    best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
                    without_improvement = 0
                else:
                    without_improvement += 1
                    if without_improvement >= PATIENCE:
                        break
            model.load_state_dict(best_state)
            return model, best_score, weight, history
        '''),
        md("## Compare class-weight strength on validation only"),
        code(r'''
        candidate_modes = ["sqrt_balanced", "balanced"] if not FAST_RUN else ["sqrt_balanced"]
        candidate_results = []
        started = time.perf_counter()
        for mode in candidate_modes:
            candidate_model, score, weight, history = train_candidate(mode)
            candidate_results.append({"mode": mode, "score": score, "weight": weight,
                                      "state": copy.deepcopy(candidate_model.state_dict()),
                                      "history": history})
            del candidate_model
            if torch.cuda.is_available(): torch.cuda.empty_cache()
        best = max(candidate_results, key=lambda item: item["score"])
        model = network_v2_from_config(model_config).to(device)
        model.load_state_dict(best["state"])
        training_seconds = time.perf_counter() - started
        history = pd.DataFrame([row for item in candidate_results for row in item["history"]])
        display(history.groupby("weight_mode")["validation_pr_auc"].max())
        print("Selected:", best["mode"], "PR-AUC:", best["score"])
        '''),
        md("## Final validation and untouched test"),
        code(r'''
        validation_probability, _ = predict_loader(model, validation_loader)
        threshold_record = select_operating_threshold(y_validation, validation_probability, minimum_precision=0.10)
        threshold = float(threshold_record["threshold"])
        validation_metrics = evaluate_binary_classifier(y_validation, validation_probability, threshold)
        test_numeric, test_categorical = preprocessor.transform(X_test)
        test_dataset = TensorDataset(torch.from_numpy(test_numeric), torch.from_numpy(test_categorical),
                                     torch.from_numpy(y_test.to_numpy(dtype=np.float32)))
        test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE * 2, shuffle=False,
                                 num_workers=2, pin_memory=device.type == "cuda")
        test_probability, _ = predict_loader(model, test_loader)
        test_metrics = evaluate_binary_classifier(y_test, test_probability, threshold)
        display(pd.DataFrame([validation_metrics, test_metrics], index=["validation", "test"])[
            ["pr_auc", "roc_auc", "precision", "recall", "f1", "brier_score"]])
        '''),
        md("## Save, reload, and package"),
        code(r'''
        torch.save({"model_state_dict": {k: v.cpu() for k, v in model.state_dict().items()},
                    "model_config": model_config, "best_validation_pr_auc": best["score"]}, RUN_DIR / "model.pt")
        joblib.dump(preprocessor, RUN_DIR / "numeric_and_categorical_preprocessor.joblib", compress=3)
        history.to_csv(RUN_DIR / "training_history.csv", index=False)
        write_json(RUN_DIR / "model_config.json", model_config)
        pd.DataFrame({"TransactionID": validation.TransactionID, "isFraud": y_validation,
                      "probability": validation_probability}).to_parquet(RUN_DIR / "validation_predictions.parquet", index=False)
        pd.DataFrame({"TransactionID": test.TransactionID, "isFraud": y_test,
                      "probability": test_probability}).to_parquet(RUN_DIR / "test_predictions.parquet", index=False)
        write_json(RUN_DIR / "threshold.json", threshold_record)
        write_json(RUN_DIR / "metrics.json", {"validation": validation_metrics, "test": test_metrics})
        write_json(RUN_DIR / "feature_schema.json", {"groups": preprocessor.groups,
                   "categorical_columns": preprocessor.categorical_columns,
                   "behavioral_contract": "data/processed/v2/behavioral_contract.json"})
        write_json(RUN_DIR / "training_config.json", {
            "model": "v2_neural_network", "run_id": RUN_ID, "fast_run": FAST_RUN,
            "random_seed": RANDOM_SEED, "training_seconds": training_seconds,
            "device": str(device), "selected_weight_mode": best["mode"],
            "positive_weight": best["weight"], "max_epochs": MAX_EPOCHS, "patience": PATIENCE,
            "versions": package_versions(["numpy", "pandas", "scikit-learn", "torch", "joblib"]),
        })
        loaded_preprocessor = joblib.load(RUN_DIR / "numeric_and_categorical_preprocessor.joblib")
        checkpoint = torch.load(RUN_DIR / "model.pt", map_location=device, weights_only=True)
        loaded_model = network_v2_from_config(checkpoint["model_config"]).to(device)
        loaded_model.load_state_dict(checkpoint["model_state_dict"])
        sample_numeric, sample_categorical = loaded_preprocessor.transform(X_validation.iloc[:5])
        loaded_model.eval()
        with torch.inference_mode():
            reloaded = torch.sigmoid(loaded_model(torch.from_numpy(sample_numeric).to(device),
                torch.from_numpy(sample_categorical).to(device))).cpu().numpy()
        np.testing.assert_allclose(validation_probability[:5], reloaded, rtol=1e-5, atol=1e-7)
        '''),
        code(PACKAGE_RUN),
    ]
    write_notebook("14_v2_tabular_neural_network_mirdula_hashvitha.ipynb", cells)


def build_consensus() -> None:
    cells = [
        md(r'''
        # 15 — Version 2 LightGBM + CatBoost consensus

        **Owners:** Midhun / Saravana / Nebal / Ajmeer

        Run only after notebooks 11 and 12 have complete full-data runs. This notebook
        chooses each model by validation PR-AUC, learns one LightGBM/CatBoost log-odds
        weight on validation, freezes it, and evaluates the test period once.

        The four original outputs remain visible. Consensus is an additional fifth score.
        '''),
        code(INSTALL), code(SETUP),
        code("MODEL_KEY = \"consensus\"\n" + ARTIFACT_SETUP),
        code(r'''
        from sklearn.metrics import average_precision_score
        from src.fraud_pipeline.validation_v2 import (
            apply_two_model_logit_blend, best_complete_run,
            fit_two_model_logit_blend, merge_prediction_files,
        )

        source_runs = {
            "lightgbm": best_complete_run(V2_ARTIFACT_ROOT, "lightgbm"),
            "catboost": best_complete_run(V2_ARTIFACT_ROOT, "catboost"),
        }
        print({name: path.name for name, path in source_runs.items()})
        validation_predictions = merge_prediction_files(source_runs, "validation")
        test_predictions = merge_prediction_files(source_runs, "test")
        blend = fit_two_model_logit_blend(
            validation_predictions.isFraud.to_numpy(),
            validation_predictions.lightgbm.to_numpy(),
            validation_predictions.catboost.to_numpy(),
        )
        print("Validation-selected blend:", blend)
        '''),
        md("## Freeze the blend and evaluate"),
        code(r'''
        validation_probability = apply_two_model_logit_blend(
            validation_predictions.lightgbm, validation_predictions.catboost,
            blend["first_weight"])
        threshold_record = select_operating_threshold(
            validation_predictions.isFraud.to_numpy(), validation_probability,
            minimum_precision=0.10)
        threshold = float(threshold_record["threshold"])
        validation_metrics = evaluate_binary_classifier(
            validation_predictions.isFraud.to_numpy(), validation_probability, threshold)
        test_probability = apply_two_model_logit_blend(
            test_predictions.lightgbm, test_predictions.catboost, blend["first_weight"])
        test_metrics = evaluate_binary_classifier(
            test_predictions.isFraud.to_numpy(), test_probability, threshold)
        display(pd.DataFrame([validation_metrics, test_metrics], index=["validation", "test"])[
            ["pr_auc", "roc_auc", "precision", "recall", "f1", "brier_score"]])
        '''),
        md("## Save the deployable ensemble recipe"),
        code(r'''
        pd.DataFrame({"TransactionID": validation_predictions.TransactionID,
            "isFraud": validation_predictions.isFraud,
            "probability": validation_probability}).to_parquet(
                RUN_DIR / "validation_predictions.parquet", index=False)
        pd.DataFrame({"TransactionID": test_predictions.TransactionID,
            "isFraud": test_predictions.isFraud,
            "probability": test_probability}).to_parquet(
                RUN_DIR / "test_predictions.parquet", index=False)
        write_json(RUN_DIR / "threshold.json", threshold_record)
        write_json(RUN_DIR / "metrics.json", {"validation": validation_metrics, "test": test_metrics})
        write_json(RUN_DIR / "consensus_config.json", {
            "method": "weighted_log_odds", "first_model": "lightgbm",
            "second_model": "catboost", "first_weight": blend["first_weight"],
            "second_weight": blend["second_weight"],
            "source_runs": {name: path.name for name, path in source_runs.items()},
        })
        write_json(RUN_DIR / "training_config.json", {
            "model": "v2_consensus", "run_id": RUN_ID, "fast_run": False,
            "selection_data": "validation_only", "test_used_for_weight_selection": False,
            "versions": package_versions(["numpy", "pandas", "scikit-learn"]),
        })
        '''),
        code(PACKAGE_RUN),
    ]
    write_notebook("15_v2_lightgbm_catboost_consensus.ipynb", cells)


def main() -> None:
    build_preparation()
    build_lightgbm()
    build_catboost()
    build_logistic()
    build_neural()
    build_consensus()
    print(f"Wrote six Version 2 notebooks to {OUTPUT}")


if __name__ == "__main__":
    main()
