# AgentFlow — PLAN.md

## Build Strategy

Vertical slices — each slice is a working, testable piece of the system. Never build a full layer in isolation. At the end of every slice, something runs.

**Rule**: Don't start the next slice until the current one has a passing test.

---

## Slice 0 — Project Skeleton
**Goal**: Repo exists, runs, imports work.

```
agentflow/
├── src/
│   ├── __init__.py
│   ├── main.py          # FastAPI app with /health only
│   └── models.py        # All Pydantic schemas
├── tests/
│   └── __init__.py
├── .env.example
├── requirements.txt
└── README.md
```

Tasks:
- [ ] Create folder structure
- [ ] `requirements.txt`: fastapi, uvicorn, pydantic, anthropic, openai, google-generativeai, pytest, pytest-asyncio, python-dotenv
- [ ] `models.py`: Task, AgentResult, LedgerEntry, RunResult, RunRequest
- [ ] `main.py`: FastAPI app + `GET /health` returns `{ "status": "ok" }`
- [ ] Verify: `uvicorn src.main:app --reload` starts without errors

**Check**: `curl localhost:8000/health` returns 200

---

## Slice 1 — DAG
**Goal**: Given a list of tasks, build a DAG, detect cycles, return waves.

Files:
- [ ] `src/dag.py`
- [ ] `tests/test_dag.py`

Logic to implement:
- `build_dag(tasks: list[Task]) -> DAG`
- `detect_cycle(dag: DAG) -> list[str] | None` — returns cycle path or None
- `resolve_waves(dag: DAG) -> list[list[Task]]` — topological sort into waves

Tests:
- Linear chain `t1 → t2 → t3` → 3 waves of 1 each
- Two independent tasks → 1 wave of 2
- Diamond `t1 → t2, t1 → t3, t2 → t4, t3 → t4` → 3 waves
- Cycle `t1 → t2 → t1` → CycleError raised with path
- Single task, no dependencies → 1 wave

**Check**: `pytest tests/test_dag.py` all green

---

## Slice 2 — Mock Provider + Agent
**Goal**: An agent can call a provider and return a result. No real API keys needed yet.

Files:
- [ ] `src/providers/mock.py`
- [ ] `src/providers/__init__.py`
- [ ] `src/agent.py`
- [ ] `tests/test_agent.py`

Logic:
- `MockProvider.complete(prompt: str) -> ProviderResponse` — returns fixed response, tracks token counts
- `Agent.run(context_packet: ContextPacket, model: str) -> AgentResult`
- Step guard: if steps >= max_steps, break

Tests:
- Agent completes task and returns output
- Agent with max_steps=1 hits step guard, returns partial result, `hit_step_guard=True`
- Token counts in AgentResult match mock provider response

**Check**: `pytest tests/test_agent.py` all green

---

## Slice 3 — Router
**Goal**: Given task_type + complexity + budget state, return correct model.

Files:
- [ ] `src/router.py`
- [ ] `tests/test_router.py`

Logic:
- `Router.select(task: Task, budget_remaining: float, budget_total: float) -> str`
- Matrix lookup: `(task_type, complexity) → model`
- Budget check: if remaining/total < 0.20, return BUDGET_FALLBACK_MODEL

Tests:
- `(reasoning, high)` → `claude-3-5-sonnet`
- `(extraction, low)` → `gemini-1.5-flash`
- `(code, medium)` with 10% budget remaining → fallback model
- `(code, medium)` with 50% budget remaining → `gpt-4o`
- All 15 matrix combinations return a valid model string

**Check**: `pytest tests/test_router.py` all green

---

## Slice 4 — Ledger
**Goal**: Track cost per task, compute counterfactual, return savings summary.

Files:
- [ ] `src/ledger.py`
- [ ] `tests/test_ledger.py`

Logic:
- `Ledger.record(agent_result: AgentResult) -> LedgerEntry`
- `Ledger.summary() -> LedgerSummary` — totals + savings
- Pricing: use PRICING table from ARCH.md
- Counterfactual: recompute same tokens against Claude Sonnet pricing

Tests:
- Single task on gemini-flash → actual cost matches formula
- Same task counterfactual on claude-sonnet → higher cost
- Savings = counterfactual − actual
- Savings % = (savings / counterfactual) * 100
- Multiple tasks → totals sum correctly

**Check**: `pytest tests/test_ledger.py` all green

---

## Slice 5 — Scheduler (with mock)
**Goal**: Full wave execution using mock provider. No real API calls.

