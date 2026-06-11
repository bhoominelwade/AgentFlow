import pytest

from src.ledger import Ledger, PRICING, COUNTERFACTUAL_MODEL
from src.models import AgentResult


def make_result(task_id="t1", model="gemini-1.5-flash", tokens_in=1000, tokens_out=2000):
    return AgentResult(
        task_id=task_id,
        output="done",
        model_used=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        steps_taken=1,
        hit_step_guard=False,
    )


def expected_cost(model, tokens_in, tokens_out):
    p = PRICING[model]
    return tokens_in / 1000 * p["in"] + tokens_out / 1000 * p["out"]


def test_actual_cost_matches_formula():
    entry = Ledger().record(make_result(model="gemini-1.5-flash", tokens_in=1000, tokens_out=2000))
    assert entry.actual_cost_usd == pytest.approx(expected_cost("gemini-1.5-flash", 1000, 2000))


def test_counterfactual_is_higher_on_sonnet():
    entry = Ledger().record(make_result(model="gemini-1.5-flash", tokens_in=1000, tokens_out=2000))
    assert entry.counterfactual_cost_usd == pytest.approx(expected_cost(COUNTERFACTUAL_MODEL, 1000, 2000))
    assert entry.counterfactual_cost_usd > entry.actual_cost_usd


def test_savings_is_counterfactual_minus_actual():
    ledger = Ledger()
    ledger.record(make_result())
    s = ledger.summary()
    assert s.savings_usd == pytest.approx(s.total_counterfactual_cost - s.total_actual_cost)


def test_savings_pct_formula():
    ledger = Ledger()
    ledger.record(make_result())
    s = ledger.summary()
    assert s.savings_pct == pytest.approx(s.savings_usd / s.total_counterfactual_cost * 100)


def test_multiple_tasks_totals_sum():
    ledger = Ledger()
    ledger.record(make_result(task_id="t1", model="gemini-1.5-flash", tokens_in=1000, tokens_out=1000))
    ledger.record(make_result(task_id="t2", model="gpt-4o", tokens_in=500, tokens_out=500))
    s = ledger.summary()
    expected_actual = expected_cost("gemini-1.5-flash", 1000, 1000) + expected_cost("gpt-4o", 500, 500)
    expected_cf = expected_cost(COUNTERFACTUAL_MODEL, 1000, 1000) + expected_cost(COUNTERFACTUAL_MODEL, 500, 500)
    assert s.total_actual_cost == pytest.approx(expected_actual)
    assert s.total_counterfactual_cost == pytest.approx(expected_cf)
