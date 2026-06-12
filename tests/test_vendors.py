import pytest

from src.vendors import (
    GEMINI_MATRIX, ANTHROPIC_MATRIX, OPENAI_MATRIX, MODERN_MATRIX,
    available_vendors, select_vendor_config, NoProviderKeyError,
    TASK_TYPES, COMPLEXITIES,
)


def test_vendor_matrices_cover_all_15_combos():
    for matrix in (GEMINI_MATRIX, ANTHROPIC_MATRIX, OPENAI_MATRIX, MODERN_MATRIX):
        assert len(matrix) == 15
        for task_type in TASK_TYPES:
            for complexity in COMPLEXITIES:
                model = matrix[(task_type, complexity)]
                assert isinstance(model, str) and model != ""


def test_single_gemini_key_routes_within_gemini():
    cfg = select_vendor_config({"GOOGLE_API_KEY": "x"})
    assert cfg.vendor == "gemini"
    assert cfg.matrix is GEMINI_MATRIX
    assert cfg.fallback_model == "gemini-1.5-flash"


def test_single_anthropic_key_routes_within_anthropic():
    cfg = select_vendor_config({"ANTHROPIC_API_KEY": "x"})
    assert cfg.vendor == "anthropic"
    assert cfg.orchestrator_model == "claude-sonnet-4-6"


def test_two_keys_pick_higher_priority_single_vendor():
    cfg = select_vendor_config({"GOOGLE_API_KEY": "x", "OPENAI_API_KEY": "y"})
    assert cfg.vendor == "openai"


def test_all_three_keys_use_best_of_breed():
    cfg = select_vendor_config(
        {"GOOGLE_API_KEY": "x", "ANTHROPIC_API_KEY": "y", "OPENAI_API_KEY": "z"}
    )
    assert cfg.vendor == "best-of-breed"
    assert cfg.matrix is MODERN_MATRIX


def test_no_key_raises():
    with pytest.raises(NoProviderKeyError):
        select_vendor_config({})


def test_available_vendors_detects_present_keys():
    found = available_vendors({"GOOGLE_API_KEY": "x", "ANTHROPIC_API_KEY": "y"})
    assert set(found) == {"gemini", "anthropic"}
