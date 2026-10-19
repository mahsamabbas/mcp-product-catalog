# CatalogPilot (MCP Product Catalog Assistant) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build CatalogPilot — a React chat UI that answers consumer-electronics catalog questions via a real local MCP server (`search_products`, `lookup_stock` on SQLite), orchestrated by FastAPI + Ollama tool-calling, with every MCP call visible as inline tool cards and a right-side Inspector.

**Architecture:** Browser talks only to FastAPI (`:8009`). FastAPI owns an MCP stdio child process for catalog tools and runs an Ollama tool loop (`qwen2.5:7b`). Catalog facts come only from tool results. Chat history is in-browser only (Clear chat); SQLite holds the synthetic catalog.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, pydantic-settings, httpx, mcp (Python SDK), pytest · React 19, Vite, TypeScript, Tailwind CSS v4, Vitest · Docker Compose · Ollama `qwen2.5:7b`

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-19-mcp-product-catalog-design.md`
- Repo root: `mcp-product-catalog/` (work on `main`, no worktrees)
- Ports: frontend `3009`, API `8009`, Ollama `11434`
- Chat model: `qwen2.5:7b` (env `OLLAMA_CHAT_MODEL`); `OLLAMA_BASE_URL` default `http://127.0.0.1:11434`
- MCP tools exactly: `search_products`, `lookup_stock` (read-only)
- Max tool rounds: **5**
- Search `limit` default **5**, max **20**
- Browser never calls Ollama or MCP. No Gemini/OpenAI required. No purchase/cart/write tools.
- Tests never hit a live model or live MCP subprocess for unit/API tests (mock httpx / inject fake MCP client). Catalog helper tests may use temp SQLite.
- Brand: **CatalogPilot**. UI direction below is mandatory — unique “precision retail ops” look, not a generic chat clone.
- Git author: `mahsamabbas <6658043+mahsamabbas@users.noreply.github.com>`; strip Cursor co-author trailers.
- Python venv: `backend/.venv` via `uv` or `python3.12 -m venv`. Node 22.

### UI / UX direction (non-negotiable)

**Concept:** CatalogPilot is a **precision retail ops console** — brand-first, one composition, tool activity as the hero story (not a dashboard of widgets).

| Token | Value |
| --- | --- |
| Atmosphere | Cool steel wash `#E7ECF2` + faint diagonal micro-hatch (CSS repeating-linear-gradient), soft radial highlight behind the brand |
| Ink | `#0E1525` |
| Signal (live / success) | Volt `#C8F542` |
| Accent (CTA / focus) | Ember `#FF5C39` |
| Protocol hint | Steel blue `#3D5A80` (sparingly — links, MCP badges) |
| Surfaces | Near-white `#F8FAFC` with **hairline** `#0E1525/12` borders — not floating card grids |
| Display font | **Syne** (Google Fonts) — brand + empty-state headline |
| Body font | **Manrope** |
| Forbidden | Purple/indigo gradients, cream+#terracotta serif cliché, Inter/Roboto/Arial/system stacks, dark-mode default, glow soup, rounded-full pill clusters, multi-layer shadows, emoji decoration, inset hero media cards |

**Layout:** Full-bleed steel atmosphere. Top: **CatalogPilot** wordmark as hero-level brand (not tiny nav). Main: chat column. Right: Inspector rail (~340px desktop; drawer on mobile). Empty state: brand + one line + suggestion chips only (no stats strip).

**Motion (ship ≥3):** (1) tool card slide+fade in, (2) Inspector row pulse when a new event arrives, (3) send/CTA ember press + subtle volt shimmer on “MCP live” badge when healthy.

**Copy:** Short, confident, no robotic filler. Tool cards show human labels (“Search products”, “Lookup stock”) plus raw JSON expand.

## File map

