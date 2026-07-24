"""Graph mechanics tests, exercised with a stub LLM (no real model calls)."""
import pytest

from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool

from app.adapters.agent.graph import build_graph


class ToolCallingFake(BaseChatModel):
    responses: list[AIMessage]
    position: int = 0

    @property
    def _llm_type(self) -> str:
        return "tool-calling-fake"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        response = self.responses[self.position]
        self.position += 1
        return ChatResult(generations=[ChatGeneration(message=response)])


@tool
def echo(value: str) -> str:
    """Return the received value."""
    return f"tool result {value}"


@pytest.mark.asyncio
async def test_graph_routes_to_end_without_toolcalls() -> None:
    # el stub responde sin tool-calls -> el grafo termina en un turno
    llm = GenericFakeChatModel(messages=iter([AIMessage(content="Hola, ¿en qué te ayudo?")]))
    graph = build_graph(llm, tools=[], checkpointer=None, guard=lambda text: None)
    out = await graph.ainvoke(
        {"messages": [HumanMessage(content="hola")]},
        config={"configurable": {"user_id": "x", "thread_id": "t"}},
    )
    assert "ayudo" in out["messages"][-1].content


@pytest.mark.asyncio
async def test_guard_blocks_offtopic() -> None:
    llm = GenericFakeChatModel(messages=iter([AIMessage(content="no debería llegar")]))
    graph = build_graph(
        llm,
        tools=[],
        checkpointer=None,
        guard=lambda text: "Solo puedo ayudarte con reservas de salas.",
    )
    out = await graph.ainvoke(
        {"messages": [HumanMessage(content="contame un chiste")]},
        config={"configurable": {"user_id": "x", "thread_id": "t"}},
    )
    assert "reservas de salas" in out["messages"][-1].content


@pytest.mark.asyncio
async def test_graph_runs_tool_and_returns_to_agent() -> None:
    llm = ToolCallingFake(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "echo",
                        "args": {"value": "ok"},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="respuesta final"),
        ]
    )
    graph = build_graph(llm, tools=[echo], checkpointer=None, guard=lambda text: None)

    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="usá la tool")]},
        config={"configurable": {"user_id": "x", "thread_id": "t"}},
    )

    assert any(
        isinstance(message, ToolMessage) and message.content == "tool result ok"
        for message in result["messages"]
    )
    assert result["messages"][-1].content == "respuesta final"
