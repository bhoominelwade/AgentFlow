import asyncio

from src.agent import Agent, ContextPacket
from src.ledger import Ledger
from src.models import AgentResult, Task
from src.router import Router


class Scheduler:
    def __init__(self, agent: Agent, router: Router, ledger: Ledger):
        self.agent = agent
        self.router = router
        self.ledger = ledger

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
                coros.append(self.agent.run(packet, model))
            for result in await asyncio.gather(*coros):
                results[result.task_id] = result
                remaining -= self.ledger.record(result).actual_cost_usd
        return list(results.values())
