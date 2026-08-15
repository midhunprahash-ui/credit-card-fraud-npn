from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.fraud_pipeline.model_adapters import ModelAdapter
from src.fraud_pipeline.registry import ModelSpec


class FixedScoreAdapter(ModelAdapter):
    def __init__(self, spec: ModelSpec, scores: list[float]) -> None:
        self.scores = np.asarray(scores)
        super().__init__(spec)

    def _predict_scores(self, frame: pd.DataFrame) -> np.ndarray:
        return self.scores


def spec_for(directory: Path) -> ModelSpec:
    (directory / "feature_schema.json").write_text(
        '{"groups":{"numeric":["amount"],"low_cardinality":[],"high_cardinality":[]}}'
    )
    return ModelSpec(
        model_key="logistic_regression",
        version_name="V1",
        run_id="run",
        artifact_directory=directory,
        threshold=0.4,
        champion=False,
        validation_pr_auc=0.5,
        test_pr_auc=0.4,
        files={"model_file": "model.joblib"},
    )


def test_standard_adapter_result_uses_saved_threshold(tmp_path: Path) -> None:
    adapter = FixedScoreAdapter(spec_for(tmp_path), [0.39, 0.4])

    results = adapter.predict(pd.DataFrame({"amount": [10.0, 20.0]}))

    assert [result.decision for result in results] == [False, True]
    assert [result.threshold for result in results] == [0.4, 0.4]
    assert all(result.model_identifier == "logistic_regression.v1" for result in results)
    assert all(result.processing_status == "completed" for result in results)


def test_adapter_rejects_missing_and_protected_features(tmp_path: Path) -> None:
    adapter = FixedScoreAdapter(spec_for(tmp_path), [0.5])
    with pytest.raises(ValueError, match="missing"):
        adapter.predict(pd.DataFrame({"different": [1]}))
    with pytest.raises(ValueError, match="Protected"):
        adapter.predict(pd.DataFrame({"amount": [1], "isFraud": [1]}))