| Path | Responsibility |
| --- | --- |
| `.gitignore` | Secrets, venv, node_modules, `*.db`, caches |
| `backend/requirements.txt` | Runtime deps |
| `backend/requirements-dev.txt` | pytest, ruff |
| `backend/.env.example` | `OLLAMA_*`, `CORS_ORIGINS`, `CATALOG_DB_PATH` |
| `backend/app/config.py` | Settings |
| `backend/app/schemas.py` | Chat + health + catalog + ToolTraceEvent models |
| `backend/app/catalog/db.py` | SQLite connect, schema, seed |
| `backend/app/catalog/queries.py` | `search_products`, `lookup_stock` pure DB helpers |
| `backend/app/catalog/seed_data.py` | ~30 synthetic electronics rows |
| `backend/mcp_server/server.py` | MCP stdio server entry (tools → catalog queries) |
| `backend/app/mcp_client.py` | Spawn/own stdio MCP session; `list_tools` / `call_tool` |
| `backend/app/ollama_client.py` | Chat-with-tools via Ollama HTTP API |
| `backend/app/chat.py` | Orchestrator: prompt + tool loop + trace |
| `backend/app/routes.py` | `/health`, `/catalog/summary`, `/chat` |
| `backend/app/main.py` | Lifespan (start MCP), CORS, router |
| `frontend/src/styles.css` | Design tokens, hatch, motion keyframes |
| `frontend/src/types.ts` | API types |
| `frontend/src/api.ts` | Typed fetch |
| `frontend/src/lib/format.ts` | Money / latency helpers |
| `frontend/src/components/*` | Shell, Chat, ToolCard, Inspector, Composer, Chips |
| `frontend/src/App.tsx` | Composition + session state |
| `docker-compose.yml`, `*/Dockerfile`, `frontend/nginx.conf` | One-command run |
| `README.md` | Delivery |

---

### Task 1: Repo scaffold + catalog SQLite helpers (TDD)

**Files:**
- Create: `.gitignore`, `backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/.env.example`
- Create: `backend/app/__init__.py`, `backend/app/config.py`
- Create: `backend/app/catalog/__init__.py`, `backend/app/catalog/db.py`, `backend/app/catalog/seed_data.py`, `backend/app/catalog/queries.py`
- Test: `backend/tests/__init__.py`, `backend/tests/test_catalog_queries.py`

**Interfaces:**
- Produces: `Settings` / `get_settings()`; `init_db(path: str) -> None`; `search_products(conn, query: str, limit: int = 5) -> list[dict]`; `lookup_stock(conn, sku: str) -> dict`

- [ ] **Step 1: Write failing catalog tests**

```python
# backend/tests/test_catalog_queries.py
import sqlite3
from pathlib import Path

from app.catalog.db import init_db
from app.catalog.queries import lookup_stock, search_products


def _conn(tmp_path: Path) -> sqlite3.Connection:
    db = tmp_path / "test.db"
    init_db(str(db))
    return sqlite3.connect(str(db))


def test_search_finds_earbuds(tmp_path: Path):
    conn = _conn(tmp_path)
    rows = search_products(conn, "earbuds", limit=5)
    assert len(rows) >= 1
    assert all("sku" in r and "price" in r for r in rows)
    assert any("earbud" in r["name"].lower() or "earbud" in r["short_description"].lower() for r in rows)


def test_search_empty_query_returns_empty(tmp_path: Path):
    conn = _conn(tmp_path)
    assert search_products(conn, "   ", limit=5) == []


def test_search_no_match(tmp_path: Path):
    conn = _conn(tmp_path)
    assert search_products(conn, "zzzz-no-such-product-qqq", limit=5) == []


def test_lookup_stock_hit(tmp_path: Path):
    conn = _conn(tmp_path)
    hit = search_products(conn, "laptop", limit=1)[0]
    stock = lookup_stock(conn, hit["sku"])
    assert stock["found"] is True
    assert stock["sku"] == hit["sku"]
    assert "quantity" in stock and "in_stock" in stock
    assert stock["in_stock"] == (stock["quantity"] > 0)


def test_lookup_stock_miss(tmp_path: Path):
    conn = _conn(tmp_path)
    stock = lookup_stock(conn, "SKU-DOES-NOT-EXIST")
    assert stock == {"sku": "SKU-DOES-NOT-EXIST", "found": False}


def test_limit_capped_at_20(tmp_path: Path):
    conn = _conn(tmp_path)
    rows = search_products(conn, "a", limit=100)
    assert len(rows) <= 20
```

- [ ] **Step 2: Run tests — expect fail**

```bash
cd backend && python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
PYTHONPATH=. pytest tests/test_catalog_queries.py -v
```

Expected: FAIL (modules missing)

- [ ] **Step 3: Implement scaffold + catalog**

`.gitignore` must include: `.env`, `.venv/`, `node_modules/`, `__pycache__/`, `*.db`, `.DS_Store`, `dist/`, `.vite/`

```text
# backend/requirements.txt
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.9.0
pydantic-settings>=2.6.0
httpx>=0.27.0
mcp>=1.1.0
```

```text
# backend/requirements-dev.txt
pytest>=8.3.0
ruff>=0.7.0
```

```text
# backend/.env.example
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_CHAT_MODEL=qwen2.5:7b
CORS_ORIGINS=http://localhost:3009
CATALOG_DB_PATH=./data/catalog.db
MCP_SERVER_SCRIPT=mcp_server/server.py
```

