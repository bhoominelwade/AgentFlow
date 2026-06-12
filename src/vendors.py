import os
from dataclasses import dataclass

from src.router import ROUTING_MATRIX, BUDGET_FALLBACK_MODEL

TASK_TYPES = ["extraction", "code", "reasoning", "writing", "review"]
COMPLEXITIES = ["low", "medium", "high"]


def _tier_matrix(low: str, medium: str, high: str) -> dict:
    by_complexity = {"low": low, "medium": medium, "high": high}
    return {(task_type, c): by_complexity[c] for task_type in TASK_TYPES for c in COMPLEXITIES}


GEMINI_MATRIX = _tier_matrix("gemini-1.5-flash", "gemini-1.5-flash", "gemini-1.5-pro")
ANTHROPIC_MATRIX = _tier_matrix("claude-haiku-4-5", "claude-sonnet-4-6", "claude-opus-4-8")
OPENAI_MATRIX = _tier_matrix("gpt-4o-mini", "gpt-4o-mini", "gpt-4o")

MODERN_MATRIX = {
    ("extraction", "low"): "gemini-1.5-flash",
    ("extraction", "medium"): "gemini-1.5-flash",
    ("extraction", "high"): "gpt-4o-mini",
    ("code", "low"): "gpt-4o-mini",
    ("code", "medium"): "gpt-4o",
    ("code", "high"): "gpt-4o",
    ("reasoning", "low"): "gpt-4o-mini",
    ("reasoning", "medium"): "claude-haiku-4-5",
    ("reasoning", "high"): "claude-sonnet-4-6",
    ("writing", "low"): "gemini-1.5-flash",
    ("writing", "medium"): "claude-haiku-4-5",
    ("writing", "high"): "claude-sonnet-4-6",
    ("review", "low"): "claude-haiku-4-5",
    ("review", "medium"): "claude-haiku-4-5",
    ("review", "high"): "claude-sonnet-4-6",
}

KEY_ENV = {
    "gemini": "GOOGLE_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}

PRIORITY = ["anthropic", "openai", "gemini"]


@dataclass
class VendorConfig:
    vendor: str
    matrix: dict
    fallback_model: str
    orchestrator_model: str


SINGLE = {
    "gemini": VendorConfig("gemini", GEMINI_MATRIX, "gemini-1.5-flash", "gemini-1.5-pro"),
    "anthropic": VendorConfig("anthropic", ANTHROPIC_MATRIX, "claude-haiku-4-5", "claude-sonnet-4-6"),
    "openai": VendorConfig("openai", OPENAI_MATRIX, "gpt-4o-mini", "gpt-4o"),
}


class NoProviderKeyError(Exception):
    pass


def available_vendors(env=None) -> list[str]:
    env = os.environ if env is None else env
    return [vendor for vendor, key in KEY_ENV.items() if env.get(key)]


def select_vendor_config(env=None) -> VendorConfig:
    vendors = available_vendors(env)
    if not vendors:
        raise NoProviderKeyError(
            "No provider API key found. Set GOOGLE_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY."
        )
    if len(vendors) == 3:
        return VendorConfig("best-of-breed", MODERN_MATRIX, "gemini-1.5-flash", "claude-sonnet-4-6")
    chosen = next(v for v in PRIORITY if v in vendors)
    return SINGLE[chosen]
