import asyncio
from types import SimpleNamespace

import pytest

from app.mcp_client import McpSessionManager
from app.schemas import ChatRequest, ToolTraceEvent


def test_chat_request_rejects_blank():
    with pytest.raises(Exception):
        ChatRequest(message="   ")


def test_chat_request_strips_message_and_has_independent_history():
    first = ChatRequest(message="  hello  ")
    second = ChatRequest(message="world")

    first.history.append({"role": "user", "content": "earbuds"})

    assert first.message == "hello"
    assert second.history == []


def test_tool_trace_event_shape():
    event = ToolTraceEvent(
        name="search_products",
        args={"query": "earbuds"},
        result={"results": []},
        ms=12,
        ok=True,
        error=None,
    )

    assert event.name == "search_products"


class FakeSession:
    def __init__(self, tool_result=None):
        self.initialized = False
        self.tool_result = tool_result

    async def initialize(self):
        self.initialized = True

    async def list_tools(self):
        return SimpleNamespace(
            tools=[
                SimpleNamespace(
                    name="search_products",
                    description="Search products",
                    input_schema={"type": "object"},
                )
            ]
        )

    async def call_tool(self, name, arguments):
        if isinstance(self.tool_result, Exception):
            raise self.tool_result
        return self.tool_result


def test_injected_session_starts_and_lists_mapped_tools():
    async def run():
        session = FakeSession()
        manager = McpSessionManager(session=session)

        await manager.start()
        tools = await manager.list_tools()

        assert session.initialized is True
        assert manager.ready is True
        assert tools == [
            {
                "name": "search_products",
                "description": "Search products",
                "input_schema": {"type": "object"},
            }
        ]
        await manager.stop()
        assert manager.ready is False

    asyncio.run(run())


def test_call_tool_parses_json_text():
    async def run():
        result = SimpleNamespace(
            content=[SimpleNamespace(type="text", text='{"count": 1}')],
            is_error=False,
            structured_content=None,
        )
        manager = McpSessionManager(session=FakeSession(result))
        await manager.start()

        value, elapsed_ms, ok, error = await manager.call_tool(
            "search_products", {"query": "earbuds"}
        )

        assert value == {"count": 1}
        assert elapsed_ms >= 0
        assert ok is True
        assert error is None

    asyncio.run(run())


def test_call_tool_prefers_json_text_over_sdk_string_wrapper():
    async def run():
        result = SimpleNamespace(
            content=[SimpleNamespace(type="text", text='{"count": 1}')],
            is_error=False,
            structured_content={"result": '{"count": 1}'},
        )
        manager = McpSessionManager(session=FakeSession(result))
        await manager.start()

        value, _, ok, error = await manager.call_tool(
            "search_products", {"query": "earbuds"}
        )

        assert value == {"count": 1}
        assert ok is True
        assert error is None

    asyncio.run(run())


def test_call_tool_reports_mcp_and_transport_errors():
    async def run():
        mcp_error = SimpleNamespace(
            content=[SimpleNamespace(type="text", text="invalid SKU")],
            is_error=True,
            structured_content=None,
        )
        manager = McpSessionManager(session=FakeSession(mcp_error))
        await manager.start()
        value, _, ok, error = await manager.call_tool("lookup_stock", {"sku": "bad"})

        assert value == "invalid SKU"
        assert ok is False
        assert error == "invalid SKU"

        manager = McpSessionManager(session=FakeSession(RuntimeError("connection lost")))
        await manager.start()
        value, _, ok, error = await manager.call_tool("lookup_stock", {"sku": "x"})

        assert value is None
        assert ok is False
        assert error == "connection lost"
        assert manager.ready is False

    asyncio.run(run())


@pytest.mark.asyncio
async def test_real_mcp_server_lists_and_calls_catalog_tools(tmp_path):
    manager = McpSessionManager(catalog_db_path=str(tmp_path / "catalog.db"))
    try:
        await manager.start()

        tools = await manager.list_tools()
        tool_names = {tool["name"] for tool in tools}
        result, _, ok, error = await manager.call_tool(
            "search_products", {"query": "AeroSound earbuds"}
        )

        assert {"search_products", "lookup_stock"} <= tool_names
        assert ok is True
        assert error is None
        assert result["count"] >= 1
        assert any(item["sku"] == "CP-1001" for item in result["results"])
    finally:
        await manager.stop()

    assert manager.ready is False