```python
# backend/app/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_chat_model: str = "qwen2.5:7b"
    cors_origins: str = "http://localhost:3009"
    catalog_db_path: str = "./data/catalog.db"
    mcp_server_script: str = "mcp_server/server.py"
    max_tool_rounds: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`seed_data.py`: export `PRODUCTS: list[dict]` with **≥28** electronics rows covering categories headphones, laptops, cables, keyboards, monitors, chargers, mice. Include at least one `quantity=0` (out of stock) and varied prices. SKUs format `CP-####` (CatalogPilot).

```python
# backend/app/catalog/db.py
import sqlite3
from pathlib import Path

from app.catalog.seed_data import PRODUCTS

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
  sku TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  price REAL NOT NULL,
  currency TEXT NOT NULL,
  short_description TEXT NOT NULL,
  quantity INTEGER NOT NULL,
  warehouse TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1
);
"""


def init_db(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            conn.executemany(
                """
                INSERT INTO products
                (sku, name, category, price, currency, short_description, quantity, warehouse, active)
                VALUES (:sku, :name, :category, :price, :currency, :short_description, :quantity, :warehouse, :active)
                """,
                PRODUCTS,
            )
            conn.commit()
    finally:
        conn.close()


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
```

```python
# backend/app/catalog/queries.py
import sqlite3


def _clamp_limit(limit: int) -> int:
    if limit < 1:
        return 5
    return min(limit, 20)


def search_products(conn: sqlite3.Connection, query: str, limit: int = 5) -> list[dict]:
    q = (query or "").strip()
    if not q:
        return []
    lim = _clamp_limit(limit)
    like = f"%{q}%"
    rows = conn.execute(
        """
        SELECT sku, name, category, price, currency, short_description
        FROM products
        WHERE active = 1
          AND (
            name LIKE ? COLLATE NOCASE
            OR category LIKE ? COLLATE NOCASE
            OR short_description LIKE ? COLLATE NOCASE
            OR sku LIKE ? COLLATE NOCASE
          )
        ORDER BY name
        LIMIT ?
        """,
        (like, like, like, like, lim),
    ).fetchall()
    return [dict(r) for r in rows]


def lookup_stock(conn: sqlite3.Connection, sku: str) -> dict:
    key = (sku or "").strip()
    if not key:
        return {"sku": key, "found": False}
    row = conn.execute(
        """
        SELECT sku, name, quantity, warehouse
        FROM products
        WHERE sku = ? AND active = 1
        """,
        (key,),
    ).fetchone()
    if row is None:
        return {"sku": key, "found": False}
    qty = int(row["quantity"])
    return {
        "sku": row["sku"],
        "name": row["name"],
        "found": True,
        "in_stock": qty > 0,
        "quantity": qty,
        "warehouse": row["warehouse"],
    }
```

- [ ] **Step 4: Run tests — expect pass**

```bash
PYTHONPATH=. pytest tests/test_catalog_queries.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .gitignore backend/
git -c user.name="mahsamabbas" -c user.email="6658043+mahsamabbas@users.noreply.github.com" commit -m "feat: add SQLite electronics catalog helpers"
```

---

### Task 2: MCP stdio server

**Files:**
- Create: `backend/mcp_server/__init__.py`, `backend/mcp_server/server.py`
- Test: `backend/tests/test_mcp_tools_unit.py` (call catalog through the same functions the MCP tools use — no live stdio required)

**Interfaces:**
- Produces: runnable `python -m mcp_server.server` (or `python mcp_server/server.py`) that registers tools `search_products` and `lookup_stock`
- Consumes: `init_db`, `connect`, `search_products`, `lookup_stock`, `CATALOG_DB_PATH` env

- [ ] **Step 1: Write unit test for tool payload shapes**

```python
# backend/tests/test_mcp_tools_unit.py
import json
from pathlib import Path

from app.catalog.db import init_db, connect
from app.catalog.queries import lookup_stock, search_products


def test_tool_payloads_json_serializable(tmp_path: Path):
    path = str(tmp_path / "c.db")
    init_db(path)
    conn = connect(path)
    results = search_products(conn, "cable", limit=3)
    assert json.dumps(results)
    miss = lookup_stock(conn, "NOPE")
    assert json.dumps(miss)
```

- [ ] **Step 2: Run — should pass once catalog exists (Task 1)**

- [ ] **Step 3: Implement MCP server**

Use the official `mcp` Python SDK `Server` + stdio. On startup read `CATALOG_DB_PATH` (default `./data/catalog.db`), call `init_db`, open connection per tool call (or shared with lock — prefer short-lived connect per call for simplicity).

**Important:** exported MCP tool names must be exactly `search_products` and `lookup_stock`. Import catalog helpers under an alias so they do not shadow tool function names.

