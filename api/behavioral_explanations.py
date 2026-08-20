"""Grounded one-line summaries for model-contributing behavioral features."""

from __future__ import annotations

import logging
from typing import Any, Literal

import httpx

from .settings import Settings, get_settings


LOGGER = logging.getLogger(__name__)
ExplanationSource = Literal["openrouter", "template"]

_BEHAVIORAL_MARKERS = (
    "_prior_count",
    "_seconds_since_previous",
    "_prior_numeric_count",
    "_prior_mean",
    "_prior_std",
    "_prior_unique_count",
)


def _canonical_feature(name: str) -> str:
    return name.split("__", 1)[-1]


def _behavioral_label(name: str) -> str | None:
    canonical = _canonical_feature(name)
    if not any(marker in canonical for marker in _BEHAVIORAL_MARKERS):
        return None
    if "seconds_since_previous" in canonical:
        return "time since the previous related transaction"
    if "prior_mean" in canonical:
        return "historical average transaction amount"
    if "prior_std" in canonical:
        return "historical transaction amount variability"
    if "prior_unique_count" in canonical:
        return "historical variety of transaction activity"
    return "previous transaction frequency"


def _select_behavioral_labels(
    features: list[dict[str, Any]], *, decision: bool
) -> list[str]:
    expected_direction = "toward_fraud" if decision else "toward_not_fraud"
    labels: list[str] = []
    for feature in features:
        if feature.get("direction") != expected_direction:
            continue
        contribution = feature.get("contribution")
        if not isinstance(contribution, (int, float)) or abs(contribution) <= 1e-12:
            continue
        label = _behavioral_label(str(feature.get("feature", "")))
        if label and label not in labels:
            labels.append(label)
        if len(labels) == 2:
            break
    return labels


def _template(labels: list[str], *, decision: bool) -> str:
    joined = labels[0] if len(labels) == 1 else f"{labels[0]} and {labels[1]}"
    return f"It is flagged as fraud because {joined} increased the model's fraud score."


def _openrouter_summary(
    labels: list[str], *, decision: bool, settings: Settings
) -> str | None:
    secret = settings.openrouter_api_key
    if secret is None:
        return None
    outcome = "fraud" if decision else "not fraud"
    direction = "increased" if decision else "reduced"
    prompt = (
        "Write exactly one concise sentence for a fraud analyst. "
        "The sentence must begin exactly with: It is flagged as fraud because "
        "Use only the supplied behavioral factors; do not add facts, values, or causes. "
        "Describe model influence rather than claiming proof of fraud. "
        "Never return None, null, N/A, or an empty response. "
        f"Outcome: {outcome}. Direction: factors {direction} the fraud score. "
        f"Behavioral factors: {', '.join(labels)}."
    )
    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {secret.get_secret_value()}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openrouter_model,
                "temperature": 0,
                "max_tokens": 256,
                "reasoning": {
                    "effort": "none",
                    "exclude": True,
                },
                "messages": [
                    {
                        "role": "system",
                        "content": "Return only the requested grounded sentence.",
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=settings.openrouter_timeout_seconds,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        sentence = " ".join(str(content).strip().strip('"').split())
        sentinel = sentence.casefold().rstrip(".")
        required_prefix = "It is flagged as fraud because "
        if (
            not sentence
            or len(sentence) > 240
            or sentinel in {"none", "null", "n/a", "not available"}
            or not sentence.casefold().startswith(required_prefix.casefold())
        ):
            return None
        return required_prefix + sentence[len(required_prefix) :]
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        LOGGER.info("openrouter_behavioral_explanation_unavailable")
        return None


def generate_behavioral_explanation(
    features: list[dict[str, Any]],
    *,
    decision: bool,
    settings: Settings | None = None,
) -> tuple[str | None, ExplanationSource | None]:
    """Return a grounded LLM sentence or deterministic equivalent."""
    if not decision:
        return None, None
    labels = _select_behavioral_labels(features, decision=decision)
    if not labels:
        return None, None
    active_settings = settings or get_settings()
    generated = _openrouter_summary(labels, decision=decision, settings=active_settings)
    if generated:
        return generated, "openrouter"
    return _template(labels, decision=decision), "template"
