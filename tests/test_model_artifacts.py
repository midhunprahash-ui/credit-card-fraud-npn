from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import torch
from catboost import CatBoostClassifier, Pool
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from src.fraud_pipeline.neural import FraudTabularNetwork, network_from_config
from src.fraud_pipeline.preprocessing import (
    CatBoostPreprocessor,
    LightGBMPreprocessor,
    NeuralTabularPreprocessor,
    build_logistic_preprocessor,
    infer_feature_groups,
)


def model_frame(rows: int = 80) -> tuple[pd.DataFrame, np.ndarray]:
    rng = np.random.default_rng(42)
    frame = pd.DataFrame(
        {
            "TransactionAmt": rng.lognormal(4, 1, rows).astype("float32"),
            "V257": rng.normal(size=rows).astype("float32"),
            "ProductCD": np.where(np.arange(rows) % 3 == 0, "C", "W"),
            "card1": np.arange(rows) % 11,
            "DeviceInfo": np.where(np.arange(rows) % 5 == 0, "mobile", "desktop"),
        }
    )
    frame.loc[::9, "TransactionAmt"] = np.nan
    frame.loc[::7, "card1"] = np.nan
    target = ((frame["ProductCD"] == "C") & (frame["V257"] > 0)).astype("int8").to_numpy()
    return frame, target


def test_logistic_pipeline_round_trip(tmp_path: Path) -> None:
    frame, target = model_frame()
    groups = infer_feature_groups(frame)
    model = Pipeline(
        [
            ("preprocessor", build_logistic_preprocessor(groups, rare_min_count=2)),
            ("classifier", LogisticRegression(max_iter=100, class_weight="balanced")),
        ]
    ).fit(frame, target)
    expected = model.predict_proba(frame.iloc[:5])[:, 1]
    path = tmp_path / "model.joblib"
    joblib.dump(model, path)
    actual = joblib.load(path).predict_proba(frame.iloc[:5])[:, 1]
    np.testing.assert_allclose(expected, actual)


def test_lightgbm_native_round_trip(tmp_path: Path) -> None:
    frame, target = model_frame()
    preprocessor = LightGBMPreprocessor(rare_min_count=2).fit(frame)
    matrix = preprocessor.transform(frame)
    model = lgb.LGBMClassifier(n_estimators=15, verbosity=-1, random_state=42).fit(
        matrix, target, categorical_feature=preprocessor.categorical_features
    )
    expected = model.predict_proba(matrix.iloc[:5])[:, 1]
    model_path = tmp_path / "model.txt"
    preprocessor_path = tmp_path / "preprocessor.joblib"
    model.booster_.save_model(str(model_path))
    joblib.dump(preprocessor, preprocessor_path)
    loaded_matrix = joblib.load(preprocessor_path).transform(frame.iloc[:5])
    actual = lgb.Booster(model_file=str(model_path)).predict(loaded_matrix)
    np.testing.assert_allclose(expected, actual, rtol=1e-6)


def test_catboost_native_round_trip(tmp_path: Path) -> None:
    frame, target = model_frame()
    preprocessor = CatBoostPreprocessor().fit(frame)
    matrix = preprocessor.transform(frame)
    pool = Pool(matrix, target, cat_features=preprocessor.categorical_features)
    model = CatBoostClassifier(
        iterations=15, depth=4, verbose=False, allow_writing_files=False, random_seed=42
    ).fit(pool)
    expected = model.predict_proba(Pool(matrix.iloc[:5], cat_features=preprocessor.categorical_features))[:, 1]
    model_path = tmp_path / "model.cbm"
    model.save_model(str(model_path))
    loaded = CatBoostClassifier()
    loaded.load_model(str(model_path))
    actual = loaded.predict_proba(Pool(matrix.iloc[:5], cat_features=preprocessor.categorical_features))[:, 1]
    np.testing.assert_allclose(expected, actual, rtol=1e-6)


def test_neural_state_dictionary_round_trip(tmp_path: Path) -> None:
    frame, _ = model_frame()
    preprocessor = NeuralTabularPreprocessor(rare_min_count=2).fit(frame)
    numeric, categorical = preprocessor.transform(frame.iloc[:5])
    config = {
        "numeric_size": preprocessor.numeric_output_size,
        "cardinalities": preprocessor.cardinalities,
        "embedding_dimensions": [4] * len(preprocessor.cardinalities),
    }
    model = FraudTabularNetwork(**config).eval()
    with torch.inference_mode():
        expected = model(torch.from_numpy(numeric), torch.from_numpy(categorical))
    path = tmp_path / "model.pt"
    torch.save({"model_state_dict": model.state_dict(), "model_config": config}, path)
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    loaded = network_from_config(checkpoint["model_config"])
    loaded.load_state_dict(checkpoint["model_state_dict"])
    loaded.eval()
    with torch.inference_mode():
        actual = loaded(torch.from_numpy(numeric), torch.from_numpy(categorical))
    torch.testing.assert_close(expected, actual)
