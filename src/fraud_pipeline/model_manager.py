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
        # Native model initialization is serialized to avoid overlapping memory
        # spikes. It deliberately does not hold the state/cache lock, so health
        # and model-status requests remain responsive during a slow load.
        self._load_lock = threading.Lock()

    def get(self, spec: ModelSpec) -> ModelAdapter:
        with self._lock:
            cached = self._cache.pop(spec.identifier, None)
            if cached is not None:
                self._cache[spec.identifier] = cached
                return cached

        with self._load_lock:
            # Another request may have populated the cache while this request
            # waited for the single model-loading slot.
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
                with self._lock:
                    state.status = "failed"
                    state.load_time_ms = (time.perf_counter() - started) * 1_000
                    state.error = type(error).__name__
                raise ModelLoadError(spec.identifier, type(error).__name__) from error

            memory_after = process.memory_info().rss
            artifact_bytes = sum(
                path.stat().st_size
                for path in spec.artifact_directory.rglob("*")
                if path.is_file()
            )
            evicted_adapters: list[ModelAdapter] = []
            with self._lock:
                state.status = "loaded"
                state.load_time_ms = (time.perf_counter() - started) * 1_000
                state.memory_delta_bytes = max(0, memory_after - memory_before)
                state.process_rss_after_load_bytes = memory_after
                state.artifact_bytes = artifact_bytes
                self._cache[spec.identifier] = adapter
                while len(self._cache) > self.max_loaded_models:
                    identifier, evicted_adapter = self._cache.popitem(last=False)
                    self._states[identifier].status = "not_loaded"
                    evicted_adapters.append(evicted_adapter)
            if evicted_adapters:
                evicted_adapters.clear()
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
