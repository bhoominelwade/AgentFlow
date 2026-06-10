from fastapi import FastAPI

app = FastAPI(title="AgentFlow")


@app.get("/health")
def health():
    return {"status": "ok"}
