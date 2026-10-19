# MCP Product Catalog Assistant (CatalogPilot)

Design for App 10. A chat assistant answers product and stock questions over a **synthetic consumer-electronics catalog** by calling a **real local MCP server** (read-only tools). The UI shows every tool call and result (inline cards + Inspector). No purchases, no real customer data, no production systems, no cloud LLM required for the core demo.

## Decisions

| Topic | Choice |
| --- | --- |
| Product name | **CatalogPilot** |
| Goal | Portfolio demo: MCP tools + Ollama tool-calling + visible tool trace |
| Approach | **Approach 2** — standalone MCP server (stdio) + FastAPI as MCP client + Ollama tool loop |
| Frontend | **React + Vite + TypeScript + Tailwind CSS** |
| Backend | **FastAPI + Pydantic v2** |
| MCP | **Python MCP server** over stdio; tools backed by SQLite |
| LLM | Local **Ollama** — default `qwen2.5:7b` (tool-capable); override via `OLLAMA_CHAT_MODEL` |
| Cloud APIs | None required for core demo |
| Catalog domain | Synthetic **consumer electronics** (~25–40 SKUs) |
| Catalog facts | **Tools-only** — never invent price / stock / SKU |
| Tool UX | **Inline tool cards** in chat **+** right-side **Inspector** timeline |
| Chat persistence | In-browser thread only + **Clear chat**; catalog in SQLite |
| Ports | Frontend **3009**, API **8009**, Ollama **11434** |
| Repo | `mcp-product-catalog` → public under `mahsamabbas` |

## Architecture

Four runtime pieces on the developer machine:

1. **Browser + React (Vite) + TypeScript + Tailwind** — CatalogPilot UI. Port **3009**.
2. **FastAPI** — chat orchestrator, MCP client (stdio), Ollama tool loop, health. Port **8009**.
3. **MCP server process** — **always spawned and owned by FastAPI** as a stdio child for the API process lifetime; exposes `search_products` and `lookup_stock` over SQLite.
4. **Ollama on the host** (`http://127.0.0.1:11434`) — chat model with tool calling. Dockerized API reaches Ollama via `host.docker.internal` (or `OLLAMA_BASE_URL`).

```
[Browser / CatalogPilot :3009]
  chat · inline tool cards · Inspector · Clear chat · suggestion chips
        │ HTTP only
        ▼
[FastAPI :8009]
  POST /chat → list MCP tools → Ollama tool loop → call_tool via MCP
  return { answer, tool_trace[] }
        │
        ├──► [MCP server · stdio]
        │      search_products · lookup_stock
        │      └── SQLite electronics catalog
        │
        └──► [Ollama :11434]
               qwen2.5:7b (or OLLAMA_CHAT_MODEL)
```

**Hard rules:**

- Browser never calls Ollama or the MCP server directly.
- Catalog facts (price, stock, SKU, product existence) come only from tool results.
- Tools are **read-only**. No buy, cart, checkout, or catalog mutation from the assistant.
- Purchases, PII collection, and non-catalog tasks are refused in the system prompt.

## MCP tools

Exactly two tools in v1:

### `search_products`

| Field | Type | Notes |
| --- | --- | --- |
| `query` | string | Required; name / category / keyword |
| `limit` | int | Optional; default **5**, max **20** |

**Returns:** list of objects:

```text
sku, name, category, price, currency, short_description
```

Empty list when nothing matches (not an error).

### `lookup_stock`

| Field | Type | Notes |
| --- | --- | --- |
| `sku` | string | Required |

**Returns on hit:**

```text
sku, name, in_stock (bool), quantity (int), warehouse (str)
```

**Returns on miss:** a structured not-found payload (e.g. `{ "sku": "...", "found": false }`) so the model can say the SKU is not in the catalog without inventing stock.

## SQLite catalog

- Seeded on first boot with ~25–40 synthetic electronics products.
- Columns: `sku` (PK), `name`, `category`, `price`, `currency`, `short_description`, `quantity`, `warehouse`, `active`.
- Search: simple SQL `LIKE` / case-insensitive match on name, category, description (good enough for demo; no vector search in v1).
- Stock: read `quantity` / derive `in_stock` (`quantity > 0`); inactive rows treated as not found.
- No write APIs on the chat path. Seed script or module may reset/reseed for local demos.

