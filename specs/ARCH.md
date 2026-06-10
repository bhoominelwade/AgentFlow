# AgentFlow — ARCH.md

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT                                  │
│              POST /run  { goal, budget_usd }                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI LAYER                              │
│                        main.py                                  │
│   - Validates request schema (Pydantic)                         │
│   - Generates run_id                                            │
│   - Delegates to Orchestrator                                   │
│   - Returns RunResult                                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                               │
│                     orchestrator.py                             │
│   - Calls Claude with goal → returns Task[]                     │
│   - Validates JSON schema (retries once if invalid)             │
│   - Passes Task[] to DAG builder                                │
└───────────────────────────┬─────────────────────────────────────┘
                            │  Task[]
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         DAG                                     │
│                        dag.py                                   │
│   - Builds adjacency list from dependencies                     │
│   - DFS cycle detection → raises CycleError if found           │
│   - Topological sort → resolves Wave[]                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │  Wave[]
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       SCHEDULER                                 │
│                      scheduler.py                               │
│   - Iterates waves in order                                     │
│   - For each wave: asyncio.gather(*[run_agent(task)...])        │
│   - Builds context_packet per task from completed outputs       │
│   - Stores task results as they complete                        │
└──────────┬──────────────────────────────────────────────────────┘
           │  context_packet per task
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                        ROUTER                                   │
│                       router.py                                 │
│   - Lookup: (task_type, complexity) → model_id                  │
│   - Budget check: if remaining < 20%, downgrade                 │
│   - Returns: model_id + provider_name                           │
└──────────┬──────────────────────────────────────────────────────┘
           │  model assignment
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                         AGENT                                   │
│                        agent.py                                 │
│   - Receives: context_packet + model assignment                 │
│   - Calls provider with built prompt                            │
│   - Step guard: max 5 iterations                                │
│   - Returns: AgentResult { output, tokens_in, tokens_out }      │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ├──────────────────────────────────────┐
           │                                      │
           ▼                                      ▼
┌─────────────────────┐              ┌────────────────────────────┐
│     PROVIDERS       │              │          LEDGER             │
│   providers/        │              │         ledger.py           │
│                     │              │                             │
│  anthropic.py       │              │  - Records per-task entry   │
│  openai.py          │              │  - actual_cost calculation  │
│  gemini.py          │              │  - counterfactual_cost calc │
│  mock.py            │              │  - savings summary          │
└─────────────────────┘              └────────────────────────────┘
```

---

## Data Flow — Single Run

```
1. POST /run  →  { goal: "...", budget_usd: 0.10 }

2. Orchestrator calls Claude:
   Prompt: "Decompose this goal into tasks. Return JSON."
   Response: [
     { id: "t1", description: "...", task_type: "extraction", complexity: "low", dependencies: [] },
     { id: "t2", description: "...", task_type: "reasoning", complexity: "high", dependencies: ["t1"] },
     { id: "t3", description: "...", task_type: "writing",   complexity: "medium", dependencies: ["t2"] }
   ]

3. DAG builds graph:
   t1 → t2 → t3
   No cycles detected.
   Waves: [ [t1], [t2], [t3] ]

4. Scheduler executes:
   Wave 1: asyncio.gather(agent(t1))       → result_t1
   Wave 2: asyncio.gather(agent(t2))       → result_t2  (context: result_t1)
   Wave 3: asyncio.gather(agent(t3))       → result_t3  (context: result_t2)

5. Router assigns per task:
   t1: (extraction, low)   → gemini-flash
   t2: (reasoning, high)   → claude-sonnet
   t3: (writing, medium)   → claude-haiku

6. Ledger computes:
   Actual:          $0.0031
   Counterfactual:  $0.0187
   Savings:         $0.0156 (83%)

7. POST /run returns RunResult
```

---

## Component Contracts

### Task (models.py)
```python
class Task(BaseModel):
    id: str
    description: str
    task_type: Literal["extraction", "code", "reasoning", "writing", "review"]
    complexity: Literal["low", "medium", "high"]
    dependencies: list[str] = []
