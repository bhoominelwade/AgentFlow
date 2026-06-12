import json

from pydantic import ValidationError

from src.models import Task


class OrchestratorError(Exception):
    pass


class Orchestrator:
    def __init__(self, provider, model: str = "claude-3-5-sonnet-20241022"):
        self.provider = provider
        self.model = model

    def _build_prompt(self, goal: str, strict: bool = False) -> str:
        base = (
            "Decompose this goal into 2-10 tasks. Return ONLY a JSON array of objects with keys: "
            "id, description, task_type (extraction|code|reasoning|writing|review), "
            "complexity (low|medium|high), dependencies (list of task ids). "
            f"Goal: {goal}"
        )
        if strict:
            return "Return ONLY valid JSON. No prose, no markdown fences. " + base
        return base

    async def _attempt(self, prompt: str) -> list[Task] | None:
        response = await self.provider.complete(prompt, self.model)
        text = response.output.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data = json.loads(text)
            return [Task(**item) for item in data]
        except (json.JSONDecodeError, ValidationError, TypeError):
            return None

    async def decompose(self, goal: str) -> list[Task]:
        tasks = await self._attempt(self._build_prompt(goal))
        if tasks is None:
            tasks = await self._attempt(self._build_prompt(goal, strict=True))
        if not tasks:
            raise OrchestratorError(f"Could not decompose goal into tasks: {goal!r}")
        return tasks
