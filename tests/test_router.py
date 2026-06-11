from src.router import Router, BUDGET_FALLBACK_MODEL
from src.models import Task

TASK_TYPES = ["extraction", "code", "reasoning", "writing", "review"]
COMPLEXITIES = ["low", "medium", "high"]


def make_task(task_type, complexity):
    return Task(id="t1", description="demo", task_type=task_type, complexity=complexity)


def test_reasoning_high_uses_sonnet():
    model = Router().select(make_task("reasoning", "high"), budget_remaining=1.0, budget_total=1.0)
    assert model == "claude-3-5-sonnet-20241022"


def test_extraction_low_uses_gemini():
    model = Router().select(make_task("extraction", "low"), budget_remaining=1.0, budget_total=1.0)
    assert model == "gemini-1.5-flash"


def test_tight_budget_downgrades_to_fallback():
    model = Router().select(make_task("code", "medium"), budget_remaining=0.1, budget_total=1.0)
    assert model == BUDGET_FALLBACK_MODEL


def test_healthy_budget_uses_matrix():
    model = Router().select(make_task("code", "medium"), budget_remaining=0.5, budget_total=1.0)
    assert model == "gpt-4o"


def test_all_combos_return_valid_model():
    router = Router()
    for task_type in TASK_TYPES:
        for complexity in COMPLEXITIES:
            model = router.select(make_task(task_type, complexity), budget_remaining=1.0, budget_total=1.0)
            assert isinstance(model, str) and model != ""