## FastAPI surface

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | `{ ollama: bool, mcp: bool, catalog_count?: int }` |
| `GET` | `/catalog/summary` | Lightweight counts / category breakdown for empty-state or Inspector header |
| `POST` | `/chat` | Run one user turn; return answer + tool trace |

### `POST /chat` request

```text
message: str          # required, non-empty
history: list[{role, content}]  # optional; current thread only (no server persistence)
```

### `POST /chat` response

```text
answer: str
tool_trace: list[ToolTraceEvent]
```

```text
ToolTraceEvent
  name: str
  args: object
  result: object | str
  ms: int
  ok: bool
  error: str | null
```

No authentication. No streaming required in v1 (single JSON response is fine; SSE optional later if time allows).

## Chat / tool loop

1. Validate input; reject empty message.
2. Ensure MCP client is connected; `list_tools` → map to Ollama tool schemas.
3. Build messages: system prompt + history + user message.
4. System prompt requirements:
   - Use tools for any product, price, stock, or SKU fact.
   - Never invent catalog data.
   - Refuse purchases and requests outside the catalog.
   - Greetings / “what can you do?” may answer without tools.
5. Loop (max **5** tool rounds):
   - Call Ollama with tools.
   - If tool calls: for each, MCP `call_tool`, append tool result, append `ToolTraceEvent`.
   - If final text: break.
6. If max rounds hit: return partial `tool_trace` + short apology that the lookup could not finish.
7. UI renders user bubble → tool cards (from `tool_trace`) → assistant `answer`; Inspector shows the same events for that turn (and optionally accumulates for the session until Clear chat).

## Frontend (CatalogPilot)

- **Layout:** main chat column + right **Inspector** panel (collapsible on small screens).
- **Chat:** user/assistant bubbles; **inline tool cards** between them when `tool_trace` is non-empty (tool name, args summary, result summary, expandable JSON).
- **Inspector:** chronological timeline of MCP calls for the current session (until Clear); each row shows name, args JSON, result JSON, latency, ok/error.
- **Clear chat:** clears in-browser messages + Inspector session trace; does not wipe SQLite catalog.
- **Suggestion chips:** e.g. search under a price, lookup a known sample SKU, refuse-purchase prompt for failure-path demo.
- Browser talks only to FastAPI (`VITE_API_BASE_URL`).

## Error handling

| Case | Behavior |
| --- | --- |
| Ollama unreachable / error | HTTP **503** — answer service unavailable |
| MCP server fail / disconnect | HTTP **503** — tool layer unavailable |
| Unknown SKU | Tool not-found → grounded “not in catalog” answer |
| Empty search | Empty list → grounded “no matches” |
| Max tool rounds | Partial trace + short apology |
| Purchase / PII / off-topic | Refuse; no matching write/PII tool exists |
| Invalid chat body | HTTP **422** |

## Testing

pytest with **Ollama and MCP client mocked** (and/or MCP tools tested against an in-memory / temp SQLite DB):

1. **Normal:** user asks to search → orchestrator records `search_products` in `tool_trace` → answer is consistent with mocked tool result.
2. **Failure:** Ollama (or MCP) unavailable → **503**.
3. Unit: catalog `search_products` / `lookup_stock` helpers — match, empty, unknown SKU.
4. Optional frontend Vitest for small pure helpers (formatters) if introduced.

## Out of scope

- Real commerce platforms, payments, carts, inventory sync
- Auth / multi-user / saved chat history across refresh
- Gemini or other cloud LLM for the core demo
- Vector search / embeddings over the catalog
- Write/update/delete products via MCP
- Telephony, WhatsApp, or external MCP hosts (Claude Desktop optional mention in README only)

## Delivery

- `docker-compose.yml`: frontend (nginx) + backend; host Ollama via `host.docker.internal`
- Root README: stack, API, env, Docker + local run, tests, limitations, design/plan links
- `.env.example` only in git (no secrets)
- Public GitHub repo under `mahsamabbas` when ready to publish

## Known limitations (expected)

- Tool-calling quality depends on local Ollama model/hardware.
- Keyword SQL search is not semantic RAG.
- Stdio MCP lifecycle is local-demo oriented, not a multi-tenant gateway.
- Single JSON chat response (no token streaming) in v1.
