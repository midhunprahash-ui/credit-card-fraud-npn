#!/usr/bin/env python3
"""Upload only registry-approved model bundles and verified runtime assets."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import boto3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.fraud_pipeline.artifacts import sha256_file
from src.fraud_pipeline.deployment_artifacts import (
    DeploymentArtifactContract,
    approved_bundle_files,
    upload_model_bundle,
)
from src.fraud_pipeline.registry import ModelRegistry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models", nargs="*", help="Stable identifiers; default: all eight")
    parser.add_argument("--bucket", default=os.getenv("R2_BUCKET_NAME", "fraud-model-artifacts"))
    parser.add_argument("--transport", choices=("s3", "wrangler"), default="s3")
    parser.add_argument("--exclude-runtime", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-round-trip", action="store_true")
    parser.add_argument(
        "--skip-over-bytes",
        type=int,
        default=0,
        help="Explicit recovery option for transports with a per-object limit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    registry = ModelRegistry.load(PROJECT_ROOT)
    selected = [registry.get(item) for item in args.models] if args.models else list(registry)
    contract = DeploymentArtifactContract.load(
        PROJECT_ROOT / "config/deployment_artifacts.json", PROJECT_ROOT
    )
    planned = []
    for spec in selected:
        for path in approved_bundle_files(contract, spec):
            relative = path.relative_to(spec.artifact_directory).as_posix()
            planned.append(
                (path, f"{contract.model_prefix(spec)}/{relative}", sha256_file(path))
            )
    if not args.exclude_runtime:
        runtime = contract.runtime_artifact("behavioral_reference.v2")
        if not runtime.local_path.is_file() or sha256_file(runtime.local_path) != runtime.sha256:
            raise ValueError("The approved behavioral reference is missing or changed")
        planned.append((runtime.local_path, runtime.object_key, runtime.sha256))
    skipped = [item for item in planned if args.skip_over_bytes and item[0].stat().st_size > args.skip_over_bytes]
    planned = [item for item in planned if item not in skipped]

    print(
        json.dumps(
            {
                "bucket": args.bucket,
                "models": [spec.identifier for spec in selected],
                "objects": len(planned),
                "bytes": sum(path.stat().st_size for path, _, _ in planned),
                "transport": args.transport,
                "dry_run": args.dry_run,
                "skipped_objects": [key for _, key, _ in skipped],
            },
            sort_keys=True,
        )
    )
    if args.dry_run:
        return
    if args.transport == "wrangler":
        _upload_with_wrangler(
            args.bucket, planned, round_trip=not args.no_round_trip
        )
    else:
        client = _s3_client()
        for spec in selected:
            upload_model_bundle(
                client=client, bucket=args.bucket, contract=contract, spec=spec
            )
        if not args.exclude_runtime:
            runtime = contract.runtime_artifact("behavioral_reference.v2")
            client.upload_file(
                str(runtime.local_path),
                args.bucket,
                runtime.object_key,
                ExtraArgs={"Metadata": {"sha256": runtime.sha256}},
            )
        if not args.no_round_trip:
            _verify_with_s3(client, args.bucket, planned)
    print(
        json.dumps(
            {
                "status": "PARTIAL" if skipped else "PASS",
                "objects_verified": len(planned),
                "objects_skipped": len(skipped),
            }
        )
    )


def _upload_with_wrangler(
    bucket: str, planned: list[tuple[Path, str, str]], *, round_trip: bool
) -> None:
    wrangler = PROJECT_ROOT / "frontend/node_modules/.bin/wrangler"
    if not wrangler.is_file():
        raise FileNotFoundError("Run npm ci in frontend before using Wrangler transport")
    with tempfile.TemporaryDirectory(prefix="npn-r2-verify-") as directory:
        verify_root = Path(directory)
        for index, (path, key, expected_sha) in enumerate(planned, start=1):
            print(f"[{index}/{len(planned)}] upload {key}", flush=True)
            subprocess.run(
                [
                    str(wrangler),
                    "r2",
                    "object",
                    "put",
                    f"{bucket}/{key}",
                    "--file",
                    str(path),
                    "--remote",
                    "--force",
                ],
                cwd=PROJECT_ROOT / "frontend",
                check=True,
            )
            if round_trip:
                destination = verify_root / str(index)
                subprocess.run(
                    [
                        str(wrangler),
                        "r2",
                        "object",
                        "get",
                        f"{bucket}/{key}",
                        "--file",
                        str(destination),
                        "--remote",
                    ],
                    cwd=PROJECT_ROOT / "frontend",
                    check=True,
                )
                if destination.stat().st_size != path.stat().st_size:
                    raise ValueError(f"R2 round-trip size mismatch: {key}")
                if sha256_file(destination) != expected_sha:
                    raise ValueError(f"R2 round-trip checksum mismatch: {key}")


def _s3_client():
    required = {
        "R2_ENDPOINT_URL": os.getenv("R2_ENDPOINT_URL"),
        "R2_ACCESS_KEY_ID": os.getenv("R2_ACCESS_KEY_ID"),
        "R2_SECRET_ACCESS_KEY": os.getenv("R2_SECRET_ACCESS_KEY"),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing server-only environment variables: {missing}")
    return boto3.client(
        "s3",
        endpoint_url=required["R2_ENDPOINT_URL"],
        aws_access_key_id=required["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=required["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def _verify_with_s3(client, bucket: str, planned: list[tuple[Path, str, str]]) -> None:
    with tempfile.TemporaryDirectory(prefix="npn-r2-verify-") as directory:
        for index, (source, key, expected_sha) in enumerate(planned):
            destination = Path(directory) / str(index)
            client.download_file(bucket, key, str(destination))
            if destination.stat().st_size != source.stat().st_size:
                raise ValueError(f"R2 round-trip size mismatch: {key}")
            if sha256_file(destination) != expected_sha:
                raise ValueError(f"R2 round-trip checksum mismatch: {key}")


if __name__ == "__main__":
    main()
