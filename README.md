# AgentFlow

A multi-agent workflow engine with DAG-based parallel execution and cost+task-aware model routing.

---

## The Problem

Most AI systems make one call to one model. That's fine for simple tasks. But for complex goals — research, analysis, code generation, report writing — a single model call is:

- **Expensive** — using Claude for a simple extraction task wastes money
- **Slow** — everything runs sequentially
- **Suboptimal** — no single model is best at everything

AgentFlow solves this by decomposing a goal into a DAG of tasks, running independent tasks in parallel, and routing each task to the best model based on **what kind of task it is** and **how complex it is**.

---

## How It Works

```
User Goal
    │
    ▼
Orchestrator (Claude)
  - Decomposes goal into tasks
  - Assigns task_type and complexity to each task
  - Builds dependency DAG
  - Detects cycles before execution starts
    │
    ▼
Scheduler
  - Resolves DAG into execution waves
  - Wave = all tasks with no unresolved dependencies
  - Runs each wave with asyncio.gather() (parallel)
  - Passes only direct dependency outputs to each agent
    │
    ▼
Router
  - Selects model per task based on task_type + complexity
  - Checks remaining budget before each call
  - Downgrades model if budget is tight
    │
    ▼
Worker Agents
  - Each agent gets: task description + dependency outputs only
  - Step guard caps max iterations
  - Returns structured result
    │
    ▼
Review Agent (Claude)
  - Aggregates all worker outputs
  - Final quality pass
    │
    ▼
Cost Ledger
  - Logs tokens in/out per model per task
  - Computes actual cost
  - Computes counterfactual cost (if everything ran on Claude)
  - Reports savings
```

---

## The Router (Core Differentiator)

The router picks the optimal model using two signals:

| Task Type | Low Complexity | Medium | High |
|---|---|---|---|
| extraction | gemini-flash | gemini-flash | gpt-4o-mini |
| code | gpt-4o-mini | gpt-4o | gpt-4o |
| reasoning | gpt-4o-mini | claude-haiku | claude |
| writing | gemini-flash | claude-haiku | claude |
| review | claude-haiku | claude | claude |

**Why these models:**
- **Claude** — best at reasoning, planning, long-form writing
- **GPT-4o** — best at code generation and structured output
- **Gemini Flash** — free tier, fast, good for simple extraction
- **Claude Haiku / GPT-4o-mini** — cheap versions for medium tasks

**Budget cap:** If total spend exceeds a set limit, the router automatically downgrades all remaining tasks to cheaper models. This is configurable.

---

## Stack

- **Language**: Python 3.11+
- **API layer**: FastAPI
- **Async**: asyncio (parallel agent execution)
- **LLM APIs**: Anthropic (Claude), OpenAI (GPT-4o), Google (Gemini)
- **No orchestration framework** — built from scratch

---

## Project Structure

```
agentflow/
├── src/
│   ├── main.py              # FastAPI entry point
│   ├── orchestrator.py      # Decomposes goal → tasks with type + complexity
│   ├── dag.py               # Builds DAG, detects cycles, resolves waves
│   ├── scheduler.py         # Runs waves in parallel via asyncio.gather
│   ├── agent.py             # Single agent runner with step guard
│   ├── router.py            # Model selection: task_type + complexity + budget
│   ├── providers/
│   │   ├── anthropic.py     # Claude API wrapper
│   │   ├── openai.py        # GPT-4o wrapper
│   │   ├── gemini.py        # Gemini API wrapper
│   │   └── mock.py          # Offline mock for tests
│   ├── ledger.py            # Cost tracking + counterfactual savings
│   └── models.py            # Pydantic schemas
├── tests/
│   ├── test_dag.py
│   ├── test_router.py
│   └── test_ledger.py
├── examples/
│   └── research_report.py   # End-to-end example
├── .env.example
├── requirements.txt
└── README.md
```

---

## Core Concepts

### DAG + Cycle Detection
Each task declares dependencies. The DAG is built from these edges. Before any execution:
- DFS-based cycle detection runs — if a cycle exists, execution stops with the cycle path in the error
- Tasks are grouped into waves — a wave is all tasks whose dependencies are already complete

### Parallel Execution
Each wave runs with `asyncio.gather()`. Tasks in the same wave have no dependencies on each other by definition, so they're safe to run concurrently.

### Context Isolation
Each agent's prompt contains only:
1. Its task description
2. Outputs of its **direct dependencies** only

No agent sees the full history. Keeps prompts tight, reduces hallucination surface.

### Step Guard
Each agent has a max step count (default: 5). If the agent loops without producing a result it halts and returns current state. Prevents runaway token spend.

### Cost Ledger
Tracks per task:
- Model used
- Tokens in / tokens out
- Actual cost (real provider pricing)
- Counterfactual cost (same tokens, all on Claude Sonnet)

Savings = counterfactual − actual

---

## Getting Started

### Prerequisites
- Python 3.11+
- API keys: Anthropic, OpenAI, Google AI

### Install

```bash
git clone https://github.com/bhoominelwade/agentflow
cd agentflow
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Fill in your API keys in .env
```

### Run

```bash
uvicorn src.main:app --reload
```

### API

```
POST /run
{
  "goal": "Research microservices vs monoliths and write a comparison report",
  "budget_usd": 0.10
}
```

### Run tests

```bash
pytest tests/
```

---

## Example Output

```
Goal: "Research microservices vs monoliths and write a comparison report"
Budget: $0.10

Wave 1 (parallel):
  ✓ extract-microservices-facts   [gemini-flash]   0.8s   $0.0001
  ✓ extract-monolith-facts        [gemini-flash]   0.9s   $0.0001

Wave 2 (parallel):
  ✓ analyze-tradeoffs             [claude-haiku]   1.1s   $0.0008
  ✓ find-use-cases                [gpt-4o-mini]    0.9s   $0.0004

Wave 3:
  ✓ write-report                  [claude]         1.8s   $0.0041

Review:
  ✓ review-final                  [claude-haiku]   0.7s   $0.0005

────────────────────────────────────────
Cost Ledger
  Actual cost:          $0.0060
  Counterfactual cost:  $0.0312  (all tasks on Claude Sonnet)
  Savings:              $0.0252  (81%)
  Budget remaining:     $0.0940
────────────────────────────────────────
```

---