```python
# backend/mcp_server/server.py
from __future__ import annotations

import json
import os

from mcp.server.fastmcp import FastMCP

from app.catalog import queries as catalog
from app.catalog.db import connect, init_db

DB_PATH = os.environ.get("CATALOG_DB_PATH", "./data/catalog.db")
init_db(DB_PATH)

mcp = FastMCP("catalogpilot")


@mcp.tool(name="search_products")
def search_products(query: str, limit: int = 5) -> str:
    """Search the electronics catalog by name, category, description, or SKU."""
    conn = connect(DB_PATH)
    try:
        rows = catalog.search_products(conn, query, limit=limit)
        return json.dumps({"results": rows, "count": len(rows)})
    finally:
        conn.close()


@mcp.tool(name="lookup_stock")
def lookup_stock(sku: str) -> str:
    """Look up stock quantity and warehouse for a product SKU."""
    conn = connect(DB_PATH)
    try:
        return json.dumps(catalog.lookup_stock(conn, sku))
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

Ensure `PYTHONPATH` includes `backend` when running so `app.catalog` imports resolve.

- [ ] **Step 4: Smoke-check module imports**

```bash
cd backend && PYTHONPATH=. python -c "import mcp_server.server; print('ok')"
```

Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add backend/mcp_server backend/tests/test_mcp_tools_unit.py
git -c user.name="mahsamabbas" -c user.email="6658043+mahsamabbas@users.noreply.github.com" commit -m "feat: add CatalogPilot MCP stdio server"
```

---

### Task 3: Schemas + MCP client manager

**Files:**
- Create: `backend/app/schemas.py`, `backend/app/mcp_client.py`
- Test: `backend/tests/test_mcp_client.py` (fake session injected)

**Interfaces:**
- Produces: `ToolTraceEvent`, `ChatRequest`, `ChatResponse`, `HealthResponse`, `CatalogSummary`
- Produces: `class McpSessionManager` with `async start()`, `async stop()`, `async list_tools() -> list[dict]`, `async call_tool(name: str, arguments: dict) -> tuple[Any, int, bool, str | None]` returning `(result, ms, ok, error)`

- [ ] **Step 1: Write failing schema/client tests**

```python
# backend/tests/test_mcp_client.py
import pytest
from app.schemas import ChatRequest, ToolTraceEvent


def test_chat_request_rejects_blank():
    with pytest.raises(Exception):
        ChatRequest(message="   ")


def test_tool_trace_event_shape():
    ev = ToolTraceEvent(
        name="search_products",
        args={"query": "earbuds"},
        result={"results": []},
        ms=12,
        ok=True,
        error=None,
    )
    assert ev.name == "search_products"
```

- [ ] **Step 2: Implement schemas**

```python
# backend/app/schemas.py
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[HistoryMessage] = Field(default_factory=list)

    @field_validator("message")
    @classmethod
    def non_empty(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("message must not be empty")
        return s


class ToolTraceEvent(BaseModel):
    name: str
    args: dict[str, Any]
    result: Any
    ms: int
    ok: bool
    error: str | None = None


class ChatResponse(BaseModel):
    answer: str
    tool_trace: list[ToolTraceEvent]


class HealthResponse(BaseModel):
    ollama: bool
    mcp: bool
    catalog_count: int | None = None


class CatalogSummary(BaseModel):
    product_count: int
    categories: dict[str, int]
    sample_skus: list[str]
```

- [ ] **Step 3: Implement MCP client**

Use `mcp` client stdio: spawn `sys.executable` with env `PYTHONPATH=<backend>`, `CATALOG_DB_PATH=...`, args `[script_path]` or `-m mcp_server.server`. Keep a single session for app lifetime.

```python
# backend/app/mcp_client.py — outline
# - McpSessionManager.start(): create stdio_client, initialize session, set self._ok = True
# - list_tools(): return [{"name", "description", "input_schema"}, ...]
# - call_tool(name, arguments): time the call; parse TextContent JSON if needed; on exception return (None, ms, False, str(e))
# - stop(): close context
# - property ready: bool
```

Implement fully with the SDK’s `stdio_client` + `ClientSession` pattern (current `mcp` package docs). If FastMCP tool list returns names `search_products` / `lookup_stock`, map those into Ollama later.

For tests, allow injecting a stub:

```python
class FakeMcp:
    ready = True
    async def list_tools(self): ...
    async def call_tool(self, name, arguments): ...
```

- [ ] **Step 4: Run tests**

