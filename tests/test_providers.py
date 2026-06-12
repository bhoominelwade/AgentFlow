import pytest

from src.providers import provider_for_model


def test_claude_models_route_to_anthropic():
    assert provider_for_model("claude-3-5-sonnet-20241022") == "anthropic"
    assert provider_for_model("claude-3-haiku-20240307") == "anthropic"


def test_gpt_models_route_to_openai():
    assert provider_for_model("gpt-4o") == "openai"
    assert provider_for_model("gpt-4o-mini") == "openai"


def test_gemini_models_route_to_gemini():
    assert provider_for_model("gemini-1.5-flash") == "gemini"


def test_unknown_model_raises():
    with pytest.raises(ValueError):
        provider_for_model("llama-3")
