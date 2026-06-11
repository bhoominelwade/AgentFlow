from src.models import Task

ROUTING_MATRIX = {
    ("extraction", "low"): "gemini-1.5-flash",
    ("extraction", "medium"): "gemini-1.5-flash",
    ("extraction", "high"): "gpt-4o-mini",
    ("code", "low"): "gpt-4o-mini",
    ("code", "medium"): "gpt-4o",
    ("code", "high"): "gpt-4o",
    ("reasoning", "low"): "gpt-4o-mini",
    ("reasoning", "medium"): "claude-3-haiku-20240307",
    ("reasoning", "high"): "claude-3-5-sonnet-20241022",
    ("writing", "low"): "gemini-1.5-flash",
    ("writing", "medium"): "claude-3-haiku-20240307",
    ("writing", "high"): "claude-3-5-sonnet-20241022",
    ("review", "low"): "claude-3-haiku-20240307",
    ("review", "medium"): "claude-3-haiku-20240307",
    ("review", "high"): "claude-3-5-sonnet-20241022",
}

BUDGET_FALLBACK_MODEL = "gemini-1.5-flash"
BUDGET_THRESHOLD_PCT = 0.20


class Router:
    def __init__(self, matrix=ROUTING_MATRIX, fallback_model=BUDGET_FALLBACK_MODEL,
                 threshold=BUDGET_THRESHOLD_PCT):
        self.matrix = matrix
        self.fallback_model = fallback_model
        self.threshold = threshold

    def select(self, task: Task, budget_remaining: float, budget_total: float) -> str:
        if budget_total <= 0 or budget_remaining / budget_total < self.threshold:
            return self.fallback_model
        return self.matrix[(task.task_type, task.complexity)]
