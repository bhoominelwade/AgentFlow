from dataclasses import dataclass

from src.models import AgentResult, LedgerEntry

PRICING = {
    "claude-3-5-sonnet-20241022": {"in": 0.003, "out": 0.015},
    "claude-3-haiku-20240307": {"in": 0.00025, "out": 0.00125},
    "gpt-4o": {"in": 0.0025, "out": 0.01},
    "gpt-4o-mini": {"in": 0.00015, "out": 0.0006},
    "gemini-1.5-flash": {"in": 0.000075, "out": 0.0003},
}

COUNTERFACTUAL_MODEL = "claude-3-5-sonnet-20241022"


@dataclass
class LedgerSummary:
    total_actual_cost: float
    total_counterfactual_cost: float
    savings_usd: float
    savings_pct: float


class Ledger:
    def __init__(self):
        self.entries: list[LedgerEntry] = []

    def _cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        price = PRICING[model]
        return tokens_in / 1000 * price["in"] + tokens_out / 1000 * price["out"]

    def record(self, agent_result: AgentResult) -> LedgerEntry:
        entry = LedgerEntry(
            task_id=agent_result.task_id,
            model_used=agent_result.model_used,
            tokens_in=agent_result.tokens_in,
            tokens_out=agent_result.tokens_out,
            actual_cost_usd=self._cost(agent_result.model_used, agent_result.tokens_in, agent_result.tokens_out),
            counterfactual_cost_usd=self._cost(COUNTERFACTUAL_MODEL, agent_result.tokens_in, agent_result.tokens_out),
        )
        self.entries.append(entry)
        return entry

    def summary(self) -> LedgerSummary:
        total_actual = sum(e.actual_cost_usd for e in self.entries)
        total_counterfactual = sum(e.counterfactual_cost_usd for e in self.entries)
        savings = total_counterfactual - total_actual
        savings_pct = (savings / total_counterfactual * 100) if total_counterfactual > 0 else 0.0
        return LedgerSummary(total_actual, total_counterfactual, savings, savings_pct)
