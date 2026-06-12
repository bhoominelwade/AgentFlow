import pytest
from fastapi import HTTPException

import src.main as main
from src.engine import run_goal
from src.orchestrator import Orchestrator
from src.scheduler import Scheduler
from src.agent import Agent
from src.router import Router
from src.ledger import Ledger
from src.providers import ProviderResponse
from src.providers.mock import MockProvider

TASKS_JSON = (
    '[{"id":"t1","description":"extract facts","task_type":"extraction","complexity":"low","dependencies":[]},'
    '{"id":"t2","description":"write report","task_type":"writing","complexity":"high","dependencies":["t1"]}]'
)


class ScriptedProvider:
    def __init__(self, output):
        self.output = output

    async def complete(self, prompt, model=None):
        return ProviderResponse(output=self.output, tokens_in=100, tokens_out=200, done=True)


def build_run(run_id):
    orchestrator = Orchestrator(ScriptedProvider(TASKS_JSON))
    scheduler = Scheduler(Agent(MockProvider()), Router(), Ledger())
    return run_goal(run_id, "make a report", 1.0, orchestrator, scheduler)


@pytest.mark.asyncio
async def test_full_run_produces_runresult():
    result = await build_run("run-1")
    assert result.run_id == "run-1"
    assert {t.id for t in result.tasks} == {"t1", "t2"}
    assert {r.task_id for r in result.results} == {"t1", "t2"}
    assert len(result.ledger) == 2
    assert result.total_counterfactual_cost >= result.total_actual_cost
    assert result.savings_usd == pytest.approx(result.total_counterfactual_cost - result.total_actual_cost)


@pytest.mark.asyncio
async def test_store_round_trip():
    result = await build_run("run-2")
    main.RUNS["run-2"] = result
    assert main.get_run("run-2") is result


def test_get_run_missing_raises():
    with pytest.raises(HTTPException):
        main.get_run("does-not-exist")
