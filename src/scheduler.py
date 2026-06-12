import asyncio

from src.agent import Agent, ContextPacket
from src.ledger import Ledger
from src.models import AgentResult, Task
from src.router import Router


class Scheduler:
    def __init__(self, agent: Agent, router: Router, ledger: Ledger,
                 max_concurrency: int = 8, max_retries: int = 1):
        self.agent = agent
        self.router = router
        self.ledger = ledger
        self.max_retries = max_retries
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def _run_task(self, packet: ContextPacket, model: str) -> AgentResult:
        async with self._semaphore:
            last_error: Exception | None = None
            for _ in range(self.max_retries + 1):
                try:
                    return await self.agent.run(packet, model)
                except Exception as exc:
                    last_error = exc
            return AgentResult(
                task_id=packet.task.id,
                output="",
                model_used=model,
                tokens_in=0,
                tokens_out=0,
                steps_taken=0,
                hit_step_guard=False,
                error=str(last_error),
            )

    async def run(self, waves: list[list[Task]], budget: float) -> list[AgentResult]:
        remaining = budget
        results: dict[str, AgentResult] = {}
        for wave in waves:
            if remaining <= 0:
                break
            coros = []
            for task in wave:
                parents = {dep: results[dep].output for dep in task.dependencies if dep in results}
                packet = ContextPacket(task=task, dependency_outputs=parents)
                model = self.router.select(task, remaining, budget)
                coros.append(self._run_task(packet, model))
            for result in await asyncio.gather(*coros):
                results[result.task_id] = result
                remaining -= self.ledger.record(result).actual_cost_usd
        return list(results.values())
