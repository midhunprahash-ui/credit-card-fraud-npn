#!/usr/bin/env python3
"""Verify all eight selected V1/V2 bundles against held-out predictions."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.fraud_pipeline.inference_runtime import (
    SelectedModelSpec,
    predict_with_selected_model,
    selected_model_specs,
    verify_artifact_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-size", type=int, default=32)
    parser.add_argument(
        "--test-data",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "v2" / "test.parquet",
    )
    parser.add_argument(
        "--raw-zip",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw" / "ieee-fraud-detection.zip",
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--model-key", help=argparse.SUPPRESS)
    parser.add_argument("--version-name", choices=["V1", "V2"], help=argparse.SUPPRESS)
    parser.add_argument("--run-id", help=argparse.SUPPRESS)
    parser.add_argument("--artifact-directory", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--threshold", type=float, help=argparse.SUPPRESS)
    parser.add_argument("--sample-path", type=Path, help=argparse.SUPPRESS)
    return parser.parse_args()


def identity_transaction_ids(raw_zip: Path) -> set[int]:
    with zipfile.ZipFile(raw_zip) as archive:
        with archive.open("train_identity.csv") as identity_csv:
            identity = pd.read_csv(identity_csv, usecols=["TransactionID"])
    return set(identity["TransactionID"].astype("int64"))


def build_verification_sample(
    test_data: Path,
    raw_zip: Path,
    sample_size: int,
) -> pd.DataFrame:
    if sample_size < 1:
        raise ValueError("sample-size must be at least one")
    sample = pd.read_parquet(test_data).iloc[:sample_size].copy()
    required = {"TransactionID", "TransactionDT", "isFraud"}
    missing = required - set(sample)
    if missing:
        raise ValueError(f"Held-out data is missing required columns: {sorted(missing)}")
    ordered = sample.sort_values(["TransactionDT", "TransactionID"], kind="stable")
    if not ordered.index.equals(sample.index):
        raise ValueError("Held-out verification sample is not chronological")

    identity_ids = identity_transaction_ids(raw_zip)
    sample["has_identity"] = sample["TransactionID"].isin(identity_ids).astype("int8")
    return sample


def run_worker(args: argparse.Namespace) -> int:
    required_values = (
        args.model_key,
        args.version_name,
        args.run_id,
        args.artifact_directory,
        args.threshold,
        args.sample_path,
    )
    if any(value is None for value in required_values):
        raise ValueError("Worker invocation is missing model arguments")

    spec = SelectedModelSpec(
        model_key=args.model_key,
        version_name=args.version_name,
        run_id=args.run_id,
        artifact_directory=args.artifact_directory,
        threshold=args.threshold,
    )
    manifest_result = verify_artifact_manifest(spec.artifact_directory)
    sample = pd.read_parquet(args.sample_path)
    labels = sample["isFraud"].copy()
    transaction_ids = sample["TransactionID"].copy()
    model_input = sample.drop(columns=["isFraud", "TransactionID"])
    if "isFraud" in model_input or "TransactionID" in model_input:
        raise AssertionError("Protected target/identifier reached model input")

    actual = predict_with_selected_model(spec, model_input)
    expected_frame = pd.read_parquet(
        spec.artifact_directory / "test_predictions.parquet",
        columns=["TransactionID", "isFraud", "probability"],
    ).iloc[: len(sample)]
    if not expected_frame["TransactionID"].reset_index(drop=True).equals(
        transaction_ids.reset_index(drop=True)
    ):
        raise ValueError("Stored predictions do not match held-out TransactionID order")
    if not expected_frame["isFraud"].reset_index(drop=True).equals(
        labels.reset_index(drop=True)
    ):
        raise ValueError("Stored prediction labels do not match held-out ground truth")

    expected = expected_frame["probability"].to_numpy(dtype=np.float64)
    max_abs_delta = float(np.max(np.abs(actual - expected)))
    parity = bool(np.allclose(actual, expected, rtol=1e-5, atol=1e-7))
    result = {
        "model_name": spec.model_name,
        "run_id": spec.run_id,
        "rows_scored": len(sample),
        "files_verified": manifest_result["files_verified"],
        "label_hidden_during_inference": True,
        "max_abs_delta": max_abs_delta,
        "status": "PASS" if parity else "FAIL",
    }
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if parity else 1


def worker_command(spec: SelectedModelSpec, sample_path: Path) -> list[str]:
    return [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        "--model-key",
        spec.model_key,
        "--version-name",
        spec.version_name,
        "--run-id",
        spec.run_id,
        "--artifact-directory",
        str(spec.artifact_directory),
        "--threshold",
        str(spec.threshold),
        "--sample-path",
        str(sample_path),
    ]


def run_all(args: argparse.Namespace) -> int:
    specs = selected_model_specs(PROJECT_ROOT)
    sample = build_verification_sample(args.test_data, args.raw_zip, args.sample_size)
    results: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="fraud-model-verification-") as temporary:
        sample_path = Path(temporary) / "heldout_sample.parquet"
        sample.to_parquet(sample_path, index=False)
        for spec in specs:
            process = subprocess.run(
                worker_command(spec, sample_path),
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if process.returncode != 0:
                results.append(
                    {
                        "model_name": spec.model_name,
                        "run_id": spec.run_id,
                        "status": "FAIL",
                        "detail": process.stderr.strip() or process.stdout.strip(),
                    }
                )
                continue
            results.append(json.loads(process.stdout.strip().splitlines()[-1]))

    report = {
        "status": "PASS" if len(results) == 8 and all(r["status"] == "PASS" for r in results) else "FAIL",
        "sample_rows": len(sample),
        "chronological": True,
        "models": results,
    }
    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for result in results:
            delta = result.get("max_abs_delta", "n/a")
            print(f"{result['model_name']}: {result['status']} (max_abs_delta={delta})")
        print(f"Verification gate: {report['status']} ({len(results)}/8 models)")
    return 0 if report["status"] == "PASS" else 1


def main() -> int:
    args = parse_args()
    return run_worker(args) if args.worker else run_all(args)


if __name__ == "__main__":
    raise SystemExit(main())
