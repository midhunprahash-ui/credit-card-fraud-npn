import threading
from pathlib import Path

import pytest

from src.fraud_pipeline.model_manager import ModelLoadError, ModelManager
from src.fraud_pipeline.registry import ModelRegistry


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_model_manager_is_bounded_and_uses_lru_order() -> None:
    registry = ModelRegistry.load(PROJECT_ROOT)
    loaded: list[str] = []

    def loader(spec):
        loaded.append(spec.identifier)
        return object()

    manager = ModelManager(registry, max_loaded_models=2, loader=loader)
    first = registry.get("logistic_regression.v1")
    second = registry.get("lightgbm.v1")
    third = registry.get("catboost.v1")

    manager.get(first)
    manager.get(second)
    manager.get(first)
    manager.get(third)

    status = manager.status()
    assert status["loaded_models"] == ["logistic_regression.v1", "catboost.v1"]
    assert loaded == [
        "logistic_regression.v1",
        "lightgbm.v1",
        "catboost.v1",
    ]
    states = {item["model_identifier"]: item for item in status["models"]}
    assert states["catboost.v1"]["load_time_ms"] is not None
    assert states["catboost.v1"]["process_rss_after_load_bytes"] > 0


def test_model_load_failure_does_not_break_unrelated_model() -> None:
    registry = ModelRegistry.load(PROJECT_ROOT)

    def loader(spec):
        if spec.identifier == "catboost.v2":
            raise FileNotFoundError("missing")
        return object()

    manager = ModelManager(registry, loader=loader)
    with pytest.raises(ModelLoadError):
        manager.get(registry.get("catboost.v2"))
    assert manager.get(registry.get("logistic_regression.v1")) is not None
    states = {
        item["model_identifier"]: item for item in manager.status()["models"]
    }
    assert states["catboost.v2"]["status"] == "failed"
    assert states["logistic_regression.v1"]["status"] == "loaded"


def test_status_remains_responsive_while_native_model_is_loading() -> None:
    registry = ModelRegistry.load(PROJECT_ROOT)
    loading = threading.Event()
    release = threading.Event()

    def loader(spec):
        loading.set()
        assert release.wait(timeout=2)
        return object()

    manager = ModelManager(registry, loader=loader)
    spec = registry.get("neural_network.v2")
    worker = threading.Thread(target=manager.get, args=(spec,))
    worker.start()
    assert loading.wait(timeout=1)

    try:
        status = manager.status()
        states = {
            item["model_identifier"]: item for item in status["models"]
        }
        assert states["neural_network.v2"]["status"] == "loading"
    finally:
        release.set()
        worker.join(timeout=2)

    assert not worker.is_alive()
