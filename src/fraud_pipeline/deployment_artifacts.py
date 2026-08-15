"""Private R2 deployment contract and verified local artifact cache."""

from __future__ import annotations

import json
import mimetypes
import shutil
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .artifacts import sha256_file
from .model_adapters import verify_artifact_manifest
from .registry import ModelSpec


class DeploymentArtifactError(RuntimeError):
    """A selected deployment artifact is missing, unsafe, or corrupt."""


@dataclass(frozen=True)
class RuntimeArtifact:
    name: str
    object_key: str
    local_path: Path
    bytes: int
    sha256: str


class DeploymentArtifactContract:
    def __init__(self, path: Path, project_root: Path) -> None:
        self.path = path
        self.project_root = project_root.resolve()
        document = json.loads(path.read_text())
        if document.get("schema_version") != "1.0":
            raise DeploymentArtifactError("Unsupported deployment artifact contract")
        prefix = str(document.get("r2_prefix", "")).strip("/")
        if not prefix or ".." in PurePosixPath(prefix).parts:
            raise DeploymentArtifactError("Unsafe R2 artifact prefix")
        self.r2_prefix = prefix
        models = document.get("models")
        runtime = document.get("runtime")
        if not isinstance(models, dict) or not isinstance(runtime, dict):
            raise DeploymentArtifactError("Invalid deployment artifact contract")
        self.models: Mapping[str, dict[str, Any]] = models
        self.runtime: Mapping[str, dict[str, Any]] = runtime

    @classmethod
    def load(cls, path: Path, project_root: Path) -> "DeploymentArtifactContract":
        if not path.is_file():
            raise DeploymentArtifactError(f"Deployment contract is missing: {path}")
        return cls(path, project_root)

    def model_entry(self, spec: ModelSpec) -> dict[str, Any]:
        entry = self.models.get(spec.identifier)
        if not isinstance(entry, dict) or entry.get("run_id") != spec.run_id:
            raise DeploymentArtifactError(
                f"Deployment contract does not match {spec.identifier}"
            )
        return entry

    def model_prefix(self, spec: ModelSpec) -> str:
        entry = self.model_entry(spec)
        expected = (
            f"{self.r2_prefix}/{spec.version_name.lower()}/"
            f"{spec.model_key}/{spec.run_id}"
        )
        if entry.get("object_prefix") != expected:
            raise DeploymentArtifactError(
                f"Unsafe object prefix for {spec.identifier}"
            )
        return expected

    def runtime_artifact(self, name: str) -> RuntimeArtifact:
        entry = self.runtime.get(name)
        if not isinstance(entry, dict):
            raise DeploymentArtifactError(f"Unknown runtime artifact: {name}")
        object_key = str(entry.get("object_key", ""))
        relative_path = Path(str(entry.get("local_path", "")))
        if (
            not object_key.startswith(f"{self.r2_prefix}/runtime/")
            or ".." in PurePosixPath(object_key).parts
            or relative_path.is_absolute()
            or ".." in relative_path.parts
        ):
            raise DeploymentArtifactError(f"Unsafe runtime artifact path: {name}")
        local_path = (self.project_root / relative_path).resolve()
        if self.project_root not in local_path.parents:
            raise DeploymentArtifactError(f"Runtime artifact escapes project: {name}")
        return RuntimeArtifact(
            name=name,
            object_key=object_key,
            local_path=local_path,
            bytes=int(entry["bytes"]),
            sha256=str(entry["sha256"]),
        )


