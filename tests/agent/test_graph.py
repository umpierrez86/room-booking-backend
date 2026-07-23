"""Graph mechanics tests, exercised with a stub LLM (no real model calls)."""
import pytest

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage

from app.adapters.agent.graph import build_graph


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
