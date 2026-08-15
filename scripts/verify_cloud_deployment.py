#!/usr/bin/env python3
"""Verify the deployed Pages -> Render -> Supabase/R2 integration boundary."""

from __future__ import annotations

import argparse
import json

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-url", default="https://credit-card-fraud-npn.onrender.com"
    )
    parser.add_argument(
        "--pages-url", default="https://npn-fraud-analyst.pages.dev"
    )
    args = parser.parse_args()
    api_url = args.api_url.rstrip("/")
    pages_url = args.pages_url.rstrip("/")
    with httpx.Client(timeout=90, follow_redirects=True) as client:
        health = _json(client, f"{api_url}/health")
        if health.get("status") != "ok" or health.get("models_registered") != 8:
            raise RuntimeError("Render health does not expose eight registered models")
        integrations = _json(client, f"{api_url}/integrations")
        for name in ("supabase", "cloudflare_r2"):
            if not integrations.get(name, {}).get("reachable"):
                raise RuntimeError(f"Integration is not reachable: {name}")
        models = _json(client, f"{api_url}/models").get("models", [])
        if len(models) != 8 or len({item["model_identifier"] for item in models}) != 8:
            raise RuntimeError("Deployed model catalog is incomplete")
        preflight = client.options(
            f"{api_url}/health",
            headers={
                "Origin": pages_url,
                "Access-Control-Request-Method": "GET",
            },
        )
        preflight.raise_for_status()
        if preflight.headers.get("access-control-allow-origin") != pages_url:
            raise RuntimeError("Render CORS does not allow the Pages production origin")
        page = client.get(pages_url)
        page.raise_for_status()
        if "NPN Fraud Analyst" not in page.text:
            raise RuntimeError("Cloudflare Pages is not serving the analyst console")
    print(
        json.dumps(
            {
                "status": "PASS",
                "api_url": api_url,
                "pages_url": pages_url,
                "models_registered": 8,
                "supabase": "reachable",
                "r2": "reachable",
                "cors": "exact-origin",
            },
            sort_keys=True,
        )
    )


def _json(client: httpx.Client, url: str) -> dict:
    response = client.get(url)
    response.raise_for_status()
    document = response.json()
    if not isinstance(document, dict):
        raise RuntimeError(f"Expected JSON object from {url}")
    return document


if __name__ == "__main__":
    main()
