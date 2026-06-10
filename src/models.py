from typing import Literal

from pydantic import BaseModel

TaskType = Literal["extraction", "code", "reasoning", "writing", "review"]
Complexity = Literal["low", "medium", "high"]


class Task(BaseModel):
    id: str
    description: str
    task_type: TaskType
    complexity: Complexity
    dependencies: list[str] = []


class AgentResult(BaseModel):
    task_id: str
    output: str
    model_used: str
    tokens_in: int
    tokens_out: int
    steps_taken: int
    hit_step_guard: bool


class LedgerEntry(BaseModel):
    task_id: str
    model_used: str
    tokens_in: int
    tokens_out: int
    actual_cost_usd: float
    counterfactual_cost_usd: float


class RunRequest(BaseModel):
    goal: str
    budget_usd: float = 0.10


class RunResult(BaseModel):
    run_id: str
    goal: str
    tasks: list[Task]
    results: list[AgentResult]
    ledger: list[LedgerEntry]
    total_actual_cost: float
    total_counterfactual_cost: float
    savings_usd: float
    savings_pct: float
