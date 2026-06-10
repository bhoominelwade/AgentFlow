# AgentFlow — SPEC.md

## Glossary (ubiquitous language)

Use these exact terms in code, docs, and conversation. Never substitute synonyms.

| Term | Definition |
|---|---|
| **Goal** | The natural language input from the user describing what they want accomplished |
| **Task** | A single unit of work with a type, complexity, and list of dependency task IDs |
| **Task Type** | The category of work: `extraction`, `code`, `reasoning`, `writing`, `review` |
| **Complexity** | Estimated difficulty of a task: `low`, `medium`, `high` |
| **DAG** | Directed Acyclic Graph — the dependency graph of all tasks for a given run |
| **Wave** | A set of tasks with no unresolved dependencies — safe to run in parallel |
| **Agent** | The process that executes a single task using an assigned model |
| **Router** | The component that selects a model given task_type + complexity + remaining budget |
| **Provider** | A wrapper around one LLM API (Anthropic, OpenAI, Google) |
| **Ledger** | The component that tracks token usage, actual cost, and counterfactual cost per task |
| **Run** | One full execution: goal → orchestration → DAG → all waves → review → ledger summary |
| **Counterfactual Cost** | What the run would have cost if every task used Claude Sonnet |
| **Budget** | User-specified max spend in USD for a run |
| **Step Guard** | A per-agent limit on max reasoning iterations to prevent infinite loops |
| **Context Packet** | The input passed to an agent: task description + direct dependency outputs only |

---

## Problem Statement

LLM applications typically make one call to one model. For complex multi-step goals this is:

- **Expensive** — premium models used for simple subtasks
- **Slow** — steps run sequentially even when independent
- **Suboptimal** — no single model excels at all task types

AgentFlow solves this with a pipeline that decomposes goals into tasks, executes independent tasks in parallel, and routes each task to the best model based on task type and complexity — while staying within a user-defined budget.

---

## Functional Requirements

### FR1 — Goal Decomposition
- System accepts a natural language goal and an optional budget (USD)
- An orchestrator LLM decomposes the goal into 2–10 tasks
- Each task has: `id`, `description`, `task_type`, `complexity`, `dependencies[]`
- Orchestrator output must be valid structured JSON (enforced by schema)

### FR2 — DAG Construction
- Build a DAG from task dependency declarations
- Detect cycles before execution — if cycle exists, return error with cycle path
- Resolve DAG into ordered waves for execution

### FR3 — Parallel Execution
- Tasks within the same wave execute concurrently via `asyncio.gather()`
- A task only starts when all its dependencies have completed
- Each agent receives only its direct dependency outputs (context isolation)

### FR4 — Model Routing
- Router selects model based on: `task_type` × `complexity` matrix
- Before each task, check remaining budget
- If budget is tight (< 20% remaining), downgrade to cheapest viable model
- Router is configurable — matrix can be overridden via config

### FR5 — Cost Tracking
- Track tokens in/out per task per model
- Compute actual cost using current provider pricing
- Compute counterfactual cost (same tokens, all on Claude Sonnet 3.5)
- Report savings = counterfactual − actual, as USD and percentage

### FR6 — Step Guard
- Each agent has a configurable max_steps (default: 5)
- If agent exceeds max_steps without producing output, halt and return partial result
- Log step guard trigger as a warning

### FR7 — FastAPI Interface
- `POST /run` — accepts goal + budget, returns full run result
- `GET /run/{run_id}` — fetch a previous run result
- `GET /health` — liveness check

---

## Non-Functional Requirements

- A run with 5 parallel tasks should complete faster than the same tasks run sequentially
- No local model dependencies — all inference via APIs
- All provider keys loaded from environment variables, never hardcoded
- Full run result stored in memory (SQLite stretch goal)

---

## Edge Cases

| Scenario | Expected Behaviour |
|---|---|
| Goal produces only 1 task | Single wave, single agent, no parallelism |
| DAG has a cycle | Return 400 error with cycle path before any LLM calls |
| Budget exhausted mid-run | Halt remaining tasks, return partial result with ledger |
| Provider API error | Retry once, then mark task as failed, continue other tasks |
| Agent hits step guard | Return partial result, log warning, continue DAG |
| Orchestrator returns invalid JSON | Retry decomposition once with stricter prompt |
| All tasks same wave | All run in parallel, no sequential dependency |

---

## Out of Scope (v1)

- Streaming per-agent output
- Web UI
- Persistent storage (SQLite is a stretch goal)
- Human-in-the-loop approval between waves
- Custom model per task (user override)
