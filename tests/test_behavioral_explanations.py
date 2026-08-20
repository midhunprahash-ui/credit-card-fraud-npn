from api.behavioral_explanations import generate_behavioral_explanation
from api.settings import Settings


def test_behavioral_explanation_uses_template_without_openrouter_key() -> None:
    text, source = generate_behavioral_explanation(
        [
            {
                "feature": "numeric__device_key_prior_count",
                "contribution": 0.4,
                "direction": "toward_fraud",
            }
        ],
        decision=True,
        settings=Settings(_env_file=None, openrouter_api_key=None),
    )

    assert source == "template"
    assert text == (
        "It is flagged as fraud because previous transaction frequency increased "
        "the model's fraud score."
    )


def test_behavioral_explanation_rejects_non_behavioral_features() -> None:
    text, source = generate_behavioral_explanation(
        [
            {
                "feature": "numeric__TransactionAmt",
                "contribution": -0.2,
                "direction": "toward_not_fraud",
            }
        ],
        decision=False,
        settings=Settings(_env_file=None, openrouter_api_key=None),
    )

    assert text is None
    assert source is None