Files:
- [ ] `src/scheduler.py`
- [ ] `tests/test_scheduler.py`

Logic:
- `Scheduler.run(waves: list[list[Task]], budget: float) -> list[AgentResult]`
- Each wave: `asyncio.gather(*[agent.run(task) for task in wave])`
- Context packet: build from completed task outputs (direct parents only)
- Budget tracking: pass remaining budget to router before each task

Tests:
- 3 tasks in sequence — outputs chain correctly (t2 receives t1 output)
- 2 parallel tasks — both complete, order in results doesn't matter
- Budget exhausted at wave 2 — wave 3 tasks cancelled, partial result returned
- Context isolation — t3 only receives t2 output, not t1 output (if t1 not a direct parent)

**Check**: `pytest tests/test_scheduler.py` all green

---

## Slice 6 — Real Providers
**Goal**: Swap mock provider for real API calls. Requires API keys in .env.

Files:
- [ ] `src/providers/anthropic.py`
- [ ] `src/providers/openai.py`
- [ ] `src/providers/gemini.py`
- [ ] Update `src/providers/__init__.py` to route by model name

Logic:
- Each provider: `async def complete(prompt: str, model: str) -> ProviderResponse`
- Provider router: given model string, call correct provider
- Load API keys from env

Manual test (not in pytest suite — costs money):
- Call each provider once with a simple prompt
- Verify token counts return correctly

**Check**: `python -c "from src.providers import complete; import asyncio; asyncio.run(complete('say hello', 'gemini-1.5-flash'))"` returns response

---

## Slice 7 — Orchestrator
**Goal**: Given a goal string, call Claude and return a validated Task list.

Files:
- [ ] `src/orchestrator.py`
- [ ] `tests/test_orchestrator.py` (uses mock provider)

Logic:
- `Orchestrator.decompose(goal: str) -> list[Task]`
- Calls Claude with structured prompt
- Parses JSON response → validates against Task schema
- If invalid JSON: retry once with stricter prompt
- If still invalid: raise OrchestratorError

Tests (mock provider):
- Valid JSON response → returns list of Tasks
- Invalid JSON on first attempt, valid on retry → returns Tasks
- Invalid JSON on both attempts → raises OrchestratorError
- Empty task list → raises OrchestratorError

**Check**: `pytest tests/test_orchestrator.py` all green

---

## Slice 8 — Wire Everything + POST /run
**Goal**: Full end-to-end run via API.

Files:
- [ ] Update `src/main.py` — add `POST /run` and `GET /run/{run_id}`
- [ ] In-memory run store: `dict[str, RunResult]`
- [ ] `tests/test_integration.py` (uses mock provider end-to-end)

Logic:
- `POST /run`: orchestrate → dag → schedule → ledger → return RunResult
- `GET /run/{run_id}`: fetch from in-memory store

Integration test (mock):
- Post a goal → get RunResult with correct structure
- RunResult contains tasks, results, ledger, savings
- `GET /run/{run_id}` returns same result

**Check**: `pytest tests/test_integration.py` all green
**Check**: `uvicorn src.main:app --reload` + Postman/curl end-to-end with real keys

---

## Slice 9 — Polish
**Goal**: GitHub-ready.

- [ ] README.md final (already done)
- [ ] `.env.example` with all required keys
- [ ] All tests passing: `pytest tests/`
- [ ] Example script: `examples/research_report.py`
- [ ] Verify example runs end-to-end with real API keys
- [ ] Add cost output to example so savings are visible in terminal

---

## Build Order Summary

```
Slice 0 — Skeleton       (no dependencies)
Slice 1 — DAG            (needs models)
Slice 2 — Mock + Agent   (needs models)
Slice 3 — Router         (needs models)
Slice 4 — Ledger         (needs models, agent)
Slice 5 — Scheduler      (needs dag, agent, router, ledger)
Slice 6 — Real Providers (needs providers interface from slice 2)
Slice 7 — Orchestrator   (needs providers, models)
Slice 8 — Wire + API     (needs everything)
Slice 9 — Polish         (needs everything)
```

**Estimated time per slice**: 1–2 hours each if focused.
**Total**: ~2 focused days to a working, tested, GitHub-ready project.

---

## Definition of Done

- [ ] `pytest tests/` passes with 0 failures
- [ ] End-to-end run completes with real API keys
- [ ] Cost ledger shows savings in terminal output
- [ ] README on GitHub with example output
- [ ] Can explain every file in an interview without notes
