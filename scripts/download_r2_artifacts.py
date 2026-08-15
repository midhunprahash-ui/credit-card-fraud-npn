#!/usr/bin/env python3
"""Download approved R2 objects into a manifest-verified local cache."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import boto3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.fraud_pipeline.deployment_artifacts import (
    DeploymentArtifactContract,
    R2ArtifactStore,
)
from src.fraud_pipeline.registry import ModelRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models", nargs="*", help="Stable identifiers; default: all eight")
    parser.add_argument("--include-runtime", action="store_true")
    args = parser.parse_args()
    required = {
        "R2_ENDPOINT_URL": os.getenv("R2_ENDPOINT_URL"),
        "R2_ACCESS_KEY_ID": os.getenv("R2_ACCESS_KEY_ID"),
        "R2_SECRET_ACCESS_KEY": os.getenv("R2_SECRET_ACCESS_KEY"),
        "R2_BUCKET_NAME": os.getenv("R2_BUCKET_NAME"),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing server-only environment variables: {missing}")
    client = boto3.client(
        "s3",
        endpoint_url=required["R2_ENDPOINT_URL"],
        aws_access_key_id=required["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=required["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    contract = DeploymentArtifactContract.load(
        PROJECT_ROOT / "config/deployment_artifacts.json", PROJECT_ROOT
    )
    store = R2ArtifactStore(
        client=client, bucket=str(required["R2_BUCKET_NAME"]), contract=contract
    )
    registry = ModelRegistry.load(PROJECT_ROOT)
    selected = [registry.get(item) for item in args.models] if args.models else list(registry)
    for spec in selected:
        print(spec.identifier, store.ensure_model(spec))
    if args.include_runtime:
        print("behavioral_reference.v2", store.ensure_runtime("behavioral_reference.v2"))


if __name__ == "__main__":
    main()
