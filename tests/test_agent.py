import pytest

from src.agent import Agent, ContextPacket
from src.providers.mock import MockProvider
from src.models import Task


def make_task(id="t1"):
    return Task(id=id, description="demo task", task_type="reasoning", complexity="low")


@pytest.mark.asyncio
async def test_agent_completes_and_returns_output():
    agent = Agent(MockProvider(), max_steps=5)
    result = await agent.run(ContextPacket(task=make_task()), model="mock-model")
    assert result.task_id == "t1"
    assert result.output != ""
    assert result.model_used == "mock-model"
    assert result.hit_step_guard is False
    assert result.steps_taken == 1


@pytest.mark.asyncio
async def test_agent_hits_step_guard():
    agent = Agent(MockProvider(finish_after_steps=2), max_steps=1)
    result = await agent.run(ContextPacket(task=make_task()), model="mock-model")
    assert result.hit_step_guard is True
    assert result.steps_taken == 1


@pytest.mark.asyncio
async def test_token_counts_match_provider():
    provider = MockProvider()
    agent = Agent(provider, max_steps=5)
    result = await agent.run(ContextPacket(task=make_task()), model="mock-model")
    assert result.tokens_in == provider.tokens_in_per_call
    assert result.tokens_out == provider.tokens_out_per_call
