# CatalogPilot — MCP Product Catalog Assistant

CatalogPilot is a local-first chat assistant over a **synthetic consumer-electronics catalog**. Ask about products, prices, SKUs, and stock. Answers are grounded in a **real MCP server** (read-only tools); the UI shows every tool call as **inline cards** plus a right-side **MCP Inspector**.

Portfolio app 10 of 10. Scope: local MCP product-search and stock-lookup over synthetic data, connect an AI assistant, and show tool calls/results. No purchases, customer data, or production systems.

## What it does

- **Real MCP, not a fake label.** FastAPI owns a Python MCP stdio child for the API lifetime. Tools are `search_products` and `lookup_stock` over SQLite.
- **Ollama tool-calling loop.** The model receives MCP tool schemas, may call tools (max 5 rounds), and FastAPI executes each call through the MCP client. Catalog facts (price, stock, SKU) come **only** from tool results — never invented.
- **Visible tool trace.** Each turn returns `tool_trace[]` (name, args, result, latency, ok/error). The chat shows inline tool cards; the Inspector keeps a session timeline until Clear chat.
- **Honest refusals.** Purchases, carts, payments, and PII requests are refused. Empty search / unknown SKU return grounded “not found” answers.
- **Local-only demo.** No cloud LLM key required. Browser talks only to FastAPI; never to Ollama or MCP directly.

## Architecture

```text
[Browser · CatalogPilot · :3009]
  chat · ToolCard · Inspector · Clear chat · suggestion chips
        │ HTTP only
        ▼
[FastAPI · :8009]
  POST /chat → list MCP tools → Ollama tool loop → MCP call_tool
  GET /health · GET /catalog/summary
        │
        ├──► [MCP server · stdio child]
        │      search_products · lookup_stock
        │      └── SQLite electronics catalog (~29 SKUs)
        │
        └──► [Ollama · host :11434]
               qwen2.5:7b (tool-capable)
```

Docker Compose runs frontend (nginx) + backend; Ollama stays on the host via `host.docker.internal`.

## Concepts demonstrated

| Concept | How CatalogPilot shows it |
| --- | --- |
| **MCP (Model Context Protocol)** | Standalone stdio server; FastAPI is the MCP client (`list_tools` / `call_tool`) |
| **Tool calling** | Ollama chat-with-tools; arguments mapped from MCP JSON schemas |
| **Grounded answers** | System prompt: use tools for catalog facts; never invent SKU/price/stock |
| **Tool observability** | `ToolTraceEvent` → inline cards + Inspector timeline |
| **Read-only tools** | Search + stock only; no write/buy/cart MCP tools |
| **Human-readable UX** | Brand-first “precision retail ops” UI (Syne + Manrope, steel / volt / ember) |
| **Local LLM ops** | Host Ollama; Docker backend reaches it without baking the model into the image |

## Tech stack

| Layer | Choice |
| --- | --- |
| Frontend | React 19, TypeScript, Vite 6, Tailwind CSS v4, nginx (production) |
| Backend | Python 3.12, FastAPI, Uvicorn, Pydantic v2, pydantic-settings |
| MCP | Official Python `mcp` SDK (`>=2.3,<3`) — stdio server + client session |
| LLM | Ollama `qwen2.5:7b` (override with `OLLAMA_CHAT_MODEL`) via HTTP (`httpx`) |
| Data | SQLite (`catalog.db`), seeded synthetic electronics |
| Tests | pytest, pytest-asyncio, Vitest, Testing Library / jsdom |
| Delivery | Docker Compose (ports **3009** UI · **8009** API · **11434** Ollama) |

## Libraries and pieces

### Backend

| Piece | Role |
| --- | --- |
| `fastapi` / `uvicorn` | HTTP API, lifespan, CORS |
| `pydantic` / `pydantic-settings` | Request/response models, env config |
| `httpx` | Async calls to Ollama `/api/chat` and `/api/tags` |
| `mcp` | MCP server (`MCPServer`) + stdio client (`stdio_client`, `ClientSession`) |
| `sqlite3` | Catalog schema, seed, tokenized `LIKE` search |
| `app/catalog/` | `db.py`, `queries.py`, `seed_data.py` |
| `mcp_server/server.py` | Tools: `search_products`, `lookup_stock` |
| `app/mcp_client.py` | Spawn/own stdio child; list/call tools; readiness |
| `app/ollama_client.py` | Chat-with-tools + health probe |
| `app/chat.py` | System prompt, tool loop, `ToolTraceEvent` assembly, 503 errors |

