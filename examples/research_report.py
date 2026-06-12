import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

import src.providers as providers
from src.agent import Agent
from src.engine import run_goal
from src.ledger import Ledger
from src.orchestrator import Orchestrator
from src.router import Router
from src.scheduler import Scheduler
from src.vendors import select_vendor_config

GOAL = "Research the pros and cons of microservices vs a monolith, then write a short comparison."
BUDGET = 0.10


async def main():
    load_dotenv()
    config = select_vendor_config()
    print(f"Vendor: {config.vendor}   Orchestrator: {config.orchestrator_model}\n")

    orchestrator = Orchestrator(providers, model=config.orchestrator_model)
    scheduler = Scheduler(
        Agent(providers),
        Router(matrix=config.matrix, fallback_model=config.fallback_model),
        Ledger(),
    )
    result = await run_goal("example-run", GOAL, BUDGET, orchestrator, scheduler)

    print(f"Goal: {result.goal}\n")
    print("Tasks:")
    for entry in result.ledger:
        print(f"  {entry.task_id:10} {entry.model_used:22} ${entry.actual_cost_usd:.6f}")
    print()
    print(f"  Actual cost:          ${result.total_actual_cost:.6f}")
    print(f"  Counterfactual cost:  ${result.total_counterfactual_cost:.6f}  (all-premium baseline)")
    print(f"  Savings:              ${result.savings_usd:.6f}  ({result.savings_pct:.1f}%)")


if __name__ == "__main__":
    asyncio.run(main())
