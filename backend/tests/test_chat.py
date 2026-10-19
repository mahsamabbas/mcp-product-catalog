import json
from copy import deepcopy

import httpx
import pytest

from app.chat import SYSTEM_PROMPT, ChatServiceError, run_chat, to_ollama_tools
from app.config import Settings
from app.ollama_client import OllamaClient
from app.schemas import ChatResponse, HistoryMessage


class FakeOllama:
    def __init__(self, scripted: list[dict]):
        self.scripted = list(scripted)
        self.calls = []

    async def chat(self, *, messages, tools, model):
        self.calls.append(
            {"messages": deepcopy(messages), "tools": deepcopy(tools), "model": model}
        )
        if not self.scripted:
            raise RuntimeError("no scripted responses left")
        return self.scripted.pop(0)


class FakeMcp:
    ready = True

    def __init__(self):
        self.calls = []

    async def list_tools(self):
        return [
            {
                "name": "search_products",
                "description": "Search catalog",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["query"],
                },
            }
        ]

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return (
            {
                "results": [
                    {
                        "sku": "CP-1001",
                        "name": "VoltBuds",
                        "price": 49.0,
                        "currency": "USD",
                    }
                ],
                "count": 1,
            },
            8,
            True,
            None,
        )


@pytest.mark.asyncio
async def test_normal_search_records_tool_trace_and_context():
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
    mcp = FakeMcp()
    history = [HistoryMessage(role="user", content="I like audio gear")]

    out = await run_chat(
        "Find earbuds",
        history,
        mcp,
        ollama,
        max_rounds=5,
        model="qwen2.5:7b",
    )

    assert isinstance(out, ChatResponse)
    assert out.tool_trace[0].name == "search_products"
    assert out.tool_trace[0].ok is True
    assert "VoltBuds" in out.answer
    assert mcp.calls == [("search_products", {"query": "earbuds", "limit": 5})]
    assert ollama.calls[0]["messages"] == [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "I like audio gear"},
        {"role": "user", "content": "Find earbuds"},
    ]
    tool_message = ollama.calls[1]["messages"][-1]
    assert tool_message["role"] == "tool"
    assert json.loads(tool_message["content"])["count"] == 1


@pytest.mark.asyncio
async def test_json_string_tool_arguments_and_failed_tool_are_recorded():
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
                                "arguments": '{"query": "camera"}',
                            }
                        }
                    ],
                }
            },
            {"message": {"role": "assistant", "content": "No result available."}},
        ]
    )

    class FailedMcp(FakeMcp):
        async def call_tool(self, name, arguments):
            return None, 3, False, "catalog timeout"

    out = await run_chat(
        "Find a camera", [], FailedMcp(), ollama, max_rounds=5, model="x"
    )

    assert out.tool_trace[0].args == {"query": "camera"}
    assert out.tool_trace[0].ok is False
    assert out.tool_trace[0].error == "catalog timeout"


@pytest.mark.asyncio
async def test_max_rounds_returns_apology_and_partial_trace():
    tool_response = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "search_products",
                        "arguments": {"query": "earbuds"},
                    }
                }
            ],
        }
    }
    out = await run_chat(
        "Find earbuds",
        [],
        FakeMcp(),
        FakeOllama([tool_response, tool_response]),
        max_rounds=2,
        model="x",
    )

    assert "couldn't complete" in out.answer.lower()
    assert len(out.tool_trace) == 2


@pytest.mark.asyncio
async def test_ollama_failure_raises_service_unavailable():
    class Boom(FakeOllama):
        async def chat(self, **kwargs):
            raise ConnectionError("down")

    with pytest.raises(ChatServiceError, match="Answer service unavailable") as exc:
        await run_chat("hi", [], FakeMcp(), Boom([]), max_rounds=5, model="x")

    assert exc.value.status == 503


@pytest.mark.asyncio
async def test_mcp_not_ready_raises():
    class Dead(FakeMcp):
        ready = False

    with pytest.raises(ChatServiceError, match="Tool layer unavailable") as exc:
        await run_chat("hi", [], Dead(), FakeOllama([]), max_rounds=5, model="x")

    assert exc.value.status == 503


