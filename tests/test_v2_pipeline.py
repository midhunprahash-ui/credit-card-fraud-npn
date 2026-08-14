import numpy as np
import pandas as pd

from src.fraud_pipeline.behavioral import (
    add_causal_behavioral_features,
    apply_behavioral_reference,
    build_behavioral_reference,
)
from src.fraud_pipeline.validation_v2 import (
    apply_two_model_logit_blend,
    expanding_time_folds,
    fit_two_model_logit_blend,
    positive_weight,
)


def behavioral_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "TransactionID": [1, 2, 3, 4, 5, 6],
            "TransactionDT": [100, 200, 300, 400, 500, 600],
            "TransactionAmt": [10.0, 20.0, 15.5, 40.0, 25.0, 12.0],
            "card1": [1001, 1001, 2002, 1001, 2002, 3003],
            "card2": [111, 111, 222, 111, 222, 333],
            "addr1": [10, 10, 20, 10, 20, 30],
            "addr2": [1, 1, 1, 1, 1, 1],
            "D1": [0, 0, 1, 0, 1, 2],
            "D4": [np.nan, 0, 1, 0, 1, 2],
            "D10": [0, 0, 1, 0, 1, 2],
            "D15": [0, 0, 1, 0, 1, 2],
            "ProductCD": ["W", "W", "C", "W", "C", "R"],
            "P_emaildomain": ["a.test", "a.test", "b.test", "c.test", "b.test", None],
            "R_emaildomain": [None] * 6,
            "DeviceType": ["desktop", "desktop", "mobile", "desktop", "mobile", None],
            "DeviceInfo": ["Windows 10", "Windows 10", "iOS", "Windows 11", "iOS", None],
            "id_30": ["Windows 10", "Windows 10", "iOS 16", "Windows 11", "iOS 16", None],
            "id_31": ["chrome 120", "chrome 120", "safari 17", "chrome 121", "safari 17", None],
            "isFraud": [0, 1, 0, 0, 1, 0],
        }
    )


def test_behavioral_features_are_past_only_and_target_free() -> None:
    raw = behavioral_frame()
    engineered = add_causal_behavioral_features(raw, copy=True)

    card_rows = engineered.loc[engineered["card1_key"].astype(str) == "1001"]
    assert card_rows["card1_key_prior_count"].tolist() == [0, 1, 2]
    assert card_rows["card1_key_seconds_since_previous"].isna().iloc[0]
    assert card_rows["card1_key_seconds_since_previous"].iloc[1:].tolist() == [100.0, 200.0]

    target_flipped = raw.copy()
    target_flipped["isFraud"] = 1 - target_flipped["isFraud"]
    flipped = add_causal_behavioral_features(target_flipped, copy=True)
    feature_columns = [column for column in engineered if column != "isFraud"]
    pd.testing.assert_frame_equal(
        engineered[feature_columns], flipped[feature_columns], check_dtype=False
    )

    future_changed = raw.copy()
    future_changed.loc[future_changed.index[-1], "TransactionAmt"] = 999_999.0
    changed = add_causal_behavioral_features(future_changed, copy=True)
    pd.testing.assert_frame_equal(
        engineered.iloc[:-1][feature_columns],
        changed.iloc[:-1][feature_columns],
        check_dtype=False,
    )


def test_frozen_behavioral_reference_supports_new_rows() -> None:
    raw = behavioral_frame()
    reference = build_behavioral_reference(raw.iloc[:5])
    new_row = raw.iloc[[5]].copy()
    new_row["card1"] = 1001
    new_row["addr1"] = 10
    transformed = apply_behavioral_reference(new_row, reference, copy=True)

    assert transformed["card1_key_prior_count"].iloc[0] == 3
    assert transformed["card1_key_seconds_since_previous"].iloc[0] == 200.0
    assert "uid_proxy_amount_prior_mean" in transformed
    assert reference["contract"]["uses_target"] is False


def test_time_folds_and_class_weights() -> None:
    folds = expanding_time_folds(850)
    assert len(folds) == 3
    for train_index, validation_index in folds:
        assert train_index[-1] < validation_index[0]
        assert not np.intersect1d(train_index, validation_index).size
    assert folds[-1][1][-1] == 849
    assert positive_weight([0, 0, 0, 1], "balanced") == 3.0
    assert np.isclose(positive_weight([0, 0, 0, 1], "sqrt_balanced"), np.sqrt(3))


def test_logit_blend_is_selected_on_validation() -> None:
    labels = np.array([0, 0, 0, 1, 1, 1])
    first = np.array([0.1, 0.2, 0.4, 0.5, 0.7, 0.9])
    second = np.array([0.2, 0.3, 0.1, 0.8, 0.6, 0.7])
    blend = fit_two_model_logit_blend(labels, first, second, grid_size=11)
    output = apply_two_model_logit_blend(first, second, blend["first_weight"])

    assert np.isclose(blend["first_weight"] + blend["second_weight"], 1.0)
    assert output.shape == labels.shape
    assert ((0 < output) & (output < 1)).all()
