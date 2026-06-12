from src.dag import build_dag, resolve_waves
from src.models import RunResult


async def run_goal(run_id, goal, budget, orchestrator, scheduler) -> RunResult:
    tasks = await orchestrator.decompose(goal)
    waves = resolve_waves(build_dag(tasks))
    results = await scheduler.run(waves, budget)
    summary = scheduler.ledger.summary()
    return RunResult(
        run_id=run_id,
        goal=goal,
        tasks=tasks,
        results=results,
        ledger=scheduler.ledger.entries,
        total_actual_cost=summary.total_actual_cost,
        total_counterfactual_cost=summary.total_counterfactual_cost,
        savings_usd=summary.savings_usd,
        savings_pct=summary.savings_pct,
    )