### Frontend

| Piece | Role |
| --- | --- |
| `react` / `react-dom` | UI |
| `vite` / `@vitejs/plugin-react` | Dev server (3009) and production build |
| `typescript` | Strict typing; mirrors API types |
| `tailwindcss` / `@tailwindcss/vite` | Utility styling + design tokens |
| `vitest` / `jsdom` / `@testing-library/react` | Unit tests (formatters, session helpers, tool summaries) |
| Components | `BrandHeader`, `StatusPill`, `ChatThread`, `ToolCard`, `Inspector`, `Composer`, `SuggestionChips` |

## MCP tools

| Tool | Input | Output |
| --- | --- | --- |
| `search_products` | `query` (required), `limit` (default 5, max 20) | `{ results: [...], count }` — sku, name, category, price, currency, short_description |
| `lookup_stock` | `sku` (required) | Hit: sku, name, found, in_stock, quantity, warehouse · Miss: `{ sku, found: false }` |

Search tokenizes the query and **AND**s case-insensitive `LIKE` matches across name, category, description, and SKU. Inactive rows are excluded.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | `{ ollama, mcp, catalog_count }` |
| `GET` | `/catalog/summary` | Product count, categories, sample SKUs |
| `POST` | `/chat` | One turn → `{ answer, tool_trace[] }` |

`POST /chat` body:

```json
{
  "message": "Find earbuds under $100",
  "history": [
    { "role": "user", "content": "I need headphones" },
    { "role": "assistant", "content": "Wireless or over-ear?" }
  ]
}
```

Errors: `422` empty message · `503` Ollama or MCP tool layer unavailable.

OpenAPI: http://localhost:8009/docs

## Environment

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

| Variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Compose uses `http://host.docker.internal:11434` |
| `OLLAMA_CHAT_MODEL` | `qwen2.5:7b` | Tool-capable chat model |
| `CORS_ORIGINS` | `http://localhost:3009` | Comma-separated browser origins |
| `CATALOG_DB_PATH` | `./data/catalog.db` | Compose: `/data/catalog.db` (named volume) |
| `MCP_SERVER_SCRIPT` | `mcp_server/server.py` | Stdio MCP entry |
| `MAX_TOOL_ROUNDS` | `5` | Cap per chat turn |
| `VITE_API_BASE_URL` | `http://localhost:8009` | Frontend build-time API URL |

No secrets required for the core demo.

## Run with Docker

```bash
ollama serve
ollama pull qwen2.5:7b
docker compose up --build
```

- UI: http://localhost:3009  
- API: http://localhost:8009  

Stop: `docker compose down`. Add `-v` only to wipe the catalog volume.

**Linux:** Ollama often listens on `127.0.0.1` only; the container may need `OLLAMA_HOST=0.0.0.0` (or the Docker bridge IP) on the host so `host.docker.internal` can reach it. Prefer binding to the bridge IP and firewalling port 11434 rather than exposing Ollama on every interface.

## Run locally

Python 3.12, Node 22, Ollama on the host.

```bash
ollama serve
ollama pull qwen2.5:7b

# backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
PYTHONPATH=. uvicorn app.main:app --reload --port 8009

# frontend (other terminal)
cd frontend
npm ci
cp .env.example .env
npm run dev
```

Open http://localhost:3009.

### Try it

- Chip **Find earbuds under $100** → `search_products` trace + grounded list  
- Chip **Is CP-1001 in stock?** → `lookup_stock`  
- Chip **Buy 2 laptops for me** → refusal, no purchase tool  

## Tests

Mocks / temp DB — no live model required for the suite. One integration test starts a real MCP stdio session against a temp catalog.

```bash
cd backend && source .venv/bin/activate && PYTHONPATH=. pytest -v
cd ../frontend && npm test
docker compose config   # optional config check
```

## Limitations

- Answer quality and latency depend on local Ollama hardware and the model’s tool-calling behavior.
- Search is keyword SQL (tokenized AND), not semantic / vector retrieval.
- Stdio MCP is for a single local API process — not a multi-tenant MCP gateway.
- Chat history is in-browser only (Clear chat); follow-ups do not automatically replay prior tool payloads unless the assistant re-calls tools or cites them from prior text.
- Responses are non-streaming JSON in v1.
- No auth, checkout, ERP sync, or real inventory.

## Project documents

- [Design specification](docs/superpowers/specs/2026-10-19-mcp-product-catalog-design.md)
- [Implementation plan](docs/superpowers/plans/2026-10-19-mcp-product-catalog.md)
