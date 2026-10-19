# CatalogPilot

CatalogPilot is a local-first product catalog assistant for a synthetic consumer-electronics store. Ask about products, prices, SKUs, and stock while the UI exposes every catalog tool call in inline cards and an MCP Inspector.

FastAPI owns a real MCP stdio server as a child process for its full lifetime. The browser talks only to FastAPI; FastAPI uses MCP for grounded catalog data and Ollama for the tool-calling chat loop.

## Features

- Grounded product search and stock lookup through read-only MCP tools
- Visible tool arguments, results, status, and latency
- Local Ollama inference with no cloud API required
- Seeded SQLite catalog persisted in Docker
- Responsive React chat with session-only history and Clear chat
- Health and catalog summary endpoints

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, nginx |
| API | Python 3.12, FastAPI, Uvicorn, Pydantic 2 |
| Tool protocol | MCP Python SDK over stdio |
| Model | Ollama with `qwen2.5:7b` |
| Data | SQLite |
| Tests | pytest, pytest-asyncio, Vitest, Testing Library |
| Runtime | Docker Compose |

Key libraries include `httpx` for Ollama HTTP calls, `pydantic-settings` for configuration, and the official `mcp` SDK for the FastAPI-owned stdio client/server session.

## API

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Report Ollama/MCP readiness and catalog count |
| `GET` | `/catalog/summary` | Return product count, category counts, and sample SKUs |
| `POST` | `/chat` | Run one chat turn and return the answer plus MCP tool trace |

`POST /chat` accepts:

```json
{
  "message": "Find wireless earbuds under $50",
  "history": [
    { "role": "user", "content": "I need headphones" },
    { "role": "assistant", "content": "What kind?" }
  ]
}
```

Interactive OpenAPI documentation is available at `http://localhost:8009/docs`.

## Environment

Copy the examples before local development if you want to customize defaults:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

| Variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama API URL; Compose uses `http://host.docker.internal:11434` |
| `OLLAMA_CHAT_MODEL` | `qwen2.5:7b` | Tool-capable Ollama model |
| `CORS_ORIGINS` | `http://localhost:3009` | Comma-separated allowed browser origins |
| `CATALOG_DB_PATH` | `./data/catalog.db` | SQLite database path; Compose uses `/data/catalog.db` |
| `MCP_SERVER_SCRIPT` | `mcp_server/server.py` | MCP stdio server entry point |
| `MAX_TOOL_ROUNDS` | `5` | Maximum tool-call rounds per chat turn |
| `VITE_API_BASE_URL` | `http://localhost:8009` | API URL compiled into the frontend |

These settings contain no secrets. Vite variables are public browser configuration.

## Run with Docker

Ollama runs on the host so models can use the host's hardware:

```bash
ollama serve
ollama pull qwen2.5:7b
docker compose up --build
```

Open `http://localhost:3009`. The API is at `http://localhost:8009`. Compose maps host Ollama into the backend with `host.docker.internal`, starts the MCP stdio child inside the backend container, and stores the catalog in the `catalog_data` volume.

Stop the app with `docker compose down`. Add `-v` only when you also want to delete the persisted catalog volume.

## Run locally

Requirements: Python 3.12, Node.js 22, and Ollama.

```bash
ollama serve
ollama pull qwen2.5:7b

cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
PYTHONPATH=. uvicorn app.main:app --reload --port 8009
```

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3009`.

## Tests

Tests use fakes and temporary databases; they do not require a live Ollama model.

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest -v

cd ../frontend
npm test
```

To validate deployment configuration:

```bash
docker compose config
```

## Limitations

- Tool-calling quality and response time depend on the local model and hardware.
- Catalog search uses SQL keyword matching, not semantic retrieval or embeddings.
- The stdio MCP lifecycle is designed for a local single-API demo, not a multi-tenant gateway.
- Chat history is browser-session state and responses are non-streaming.
- Catalog tools are intentionally read-only; there is no checkout, payment, authentication, or production inventory integration.

## Project documents

- [Design specification](docs/superpowers/specs/2026-10-19-mcp-product-catalog-design.md)
- [Implementation plan](docs/superpowers/plans/2026-10-19-mcp-product-catalog.md)
