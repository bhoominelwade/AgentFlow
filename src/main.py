import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

import src.providers as providers
from src.agent import Agent
from src.engine import run_goal
from src.ledger import Ledger
from src.models import RunRequest, RunResult
from src.orchestrator import Orchestrator
from src.router import Router
from src.scheduler import Scheduler
from src.vendors import select_vendor_config

load_dotenv()

app = FastAPI(title="AgentFlow")
RUNS: dict[str, RunResult] = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run")
async def post_run(request: RunRequest) -> RunResult:
    run_id = str(uuid.uuid4())
    config = select_vendor_config()
    orchestrator = Orchestrator(providers, model=config.orchestrator_model)
    scheduler = Scheduler(
        Agent(providers),
        Router(matrix=config.matrix, fallback_model=config.fallback_model),
        Ledger(),
    )
    result = await run_goal(run_id, request.goal, request.budget_usd, orchestrator, scheduler)
    RUNS[run_id] = result
    return result


@app.get("/run/{run_id}")
def get_run(run_id: str) -> RunResult:
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="run not found")
    return RUNS[run_id]
