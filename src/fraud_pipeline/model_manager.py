"""Lazy bounded cache for independently loadable model adapters."""

from __future__ import annotations

import gc
import threading
import time
from collections import OrderedDict
from dataclasses import asdict, dataclass
from typing import Callable

import psutil

from .model_adapters import ModelAdapter, load_model_adapter
from .registry import ModelRegistry, ModelSpec


class ModelLoadError(RuntimeError):
    def __init__(self, model_identifier: str, error_type: str) -> None:
        super().__init__(f"Unable to load approved model {model_identifier}")
        self.model_identifier = model_identifier
        self.error_type = error_type


@dataclass
class ModelLoadState:
    model_identifier: str
    status: str = "not_loaded"
    load_time_ms: float | None = None
    artifact_bytes: int | None = None
    memory_delta_bytes: int | None = None
    process_rss_after_load_bytes: int | None = None
    error: str | None = None


class ModelManager:
    """Load requested models only and evict the least recently used adapter."""

    def __init__(
        self,
        registry: ModelRegistry,
        *,
        max_loaded_models: int = 2,
        loader: Callable[[ModelSpec], ModelAdapter] = load_model_adapter,
    ) -> None:
        if max_loaded_models < 1:
            raise ValueError("max_loaded_models must be at least one")
        self.registry = registry
        self.max_loaded_models = max_loaded_models
        self.loader = loader
        self._cache: OrderedDict[str, ModelAdapter] = OrderedDict()
        self._states = {spec.identifier: ModelLoadState(spec.identifier) for spec in registry}
        self._lock = threading.RLock()

    def get(self, spec: ModelSpec) -> ModelAdapter:
        with self._lock:
            cached = self._cache.pop(spec.identifier, None)
            if cached is not None:
                self._cache[spec.identifier] = cached
                return cached
            state = self._states[spec.identifier]
            state.status = "loading"
            state.error = None
            started = time.perf_counter()
            process = psutil.Process()
            memory_before = process.memory_info().rss
            try:
                adapter = self.loader(spec)
            except Exception as error:
                state.status = "failed"
                state.load_time_ms = (time.perf_counter() - started) * 1_000
                state.error = type(error).__name__
                raise ModelLoadError(spec.identifier, type(error).__name__) from error
            state.status = "loaded"
            state.load_time_ms = (time.perf_counter() - started) * 1_000
            memory_after = process.memory_info().rss
            state.memory_delta_bytes = max(0, memory_after - memory_before)
            state.process_rss_after_load_bytes = memory_after
            state.artifact_bytes = sum(
                path.stat().st_size
                for path in spec.artifact_directory.rglob("*")
                if path.is_file()
            )
            self._cache[spec.identifier] = adapter
            evicted = False
            while len(self._cache) > self.max_loaded_models:
                identifier, _ = self._cache.popitem(last=False)
                self._states[identifier].status = "not_loaded"
                evicted = True
            if evicted:
                gc.collect()
            return adapter

    def preload(self, identifiers: list[str]) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        for identifier in identifiers:
            spec = self.registry.get(identifier)
            try:
                self.get(spec)
                results.append({"model_identifier": identifier, "status": "loaded"})
            except Exception as error:
                results.append(
                    {
                        "model_identifier": identifier,
                        "status": "failed",
                        "error": type(error).__name__,
                    }
                )
        return results

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "max_loaded_models": self.max_loaded_models,
                "loaded_models": list(self._cache),
                "models": [asdict(self._states[spec.identifier]) for spec in self.registry],
            }
