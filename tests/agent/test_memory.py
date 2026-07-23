"""Conversation memory persists between turns via the graph's checkpointer.

CI-safe: no Postgres, no `GOOGLE_API_KEY`. The graph is compiled *once* with
an in-process `MemorySaver` and a stub LLM, then invoked twice with the same
`thread_id`; the second turn must see the first turn's messages in its state,
which is exactly what a wired checkpointer buys and `checkpointer=None` did not.
"""
import uuid

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver

from app.adapters.agent.graph import build_graph


def _stub_llm() -> GenericFakeChatModel:
    """A stub that answers each turn without requesting any tool call."""
    return GenericFakeChatModel(
        messages=iter([AIMessage(content="turno 1"), AIMessage(content="turno 2")])
    )


@pytest.mark.asyncio
async def test_second_turn_sees_first_turn_messages_with_same_thread() -> None:
    graph = build_graph(
        _stub_llm(), tools=[], checkpointer=MemorySaver(), guard=lambda text: None
    )
    thread_id = f"user-{uuid.uuid4()}"
    config: RunnableConfig = {"configurable": {"user_id": "u", "thread_id": thread_id}}

    await graph.ainvoke({"messages": [HumanMessage(content="hola, soy el turno uno")]}, config=config)
    second = await graph.ainvoke({"messages": [HumanMessage(content="¿qué te dije antes?")]}, config=config)

    texts = [m.text for m in second["messages"]]
    # The first turn's human + AI messages were replayed from the checkpoint,
    # so both turns' content is present in the second invocation's state.
    assert "hola, soy el turno uno" in texts
    assert "turno 1" in texts
    assert "¿qué te dije antes?" in texts
    assert "turno 2" in texts


@pytest.mark.asyncio
async def test_distinct_threads_do_not_share_memory() -> None:
    graph = build_graph(
        _stub_llm(), tools=[], checkpointer=MemorySaver(), guard=lambda text: None
    )
    thread_a: RunnableConfig = {"configurable": {"user_id": "u", "thread_id": "user-A"}}
    thread_b: RunnableConfig = {"configurable": {"user_id": "u", "thread_id": "user-B"}}

    await graph.ainvoke({"messages": [HumanMessage(content="secreto del hilo A")]}, config=thread_a)
    other = await graph.ainvoke(
        {"messages": [HumanMessage(content="hola desde hilo B")]}, config=thread_b
    )

    texts = [m.text for m in other["messages"]]
    assert "secreto del hilo A" not in texts
    assert "hola desde hilo B" in texts