```bash
PYTHONPATH=. pytest tests/test_mcp_client.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas.py backend/app/mcp_client.py backend/tests/test_mcp_client.py
git -c user.name="mahsamabbas" -c user.email="6658043+mahsamabbas@users.noreply.github.com" commit -m "feat: add chat schemas and MCP session manager"
```

---

### Task 4: Ollama client + chat orchestrator (TDD)

**Files:**
- Create: `backend/app/ollama_client.py`, `backend/app/chat.py`
- Test: `backend/tests/test_chat.py`

**Interfaces:**
- Consumes: `McpSessionManager` (or protocol), `Settings`
- Produces: `async def run_chat(message: str, history: list[HistoryMessage], mcp, ollama, settings) -> ChatResponse`
- Produces: `SYSTEM_PROMPT` constant enforcing tools-only facts + purchase refusal

- [ ] **Step 1: Write failing orchestrator tests (mocked)**

```python
# backend/tests/test_chat.py
import pytest
from app.chat import run_chat
from app.schemas import ChatResponse, HistoryMessage


class FakeOllama:
    def __init__(self, scripted: list[dict]):
        self.scripted = list(scripted)
        self.calls = []

    async def chat(self, *, messages, tools, model):
        self.calls.append({"messages": messages, "tools": tools, "model": model})
        if not self.scripted:
            raise RuntimeError("no scripted responses left")
        return self.scripted.pop(0)


class FakeMcp:
    ready = True

    async def list_tools(self):
        return [
            {
                "name": "search_products",
                "description": "Search catalog",
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
                    "required": ["query"],
                },
            }
        ]

    async def call_tool(self, name, arguments):
        assert name == "search_products"
        return ({"results": [{"sku": "CP-1001", "name": "VoltBuds", "price": 49.0, "currency": "USD", "category": "headphones", "short_description": "earbuds"}], "count": 1}, 8, True, None)


@pytest.mark.asyncio
async def test_normal_search_records_tool_trace():
    ollama = FakeOllama(
        [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "search_products",
                                "arguments": {"query": "earbuds", "limit": 5},
                            }
                        }
                    ],
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": "I found VoltBuds (CP-1001) at $49 USD.",
                }
            },
        ]
    )
    out = await run_chat("Find earbuds", [], FakeMcp(), ollama, max_rounds=5, model="qwen2.5:7b")
    assert isinstance(out, ChatResponse)
    assert out.tool_trace and out.tool_trace[0].name == "search_products"
    assert out.tool_trace[0].ok is True
    assert "VoltBuds" in out.answer


@pytest.mark.asyncio
async def test_ollama_failure_raises_service_unavailable():
    class Boom(FakeOllama):
        async def chat(self, **kwargs):
            raise ConnectionError("down")

    with pytest.raises(Exception) as ei:
        await run_chat("hi", [], FakeMcp(), Boom([]), max_rounds=5, model="x")
    assert "unavailable" in str(ei.value).lower() or ei.value.__class__.__name__ == "ChatServiceError"
```

Also add:

```python
@pytest.mark.asyncio
async def test_mcp_not_ready_raises():
    class Dead(FakeMcp):
        ready = False

    with pytest.raises(Exception):
        await run_chat("hi", [], Dead(), FakeOllama([]), max_rounds=5, model="x")
```

- [ ] **Step 2: Run — expect fail**

- [ ] **Step 3: Implement Ollama + chat**

```python
# backend/app/ollama_client.py
import httpx


class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def healthy(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def chat(self, *, messages: list[dict], tools: list[dict], model: str) -> dict:
        payload = {"model": model, "messages": messages, "stream": False, "tools": tools}
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{self.base_url}/api/chat", json=payload)
            r.raise_for_status()
            return r.json()
```

Map MCP tool schemas → Ollama tools format:

```python
def to_ollama_tools(mcp_tools: list[dict]) -> list[dict]:
    out = []
    for t in mcp_tools:
        out.append(
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description") or t["name"],
                    "parameters": t.get("input_schema")
                    or {"type": "object", "properties": {}},
                },
            }
        )
    return out
```

`SYSTEM_PROMPT` (exact intent):

```text
You are CatalogPilot, a product catalog assistant for a synthetic consumer-electronics store.
Use tools for ANY product, price, stock, or SKU fact. Never invent catalog data.
If tools return empty or not found, say so honestly.
Refuse purchases, carts, payments, and requests for personal data.
Greetings and capability questions may be answered without tools.
Keep answers concise.
```

`run_chat` loop:
1. If not `mcp.ready` → raise `ChatServiceError("Tool layer unavailable", status=503)`
2. `tools = to_ollama_tools(await mcp.list_tools())`
3. messages = [system] + history + user
4. For round in 1..max_rounds:
   - call ollama; on transport error → `ChatServiceError("Answer service unavailable", 503)`
   - if tool_calls: for each, `call_tool`, append tool_trace, append tool role message with result string
   - else: return ChatResponse(answer=content, tool_trace=...)
