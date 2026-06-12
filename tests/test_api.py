from fastapi.testclient import TestClient

import src.main as main
from src.dag import CycleError
from src.orchestrator import OrchestratorError
from src.vendors import NoProviderKeyError, VendorConfig, GEMINI_MATRIX

client = TestClient(main.app)


def _gemini_cfg():
    return VendorConfig("gemini", GEMINI_MATRIX, "gemini-1.5-flash", "gemini-1.5-pro")


def test_health_ok():
    assert client.get("/health").json() == {"status": "ok"}


def test_missing_run_returns_404():
    assert client.get("/run/does-not-exist").status_code == 404


def test_no_provider_key_returns_503(monkeypatch):
    def boom(*args, **kwargs):
        raise NoProviderKeyError("no key")

    monkeypatch.setattr(main, "select_vendor_config", boom)
    response = client.post("/run", json={"goal": "x", "budget_usd": 0.1})
    assert response.status_code == 503


def test_cycle_returns_400_with_path(monkeypatch):
    monkeypatch.setattr(main, "select_vendor_config", lambda *a, **k: _gemini_cfg())

    async def cyclic(*args, **kwargs):
        raise CycleError(["t1", "t2", "t1"])

    monkeypatch.setattr(main, "run_goal", cyclic)
    response = client.post("/run", json={"goal": "x", "budget_usd": 0.1})
    assert response.status_code == 400
    assert "t1" in str(response.json())


def test_bad_decomposition_returns_400(monkeypatch):
    monkeypatch.setattr(main, "select_vendor_config", lambda *a, **k: _gemini_cfg())

    async def bad(*args, **kwargs):
        raise OrchestratorError("invalid JSON twice")

    monkeypatch.setattr(main, "run_goal", bad)
    response = client.post("/run", json={"goal": "x", "budget_usd": 0.1})
    assert response.status_code == 400
