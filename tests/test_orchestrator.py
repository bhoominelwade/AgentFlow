import pytest

from src.orchestrator import Orchestrator, OrchestratorError
from src.providers import ProviderResponse

VALID = '[{"id": "t1", "description": "do x", "task_type": "reasoning", "complexity": "low", "dependencies": []}]'


class ScriptedProvider:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = 0

    async def complete(self, prompt, model=None):
        out = self.outputs[min(self.calls, len(self.outputs) - 1)]
        self.calls += 1
        return ProviderResponse(output=out, tokens_in=10, tokens_out=20, done=True)


@pytest.mark.asyncio
async def test_valid_json_returns_tasks():
    tasks = await Orchestrator(ScriptedProvider([VALID])).decompose("build a thing")
    assert len(tasks) == 1
    assert tasks[0].id == "t1"
    assert tasks[0].task_type == "reasoning"


@pytest.mark.asyncio
async def test_invalid_then_valid_retries():
    provider = ScriptedProvider(["not json at all", VALID])
    tasks = await Orchestrator(provider).decompose("build a thing")
    assert len(tasks) == 1
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_invalid_twice_raises():
    with pytest.raises(OrchestratorError):
        await Orchestrator(ScriptedProvider(["nope", "still nope"])).decompose("build a thing")


@pytest.mark.asyncio
async def test_empty_task_list_raises():
    with pytest.raises(OrchestratorError):
        await Orchestrator(ScriptedProvider(["[]"])).decompose("build a thing")
