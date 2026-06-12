import asyncio

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
    return Scheduler(Agent(provider), router or Router(), Ledger(), retry_backoff=0)


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


class AlwaysFailProvider:
    async def complete(self, prompt, model=None):
        raise RuntimeError("simulated API error")


class FlakyProvider:
    def __init__(self, fail_times=1):
        self.fail_times = fail_times
        self.calls = 0

    async def complete(self, prompt, model=None):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("transient API error")
        return ProviderResponse(output="recovered", tokens_in=10, tokens_out=20, done=True)


class ConcurrencyProbeProvider:
    def __init__(self):
        self.current = 0
        self.peak = 0

    async def complete(self, prompt, model=None):
        self.current += 1
        self.peak = max(self.peak, self.current)
        await asyncio.sleep(0.02)
        self.current -= 1
        return ProviderResponse(output="x", tokens_in=10, tokens_out=20, done=True)


@pytest.mark.asyncio
async def test_failing_task_is_isolated_not_fatal():
    waves = resolve_waves(build_dag([make_task("t1")]))
    results = await make_scheduler(AlwaysFailProvider()).run(waves, budget=1.0)
    assert len(results) == 1
    assert results[0].error is not None
    assert results[0].output == ""


@pytest.mark.asyncio
async def test_retry_once_then_succeeds():
    results = await make_scheduler(FlakyProvider(fail_times=1)).run(
        resolve_waves(build_dag([make_task("t1")])), budget=1.0
    )
    assert results[0].error is None
    assert results[0].output == "recovered"


@pytest.mark.asyncio
async def test_concurrency_is_capped():
    provider = ConcurrencyProbeProvider()
    tasks = [make_task(f"t{i}") for i in range(6)]  # one wide wave, all independent
    waves = resolve_waves(build_dag(tasks))
    scheduler = Scheduler(Agent(provider), Router(), Ledger(), max_concurrency=2)
    await scheduler.run(waves, budget=1.0)
    assert provider.peak <= 2