5. Max rounds → return apology + partial trace

Parse Ollama `tool_calls` defensively (arguments may be dict or JSON string).

- [ ] **Step 4: Install pytest-asyncio if needed; run tests**

```bash
pip install pytest-asyncio
PYTHONPATH=. pytest tests/test_chat.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/ollama_client.py backend/app/chat.py backend/tests/test_chat.py backend/requirements-dev.txt
git -c user.name="mahsamabbas" -c user.email="6658043+mahsamabbas@users.noreply.github.com" commit -m "feat: add Ollama tool loop chat orchestrator"
```

---

### Task 5: FastAPI routes + lifespan + health

**Files:**
- Create: `backend/app/routes.py`, `backend/app/main.py`
- Test: `backend/tests/test_api.py` (TestClient; mock chat/mcp/ollama)

**Interfaces:**
- Produces: app with `GET /health`, `GET /catalog/summary`, `POST /chat`
- Lifespan starts `init_db` + `McpSessionManager.start()`; shutdown stops MCP

- [ ] **Step 1: Write API tests**

```python
# backend/tests/test_api.py
from fastapi.testclient import TestClient
from app.main import create_app
from app.schemas import ChatResponse, ToolTraceEvent


def test_health_shape(monkeypatch):
    app = create_app(testing=True)
    client = TestClient(app)
    # testing mode: inject fakes via app.state
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "ollama" in body and "mcp" in body


def test_chat_normal(monkeypatch):
    app = create_app(testing=True)

    async def fake_run_chat(**kwargs):
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
    client = TestClient(app)
    r = client.post("/chat", json={"message": "earbuds please", "history": []})
    assert r.status_code == 200
    assert r.json()["tool_trace"][0]["name"] == "search_products"


def test_chat_service_unavailable(monkeypatch):
    from app.chat import ChatServiceError
    app = create_app(testing=True)

    async def boom(**kwargs):
        raise ChatServiceError("Answer service unavailable", status_code=503)

    app.state["run_chat"] = boom
    client = TestClient(app)
    r = client.post("/chat", json={"message": "hi"})
    assert r.status_code == 503


def test_chat_empty_422():
    app = create_app(testing=True)
    client = TestClient(app)
    r = client.post("/chat", json={"message": "  "})
    assert r.status_code == 422
```

- [ ] **Step 2: Implement routes + main**

`create_app(testing: bool = False)`:
- CORS from settings
- On lifespan (non-testing): `init_db`, start MCP, create OllamaClient
- testing: skip real MCP; set default fakes in `app.state`

```python
# routes excerpt
@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    run = request.app.state["run_chat"]
    try:
        return await run(
            message=body.message,
            history=body.history,
            mcp=request.app.state["mcp"],
            ollama=request.app.state["ollama"],
            max_rounds=get_settings().max_tool_rounds,
            model=get_settings().ollama_chat_model,
        )
    except ChatServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
```

`/catalog/summary`: query DB for counts by category + 3 sample SKUs.

- [ ] **Step 3: Run full backend suite**

```bash
PYTHONPATH=. pytest -v
```

Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/routes.py backend/app/main.py backend/tests/test_api.py
git -c user.name="mahsamabbas" -c user.email="6658043+mahsamabbas@users.noreply.github.com" commit -m "feat: expose health, catalog summary, and chat API"
```

---

### Task 6: Frontend scaffold + CatalogPilot design system

**Files:**
- Create: `frontend/` Vite React-TS app
- Create: `frontend/src/styles.css`, `frontend/index.html`, fonts via Google Fonts link for **Syne** + **Manrope**
- Create: `frontend/src/types.ts`, `frontend/src/api.ts`, `frontend/src/lib/format.ts`
- Test: `frontend/src/lib/format.test.ts`

**Interfaces:**
- Produces: `formatMoney(amount, currency)`, `formatMs(ms)`, `postChat`, `getHealth`, `getCatalogSummary`
- Visual tokens as CSS variables in `:root`

- [ ] **Step 1: Scaffold**

```bash
cd /Users/azc/Desktop/azc/mahsamabbas_repos/mcp-product-catalog
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install && npm install -D tailwindcss @tailwindcss/vite vitest jsdom @testing-library/react
```

Wire Tailwind v4 in `vite.config.ts` with `@tailwindcss/vite` plugin. Dev server port **3009**. Proxy optional; prefer `VITE_API_BASE_URL=http://localhost:8009`.