@pytest.mark.asyncio
async def test_mcp_becoming_unready_mid_loop_raises():
    mcp = FakeMcp()
    ollama = FakeOllama(
        [
            {
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "search_products",
                                "arguments": {"query": "earbuds"},
                            }
                        }
                    ],
                }
            }
        ]
    )

    async def transport_failure(name, arguments):
        mcp.ready = False
        return None, 1, False, "connection lost"

    mcp.call_tool = transport_failure

    with pytest.raises(ChatServiceError, match="Tool layer unavailable") as exc:
        await run_chat("Find earbuds", [], mcp, ollama, max_rounds=5, model="x")

    assert exc.value.status == 503


@pytest.mark.asyncio
async def test_mcp_drop_during_answer_generation_raises():
    mcp = FakeMcp()

    class DropsMcpWhileAnswering(FakeOllama):
        async def chat(self, **kwargs):
            mcp.ready = False
            return {"message": {"role": "assistant", "content": "Unverified answer"}}

    with pytest.raises(ChatServiceError, match="Tool layer unavailable") as exc:
        await run_chat(
            "Find earbuds",
            [],
            mcp,
            DropsMcpWhileAnswering([]),
            max_rounds=5,
            model="x",
        )

    assert exc.value.status == 503


@pytest.mark.asyncio
async def test_logical_tool_failure_remains_a_trace_event():
    ollama = FakeOllama(
        [
            {
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "search_products",
                                "arguments": {"query": "camera"},
                            }
                        }
                    ],
                }
            },
            {"message": {"role": "assistant", "content": "No result available."}},
        ]
    )

    class LogicalFailureMcp(FakeMcp):
        async def call_tool(self, name, arguments):
            return {"code": "invalid_query"}, 3, False, "invalid query"

    out = await run_chat(
        "Find a camera", [], LogicalFailureMcp(), ollama, max_rounds=5, model="x"
    )

    assert out.answer == "No result available."
    assert out.tool_trace[0].ok is False
    assert out.tool_trace[0].result == {"code": "invalid_query"}


@pytest.mark.asyncio
async def test_run_chat_accepts_settings_for_model_and_round_limit():
    ollama = FakeOllama(
        [{"message": {"role": "assistant", "content": "Hello from CatalogPilot."}}]
    )
    settings = Settings(ollama_chat_model="custom-model", max_tool_rounds=3)

    out = await run_chat("hello", [], FakeMcp(), ollama, settings)

    assert out.answer == "Hello from CatalogPilot."
    assert ollama.calls[0]["model"] == "custom-model"


def test_mcp_tools_are_mapped_to_ollama_function_tools():
    assert to_ollama_tools(
        [{"name": "catalog_summary", "description": "", "input_schema": None}]
    ) == [
        {
            "type": "function",
            "function": {
                "name": "catalog_summary",
                "description": "catalog_summary",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]


@pytest.mark.asyncio
async def test_ollama_client_health_and_chat(monkeypatch):
    requests = []

    async def handler(request):
        requests.append(request)
        if request.url.path == "/api/tags":
            return httpx.Response(200)
        return httpx.Response(200, json={"message": {"content": "hello"}})

    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    client = OllamaClient("http://ollama.test/")

    assert await client.healthy() is True
    response = await client.chat(
        messages=[{"role": "user", "content": "hello"}],
        tools=[],
        model="qwen",
    )

    assert response == {"message": {"content": "hello"}}
    assert json.loads(requests[1].content) == {
        "model": "qwen",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
        "tools": [],
    }


@pytest.mark.asyncio
async def test_ollama_health_returns_false_on_transport_failure(monkeypatch):
    original_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        return original_client(
            transport=httpx.MockTransport(
                lambda request: (_ for _ in ()).throw(httpx.ConnectError("down"))
            )
        )

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    assert await OllamaClient("http://ollama.test").healthy() is False