```

### AgentResult (models.py)
```python
class AgentResult(BaseModel):
    task_id: str
    output: str
    model_used: str
    tokens_in: int
    tokens_out: int
    steps_taken: int
    hit_step_guard: bool
```

### LedgerEntry (models.py)
```python
class LedgerEntry(BaseModel):
    task_id: str
    model_used: str
    tokens_in: int
    tokens_out: int
    actual_cost_usd: float
    counterfactual_cost_usd: float
```

### RunResult (models.py)
```python
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
```

---

## Router Matrix

```python
ROUTING_MATRIX = {
    ("extraction", "low"):    "gemini-1.5-flash",
    ("extraction", "medium"): "gemini-1.5-flash",
    ("extraction", "high"):   "gpt-4o-mini",

    ("code", "low"):          "gpt-4o-mini",
    ("code", "medium"):       "gpt-4o",
    ("code", "high"):         "gpt-4o",

    ("reasoning", "low"):     "gpt-4o-mini",
    ("reasoning", "medium"):  "claude-3-haiku-20240307",
    ("reasoning", "high"):    "claude-3-5-sonnet-20241022",

    ("writing", "low"):       "gemini-1.5-flash",
    ("writing", "medium"):    "claude-3-haiku-20240307",
    ("writing", "high"):      "claude-3-5-sonnet-20241022",

    ("review", "low"):        "claude-3-haiku-20240307",
    ("review", "medium"):     "claude-3-haiku-20240307",
    ("review", "high"):       "claude-3-5-sonnet-20241022",
}

BUDGET_FALLBACK_MODEL = "gemini-1.5-flash"
BUDGET_THRESHOLD_PCT = 0.20  # downgrade when < 20% budget remaining
```

---

## Pricing Table (for Ledger)

```python
# USD per 1000 tokens
PRICING = {
    "claude-3-5-sonnet-20241022": {"in": 0.003,   "out": 0.015},
    "claude-3-haiku-20240307":    {"in": 0.00025,  "out": 0.00125},
    "gpt-4o":                     {"in": 0.0025,   "out": 0.01},
    "gpt-4o-mini":                {"in": 0.00015,  "out": 0.0006},
    "gemini-1.5-flash":           {"in": 0.000075, "out": 0.0003},
}

# Counterfactual baseline
COUNTERFACTUAL_MODEL = "claude-3-5-sonnet-20241022"
```

---

## Key Design Decisions

### ADR-1: asyncio over threading for parallelism
**Decision**: Use `asyncio.gather()` for parallel agent execution.
**Reason**: LLM API calls are I/O bound, not CPU bound. asyncio handles concurrent I/O efficiently without the overhead and complexity of threads. All major Python LLM SDKs support async natively.

### ADR-2: No orchestration framework (LangChain, CrewAI etc.)
**Decision**: Build DAG, routing, and agent loop from scratch.
**Reason**: Portfolio project — must be able to explain every component. Frameworks hide the complexity we want to demonstrate. Also avoids framework lock-in and version churn.

### ADR-3: Context isolation per agent
**Decision**: Each agent receives only its task + direct parent outputs.
**Reason**: Passing full run history to every agent bloats token usage, increases cost, and introduces noise. Isolation keeps prompts tight and agents focused.

### ADR-4: Structured JSON from orchestrator
**Decision**: Orchestrator must return valid JSON matching Task schema.
**Reason**: Downstream components (DAG, router) require typed task objects. Unstructured text decomposition would require fragile parsing. One retry with stricter prompt handles edge cases.

### ADR-5: Budget downgrade at 20% threshold
**Decision**: Switch to fallback model when < 20% budget remains.
**Reason**: Hard stop at 0% risks partial results mid-wave. 20% buffer ensures at least one more wave can complete at reduced cost before exhaustion.

---

## What This Is NOT

- Not a replacement for LangGraph or CrewAI in production
- Not a general-purpose agent framework
- Not a streaming system (v1)
- Not persistent (v1 — in-memory only)
