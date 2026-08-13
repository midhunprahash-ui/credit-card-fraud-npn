import numpy as np
import pandas as pd

from src.fraud_pipeline.common import add_shared_features, chronological_split
from src.fraud_pipeline.evaluation import (
    evaluate_binary_classifier,
    select_operating_threshold,
)
from src.fraud_pipeline.preprocessing import (
    CatBoostPreprocessor,
    LightGBMPreprocessor,
    NeuralTabularPreprocessor,
    build_logistic_preprocessor,
    infer_feature_groups,
)


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "TransactionID": [3, 1, 2, 4, 5, 6, 7, 8, 9, 10],
            "TransactionDT": [30, 10, 20, 40, 50, 60, 70, 80, 90, 100],
            "TransactionAmt": [10.0, 20.5, np.nan, 8.0, 11.0, 9.0, 50.0, 7.0, 6.0, 5.0],
            "ProductCD": ["W", "W", "C", None, "W", "C", "W", "W", "C", "W"],
            "card1": [1, 1, 2, 3, 1, 2, 4, 5, 6, 7],
            "card2": [10, 10, 20, 30, 10, 20, 40, 50, 60, np.nan],
            "addr1": [100] * 10,
            "addr2": [1] * 10,
            "P_emaildomain": ["a.com"] * 9 + ["b.com"],
            "R_emaildomain": [None] * 10,
            "DeviceType": [None] * 10,
            "isFraud": [0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
        }
    )


def test_shared_features_and_time_split() -> None:
    frame = add_shared_features(sample_frame(), copy=True)
    assert "num_missing" in frame
    assert "transaction_relative_hour_phase" in frame
    assert "card_1_2" in frame
    train, validation, test, metadata = chronological_split(frame)
    assert len(train) == 7
    assert len(validation) == 1
    assert len(test) == 2
    assert train.TransactionDT.max() < validation.TransactionDT.min()
    assert metadata["method"] == "chronological"


def test_model_specific_preprocessors() -> None:
    frame = add_shared_features(sample_frame(), copy=True)
    groups = infer_feature_groups(frame)
    assert "TransactionAmt" in groups["numeric"]
    assert "card1" in groups["low_cardinality"]

    logistic = build_logistic_preprocessor(groups, rare_min_count=2)
    logistic_output = logistic.fit_transform(frame)
    assert logistic_output.shape[0] == len(frame)

    lightgbm = LightGBMPreprocessor(rare_min_count=2).fit(frame)
    lgbm_output = lightgbm.transform(frame)
    assert len(lgbm_output) == len(frame)

    catboost = CatBoostPreprocessor().fit(frame)
    cat_output = catboost.transform(frame)
    assert cat_output["ProductCD"].isna().sum() == 0

    neural = NeuralTabularPreprocessor(rare_min_count=2).fit(frame)
    numeric, categorical = neural.transform(frame)
    assert numeric.shape[0] == len(frame)
    assert categorical.shape[1] == len(neural.categorical_columns)


def test_rare_and_unknown_categories_are_distinct() -> None:
    frame = add_shared_features(sample_frame(), copy=True)
    future = frame.iloc[:2].copy()
    future["ProductCD"] = ["C", "NEVER_SEEN"]

    lightgbm = LightGBMPreprocessor(rare_min_count=4).fit(frame)
    transformed = lightgbm.transform(future)
    assert str(transformed["ProductCD"].iloc[0]) == "OTHER"
    assert str(transformed["ProductCD"].iloc[1]) == "UNKNOWN"

    neural = NeuralTabularPreprocessor(rare_min_count=4).fit(frame)
    _, categorical = neural.transform(future)
    product_index = neural.categorical_columns.index("ProductCD")
    assert categorical[0, product_index] == 2  # OTHER
    assert categorical[1, product_index] == 1  # UNKNOWN


def test_common_evaluation_contract() -> None:
    y = np.array([0, 0, 0, 1, 1])
    p = np.array([0.05, 0.10, 0.20, 0.70, 0.90])
    threshold = select_operating_threshold(y, p, minimum_precision=0.5)
    metrics = evaluate_binary_classifier(y, p, float(threshold["threshold"]))
    assert metrics["pr_auc"] > 0.9
    assert "top_5_percent" in metrics