class R2ArtifactStore:
    """Download immutable approved objects and atomically publish a verified cache."""

    def __init__(
        self,
        *,
        client: Any,
        bucket: str,
        contract: DeploymentArtifactContract,
    ) -> None:
        self.client = client
        self.bucket = bucket
        self.contract = contract
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()
        self._verified: set[str] = set()

    def ensure_model(self, spec: ModelSpec) -> dict[str, Any]:
        lock = self._lock_for(spec.identifier)
        with lock:
            if (
                spec.identifier in self._verified
                and spec.artifact_directory.is_dir()
            ):
                return {"files_verified": 0, "downloaded": False, "cached": True}
            if spec.artifact_directory.is_dir():
                try:
                    result = verify_artifact_manifest(spec.artifact_directory)
                    self._verify_local_manifest_pin(spec)
                    self._verified.add(spec.identifier)
                    return {**result, "downloaded": False}
                except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
                    raise DeploymentArtifactError(
                        f"Existing artifact cache is invalid for {spec.identifier}"
                    ) from error

            entry = self.contract.model_entry(spec)
            parent = spec.artifact_directory.parent
            parent.mkdir(parents=True, exist_ok=True)
            temporary = Path(tempfile.mkdtemp(prefix=f".{spec.run_id}-", dir=parent))
            try:
                manifest_path = temporary / "manifest.json"
                self._download(
                    f"{self.contract.model_prefix(spec)}/manifest.json",
                    manifest_path,
                )
                if sha256_file(manifest_path) != entry["manifest_sha256"]:
                    raise DeploymentArtifactError(
                        f"Manifest checksum mismatch for {spec.identifier}"
                    )
                manifest = _validated_manifest(manifest_path, spec.run_id)
                required = set(spec.files.values()) | {
                    "feature_schema.json",
                    "threshold.json",
                }
                declared = {str(item["path"]) for item in manifest["files"]}
                if not required.issubset(declared):
                    raise DeploymentArtifactError(
                        f"Manifest omits required files for {spec.identifier}"
                    )
                for item in manifest["files"]:
                    relative = _safe_relative(str(item["path"]))
                    destination = temporary / relative
                    self._download(
                        f"{self.contract.model_prefix(spec)}/{relative.as_posix()}",
                        destination,
                    )
                    if destination.stat().st_size != int(item["bytes"]):
                        raise DeploymentArtifactError(
                            f"Downloaded size mismatch: {spec.identifier}/{relative}"
                        )
                    if sha256_file(destination) != item["sha256"]:
                        raise DeploymentArtifactError(
                            f"Downloaded checksum mismatch: {spec.identifier}/{relative}"
                        )
                result = verify_artifact_manifest(temporary)
                if spec.artifact_directory.exists():
                    result = verify_artifact_manifest(spec.artifact_directory)
                    self._verify_local_manifest_pin(spec)
                    self._verified.add(spec.identifier)
                    return {**result, "downloaded": False}
                temporary.replace(spec.artifact_directory)
                self._verified.add(spec.identifier)
                return {**result, "downloaded": True}
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)

    def ensure_runtime(self, name: str) -> dict[str, Any]:
        artifact = self.contract.runtime_artifact(name)
        lock = self._lock_for(f"runtime:{name}")
        with lock:
            if artifact.local_path.is_file():
                if (
                    artifact.local_path.stat().st_size == artifact.bytes
                    and sha256_file(artifact.local_path) == artifact.sha256
                ):
                    return {"downloaded": False, "bytes": artifact.bytes}
                raise DeploymentArtifactError(
                    f"Existing runtime artifact is invalid: {name}"
                )
            artifact.local_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                prefix=f".{artifact.local_path.name}-",
                dir=artifact.local_path.parent,
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
            try:
                self._download(artifact.object_key, temporary)
                if temporary.stat().st_size != artifact.bytes:
                    raise DeploymentArtifactError(
                        f"Downloaded runtime size mismatch: {name}"
                    )
                if sha256_file(temporary) != artifact.sha256:
                    raise DeploymentArtifactError(
                        f"Downloaded runtime checksum mismatch: {name}"
                    )
                temporary.replace(artifact.local_path)
                return {"downloaded": True, "bytes": artifact.bytes}
            finally:
                temporary.unlink(missing_ok=True)

    def _verify_local_manifest_pin(self, spec: ModelSpec) -> None:
        entry = self.contract.model_entry(spec)
        if sha256_file(spec.artifact_directory / "manifest.json") != entry[
            "manifest_sha256"
        ]:
            raise DeploymentArtifactError(
                f"Local manifest is not the approved manifest for {spec.identifier}"
            )

    def _download(self, key: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, key, str(destination))

    def _lock_for(self, name: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(name, threading.Lock())


def upload_model_bundle(
    *,
    client: Any,
    bucket: str,
    contract: DeploymentArtifactContract,
    spec: ModelSpec,
) -> dict[str, int]:
    """Upload only files declared by the approved, pinned local manifest."""
    files = approved_bundle_files(contract, spec)
    prefix = contract.model_prefix(spec)
    for path in files:
        relative = path.relative_to(spec.artifact_directory).as_posix()
        extra: dict[str, Any] = {
            "Metadata": {"sha256": sha256_file(path)},
            "ContentType": mimetypes.guess_type(path.name)[0]
            or "application/octet-stream",
        }
        client.upload_file(
            str(path), bucket, f"{prefix}/{relative}", ExtraArgs=extra
        )
    return {"files_uploaded": len(files), "bytes_uploaded": sum(p.stat().st_size for p in files)}


def approved_bundle_files(
    contract: DeploymentArtifactContract, spec: ModelSpec
) -> list[Path]:
    verify_artifact_manifest(spec.artifact_directory)
    entry = contract.model_entry(spec)
    manifest_path = spec.artifact_directory / "manifest.json"
    if sha256_file(manifest_path) != entry["manifest_sha256"]:
        raise DeploymentArtifactError(
            f"Local manifest is not deployment-approved for {spec.identifier}"
        )
    manifest = _validated_manifest(manifest_path, spec.run_id)
    return [manifest_path] + [
        spec.artifact_directory / _safe_relative(str(item["path"]))
        for item in manifest["files"]
    ]


def _validated_manifest(path: Path, run_id: str) -> dict[str, Any]:
    document = json.loads(path.read_text())
    if document.get("artifact_directory") != run_id:
        raise DeploymentArtifactError("Manifest run ID does not match registry")
    files = document.get("files")
    if not isinstance(files, list) or not files:
        raise DeploymentArtifactError("Artifact manifest has no files")
    seen: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            raise DeploymentArtifactError("Invalid artifact manifest entry")
        relative = _safe_relative(str(item.get("path", ""))).as_posix()
        if relative in seen:
            raise DeploymentArtifactError("Duplicate artifact manifest path")
        seen.add(relative)
        if int(item.get("bytes", -1)) < 0 or len(str(item.get("sha256", ""))) != 64:
            raise DeploymentArtifactError("Invalid artifact manifest size or checksum")
    return document


def _safe_relative(value: str) -> Path:
    pure = PurePosixPath(value)
    if not value or pure.is_absolute() or ".." in pure.parts or "\\" in value:
        raise DeploymentArtifactError(f"Unsafe artifact path: {value}")
    return Path(*pure.parts)
