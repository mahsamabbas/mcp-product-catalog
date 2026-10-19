from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main_module
from app.catalog.db import init_db
from app.chat import ChatServiceError
from app.config import Settings
from app.main import create_app
from app.schemas import ChatResponse, ToolTraceEvent


def test_health_reports_injected_service_status(tmp_path: Path):
    app = create_app(testing=True)
    app.state["catalog_db_path"] = str(tmp_path / "catalog.db")
    init_db(app.state["catalog_db_path"])
    app.state["mcp"].ready = True

    async def healthy():
        return True

    app.state["ollama"].healthy = healthy

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"ollama": True, "mcp": True, "catalog_count": 29}


def test_catalog_summary_returns_category_counts_and_sample_skus(tmp_path: Path):
    app = create_app(testing=True)
    app.state["catalog_db_path"] = str(tmp_path / "catalog.db")
    init_db(app.state["catalog_db_path"])

    response = TestClient(app).get("/catalog/summary")

    assert response.status_code == 200
    assert response.json() == {
        "product_count": 29,
        "categories": {
            "cables": 4,
            "chargers": 4,
            "headphones": 5,
            "keyboards": 4,
            "laptops": 4,
            "mice": 4,
            "monitors": 4,
        },
        "sample_skus": ["CP-1001", "CP-1002", "CP-1003"],
    }


def test_chat_normal():
    app = create_app(testing=True)
    received = {}

    async def fake_run_chat(**kwargs):
        received.update(kwargs)
        return ChatResponse(
            answer="Found VoltBuds.",
            tool_trace=[
                ToolTraceEvent(
                    name="search_products",
                    args={"query": "earbuds"},
                    result={"count": 1},
                    ms=5,
                    ok=True,
                )
            ],
        )

    app.state["run_chat"] = fake_run_chat

    response = TestClient(app).post(
        "/chat",
        json={"message": "earbuds please", "history": []},
    )

    assert response.status_code == 200
    assert response.json()["tool_trace"][0]["name"] == "search_products"
    assert received["message"] == "earbuds please"
    assert received["history"] == []
    assert received["mcp"] is app.state["mcp"]
    assert received["ollama"] is app.state["ollama"]


def test_chat_service_unavailable():
    app = create_app(testing=True)

    async def boom(**kwargs):
        raise ChatServiceError("Answer service unavailable", status=503)

    app.state["run_chat"] = boom

    response = TestClient(app).post("/chat", json={"message": "hi"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Answer service unavailable"}


def test_chat_empty_message_is_rejected():
    app = create_app(testing=True)

    response = TestClient(app).post("/chat", json={"message": "  "})

    assert response.status_code == 422


def test_cors_uses_configured_origins(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://localhost:3009, https://catalog.example ",
    )
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        app = create_app(testing=True)
        response = TestClient(app).options(
            "/health",
            headers={
                "Origin": "https://catalog.example",
                "Access-Control-Request-Method": "GET",
            },
        )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "https://catalog.example"
    )


def test_non_testing_lifespan_initializes_and_stops_services(
    monkeypatch,
    tmp_path: Path,
):
    events = []
    db_path = str(tmp_path / "catalog.db")

    class FakeMcp:
        ready = False

        def __init__(self, *, catalog_db_path, server_script):
            events.append(("mcp_created", catalog_db_path, server_script))

        async def start(self):
            self.ready = True
            events.append("mcp_started")

        async def stop(self):
            self.ready = False
            events.append("mcp_stopped")

    class FakeOllama:
        def __init__(self, base_url):
            events.append(("ollama_created", base_url))

    def fake_init_db(path):
        events.append(("db_initialized", path))

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(catalog_db_path=db_path, mcp_server_script="server.py"),
    )
    monkeypatch.setattr(main_module, "init_db", fake_init_db)
    monkeypatch.setattr(main_module, "McpSessionManager", FakeMcp)
    monkeypatch.setattr(main_module, "OllamaClient", FakeOllama)

    app = create_app()
    with TestClient(app):
        assert app.state["mcp"].ready is True

    assert events == [
        ("db_initialized", db_path),
        ("mcp_created", db_path, "server.py"),
        ("ollama_created", "http://127.0.0.1:11434"),
        "mcp_started",
        "mcp_stopped",
    ]