- [ ] **Step 2: Failing format test**

```ts
// frontend/src/lib/format.test.ts
import { describe, expect, it } from "vitest";
import { formatMoney, formatMs } from "./format";

describe("formatMoney", () => {
  it("formats USD", () => {
    expect(formatMoney(49, "USD")).toMatch(/\$49/);
  });
});

describe("formatMs", () => {
  it("shows ms", () => {
    expect(formatMs(12)).toBe("12 ms");
  });
});
```

- [ ] **Step 3: Implement format + styles + api types**

```css
/* frontend/src/styles.css — core tokens */
@import "tailwindcss";
@import url("https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&family=Syne:wght@600;700;800&display=swap");

:root {
  --cp-ink: #0e1525;
  --cp-steel: #e7ecf2;
  --cp-surface: #f8fafc;
  --cp-volt: #c8f542;
  --cp-ember: #ff5c39;
  --cp-protocol: #3d5a80;
  --cp-hairline: color-mix(in srgb, var(--cp-ink) 12%, transparent);
  --font-display: "Syne", sans-serif;
  --font-body: "Manrope", sans-serif;
}

html, body, #root {
  height: 100%;
  margin: 0;
  font-family: var(--font-body);
  color: var(--cp-ink);
  background: var(--cp-steel);
}

body {
  background-image:
    radial-gradient(900px 480px at 12% -10%, color-mix(in srgb, var(--cp-volt) 28%, transparent), transparent 60%),
    repeating-linear-gradient(
      -18deg,
      transparent,
      transparent 11px,
      color-mix(in srgb, var(--cp-ink) 3.5%, transparent) 11px,
      color-mix(in srgb, var(--cp-ink) 3.5%, transparent) 12px
    );
}

@keyframes cp-tool-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes cp-pulse-row {
  0% { background-color: color-mix(in srgb, var(--cp-volt) 35%, transparent); }
  100% { background-color: transparent; }
}
@keyframes cp-shimmer {
  0% { background-position: 0% 50%; }
  100% { background-position: 100% 50%; }
}
```

`index.html` title: `CatalogPilot`.

- [ ] **Step 4: Run vitest**

```bash
cd frontend && npx vitest run
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/
git -c user.name="mahsamabbas" -c user.email="6658043+mahsamabbas@users.noreply.github.com" commit -m "feat: scaffold CatalogPilot frontend design system"
```

---

### Task 7: Unique UX — chat, tool cards, Inspector

**Files:**
- Create: `frontend/src/components/BrandHeader.tsx`, `ChatThread.tsx`, `ToolCard.tsx`, `Inspector.tsx`, `Composer.tsx`, `SuggestionChips.tsx`, `StatusPill.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Session state in `App`: `messages: Array<UserMsg | AssistantMsg | ToolGroupMsg>`, `inspectorEvents: ToolTraceEvent[]`, `busy`, `health`
- After `/chat`: append user → tool group (if any) → assistant; concat tool_trace into inspector

- [ ] **Step 1: Build BrandHeader**

Hero-level **CatalogPilot** (Syne 800, large). Subline one short sentence: “Ask the catalog. Watch the tools.” StatusPill: volt shimmer when `health.mcp && health.ollama`, else muted “offline”. Clear chat button (ember outline, not a heavy card).

- [ ] **Step 2: ToolCard**

Inline between turns:
- Left volt tick / protocol badge with tool human name
- Args one-liner (`query=earbuds`, `sku=CP-1001`)
- Result summary (e.g. “3 products”, “12 in stock · Austin”)
- `<details>` for raw JSON
- CSS `animation: cp-tool-in 280ms ease-out`

- [ ] **Step 3: Inspector**

Right rail titled **MCP Inspector**. Header shows catalog product_count from summary. Timeline newest-at-top or chronological bottom — pick **chronological top→bottom** for session. New rows get `cp-pulse-row` once. Empty: “Tool calls will land here.”

- [ ] **Step 4: ChatThread + Composer + Chips**

- Bubbles: user ember-tinted soft fill; assistant surface with hairline border (not heavy shadow cards)
- Composer: full-width input, ember send button, Enter to send
- Chips (exact starters):
  1. `Find wireless earbuds under $50`
  2. `Is CP-1001 in stock?` (use a real seeded SKU from seed_data)
  3. `Buy 2 laptops for me` (refusal path)

- [ ] **Step 5: App composition**

One viewport composition: header + (thread | inspector) + composer. `100dvh`, overflow hidden; thread and inspector scroll internally. Mobile: Inspector behind a “Inspector” toggle drawer.

Wire `postChat`; on error show inline banner (503 copy from API detail).

- [ ] **Step 6: Manual visual pass**

```bash
cd frontend && npm run dev
```

Check: brand dominates first look; no purple; fonts Syne/Manrope; motions present; chips work offline (don’t need API for layout).

- [ ] **Step 7: Commit**

```bash
git add frontend/src
git -c user.name="mahsamabbas" -c user.email="6658043+mahsamabbas@users.noreply.github.com" commit -m "feat: add CatalogPilot chat, tool cards, and MCP Inspector UX"
```

---

### Task 8: Docker Compose + README + env examples

**Files:**
- Create: `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`
- Create: `frontend/.env.example`, root `README.md`
- Modify: backend CORS default for docker if needed

- [ ] **Step 1: Docker**

Compose services `frontend` (3009→80) and `backend` (8009→8000). Backend env:

```yaml
OLLAMA_BASE_URL: http://host.docker.internal:11434
CATALOG_DB_PATH: /data/catalog.db
CORS_ORIGINS: http://localhost:3009
```

Mount named volume for `/data`. `extra_hosts: ["host.docker.internal:host-gateway"]` for Linux friendliness.

Frontend build arg `VITE_API_BASE_URL=http://localhost:8009`.

