import pytest

from src.scheduler import Scheduler
from src.agent import Agent
from src.router import Router
from src.ledger import Ledger
from src.dag import build_dag, resolve_waves
from src.providers import ProviderResponse
from src.models import Task


class RecordingProvider:
    def __init__(self, tokens_in=1000, tokens_out=1000):
        self.prompts = []
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out

    async def complete(self, prompt, model=None):
        self.prompts.append(prompt)
        first_line = prompt.splitlines()[0] if prompt else ""
        return ProviderResponse(
            output=f"OUTPUT[{first_line}]",
            tokens_in=self.tokens_in,
            tokens_out=self.tokens_out,
            done=True,
        )


class FixedRouter:
    def __init__(self, model="gpt-4o"):
        self.model = model

    def select(self, task, budget_remaining, budget_total):
        return self.model


def make_task(id, deps=None):
    return Task(id=id, description=f"task {id}", task_type="reasoning", complexity="low", dependencies=deps or [])


def prompt_for(provider, desc):
    return next(p for p in provider.prompts if p.splitlines()[0] == desc)


def make_scheduler(provider, router=None):
    return Scheduler(Agent(provider), router or Router(), Ledger())


@pytest.mark.asyncio
async def test_sequential_outputs_chain():
    provider = RecordingProvider()
    tasks = [make_task("t1"), make_task("t2", ["t1"]), make_task("t3", ["t2"])]
    waves = resolve_waves(build_dag(tasks))
    results = await make_scheduler(provider).run(waves, budget=1.0)
    assert {r.task_id for r in results} == {"t1", "t2", "t3"}
    assert "OUTPUT[task t1]" in prompt_for(provider, "task t2")


@pytest.mark.asyncio
async def test_parallel_tasks_all_complete():
    provider = RecordingProvider()
    tasks = [make_task("t1"), make_task("t2")]
    waves = resolve_waves(build_dag(tasks))
    results = await make_scheduler(provider).run(waves, budget=1.0)
    assert {r.task_id for r in results} == {"t1", "t2"}
    assert all(r.output != "" for r in results)


@pytest.mark.asyncio
async def test_context_isolation_direct_parents_only():
    provider = RecordingProvider()
    tasks = [make_task("t1"), make_task("t2", ["t1"]), make_task("t3", ["t2"])]
    waves = resolve_waves(build_dag(tasks))
    await make_scheduler(provider).run(waves, budget=1.0)
    t3_prompt = prompt_for(provider, "task t3")
    assert "OUTPUT[task t2]" in t3_prompt
    assert "OUTPUT[task t1]" not in t3_prompt


@pytest.mark.asyncio
async def test_budget_halt_cancels_later_waves():
    provider = RecordingProvider(tokens_in=1000, tokens_out=1000)  # gpt-4o -> 0.0125/task
    tasks = [make_task("t1"), make_task("t2", ["t1"]), make_task("t3", ["t2"])]
    waves = resolve_waves(build_dag(tasks))
    scheduler = make_scheduler(provider, router=FixedRouter("gpt-4o"))
    results = await scheduler.run(waves, budget=0.02)  # starts wave 1 & 2, not the 3rd
    ids = {r.task_id for r in results}
    assert ids == {"t1", "t2"}
