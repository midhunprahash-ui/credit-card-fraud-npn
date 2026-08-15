"""Strict loader for the approved V1 and V2 model registries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping, cast

from .model_contracts import (
    MODEL_ORDER,
    VERSION_ORDER,
    ModelKey,
    VersionName,
    model_identifier,
    model_name,
)


REGISTRY_FILES: dict[VersionName, str] = {
    "V1": "model_registry.json",
    "V2": "model_registry_v2.json",
}


@dataclass(frozen=True)
class ModelSpec:
    model_key: ModelKey
    version_name: VersionName
    run_id: str
    artifact_directory: Path
    threshold: float
    champion: bool
    validation_pr_auc: float
    test_pr_auc: float
    files: Mapping[str, str]

    @property
    def identifier(self) -> str:
        return model_identifier(self.model_key, self.version_name)

    @property
    def model_name(self) -> str:
        return model_name(self.model_key, self.version_name)


class ModelRegistry:
    """Validated, immutable view of the eight independently selectable runs."""

    def __init__(self, specs: list[ModelSpec]) -> None:
        self._specs = tuple(specs)
        self._by_identifier = {spec.identifier: spec for spec in specs}
        if len(self._specs) != 8 or len(self._by_identifier) != 8:
            raise ValueError("The selected-model registry must contain exactly eight pipelines")

    @classmethod
    def load(cls, project_root: Path) -> "ModelRegistry":
        root = project_root.resolve()
        artifact_root = (root / "artifacts").resolve()
        specs: list[ModelSpec] = []
        for version_name in VERSION_ORDER:
            registry_path = root / "config" / REGISTRY_FILES[version_name]
            registry = json.loads(registry_path.read_text())
            models = registry.get("models")
            if not isinstance(models, dict):
                raise ValueError(f"Invalid models object in {registry_path}")
            champion = registry.get("champion")
            if champion not in MODEL_ORDER:
                raise ValueError(f"Invalid champion in {registry_path}: {champion}")
            for model_key in MODEL_ORDER:
                config = models.get(model_key)
                if not isinstance(config, dict) or config.get("enabled") is not True:
                    raise ValueError(
                        f"Required model is not enabled: {model_identifier(model_key, version_name)}"
                    )
                specs.append(
                    _parse_spec(
                        artifact_root,
                        model_key,
                        version_name,
                        config,
                        champion=model_key == champion,
                    )
                )
        return cls(specs)

    def __iter__(self) -> Iterator[ModelSpec]:
        return iter(self._specs)

    def __len__(self) -> int:
        return len(self._specs)

    def get(self, identifier: str) -> ModelSpec:
        try:
            return self._by_identifier[identifier]
        except KeyError as error:
            raise ValueError(f"Unknown model identifier: {identifier}") from error

    def for_versions(self, versions: set[VersionName]) -> tuple[ModelSpec, ...]:
        return tuple(spec for spec in self._specs if spec.version_name in versions)


def _parse_spec(
    artifact_root: Path,
    model_key: ModelKey,
    version_name: VersionName,
    config: dict[str, Any],
    *,
    champion: bool,
) -> ModelSpec:
    threshold = float(config["threshold"])
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"Invalid threshold for {model_identifier(model_key, version_name)}")
    run_id = str(config["run_id"])
    directory = (artifact_root / str(config["artifact_subdirectory"])).resolve()
    if artifact_root not in directory.parents or directory.name != run_id:
        raise ValueError(f"Unsafe or inconsistent artifact path for {model_key}.{version_name}")
    files = {
        key: str(value)
        for key, value in config.items()
        if key.endswith("_file") and isinstance(value, str)
    }
    if "model_file" not in files:
        raise ValueError(f"Missing model_file for {model_key}.{version_name}")
    return ModelSpec(
        model_key=cast(ModelKey, model_key),
        version_name=version_name,
        run_id=run_id,
        artifact_directory=directory,
        threshold=threshold,
        champion=champion,
        validation_pr_auc=float(config["validation_pr_auc"]),
        test_pr_auc=float(config["test_pr_auc"]),
        files=files,
    )