- [ ] **Step 2: README**

Include: description, features, stack table, libraries, API routes, env vars, Docker + local run, Ollama pull `qwen2.5:7b`, tests, limitations, links to design + this plan. Note MCP is a real stdio server owned by FastAPI.

- [ ] **Step 3: Verify compose config**

```bash
docker compose config
```

Expected: valid config

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml backend/Dockerfile frontend/Dockerfile frontend/nginx.conf frontend/.env.example README.md
git -c user.name="mahsamabbas" -c user.email="6658043+mahsamabbas@users.noreply.github.com" commit -m "docs: add Docker Compose and README for CatalogPilot"
```

---

### Task 9: End-to-end hardening + final review fixes

**Files:**
- Modify as needed after live run
- Optional: `frontend/src/components/*.tsx` polish

- [ ] **Step 1: Live backend**

```bash
ollama serve   # if not running
ollama pull qwen2.5:7b
cd backend && source .venv/bin/activate
export PYTHONPATH=.
export CATALOG_DB_PATH=./data/catalog.db
uvicorn app.main:app --reload --port 8009
```

- [ ] **Step 2: Curl happy path**

```bash
curl -s http://localhost:8009/health | python -m json.tool
curl -s http://localhost:8009/catalog/summary | python -m json.tool
curl -s -X POST http://localhost:8009/chat \
  -H 'content-type: application/json' \
  -d '{"message":"Find wireless earbuds","history":[]}' | python -m json.tool
```

Expected: health mcp+ollama true; chat includes `tool_trace` with `search_products`.

- [ ] **Step 3: Full test suite + frontend tests**

```bash
cd backend && PYTHONPATH=. pytest -v
cd ../frontend && npx vitest run
```

- [ ] **Step 4: UI polish checklist**

- [ ] Brand readable as hero without nav
- [ ] Tool cards + Inspector both update on one turn
- [ ] Clear chat wipes thread + inspector, not DB
- [ ] Purchase chip refuses cleanly
- [ ] Mobile inspector drawer works
- [ ] No forbidden visual tropes

- [ ] **Step 5: Commit any fixes**

```bash
git add -A
git -c user.name="mahsamabbas" -c user.email="6658043+mahsamabbas@users.noreply.github.com" commit -m "fix: harden CatalogPilot chat path and UI polish"
```

---

## Self-review (plan vs spec)

| Spec requirement | Task |
| --- | --- |
| Real MCP stdio server, FastAPI-owned | Task 2–3, 5 |
| Tools `search_products`, `lookup_stock` | Task 1–2 |
| SQLite electronics seed | Task 1 |
| Ollama tool loop, max 5 rounds | Task 4 |
| Tools-only catalog facts + purchase refuse | Task 4 system prompt |
| `/health`, `/catalog/summary`, `/chat` | Task 5 |
| Inline tool cards + Inspector | Task 7 |
| Clear chat, no multi-session persistence | Task 7 |
| React+Vite+TS+Tailwind, ports 3009/8009 | Task 6–8 |
| Docker + README + .env.example | Task 8 |
| pytest normal + failure | Task 4–5 |
| Modern unique UI | Task 6–7 + Global UI constraints |

**Placeholder scan:** none intentional — FastMCP import path locked to `mcp.server.fastmcp`; if SDK version differs, implementer adjusts import but keeps tool names and stdio transport.

**Type consistency:** `ToolTraceEvent` fields `name, args, result, ms, ok, error` used in schemas, chat, API tests, and frontend types.
