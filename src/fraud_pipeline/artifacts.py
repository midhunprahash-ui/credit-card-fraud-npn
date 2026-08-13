"""Small helpers for reproducible, versioned model bundles."""

from __future__ import annotations

import hashlib
import json
import platform
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Iterable


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")


def package_versions(packages: Iterable[str]) -> dict[str, str]:
    result = {"python": platform.python_version()}
    for package in packages:
        try:
            result[package] = version(package)
        except PackageNotFoundError:
            result[package] = "not-installed"
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(directory: Path) -> dict[str, Any]:
    files = []
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        files.append(
            {
                "path": str(path.relative_to(directory)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {"artifact_directory": directory.name, "files": files}
