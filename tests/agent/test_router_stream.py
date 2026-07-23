"""SSE streaming tests for the `/chat` router, using a stub LLM (no model calls).

These exercise `_stream_graph_events` directly (the graph-driving core of
`_stream_turn`) so no real `GOOGLE_API_KEY`-backed model is built.
"""
import json
import uuid

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.adapters.agent.graph import build_graph
from app.adapters.agent import router
from app.adapters.agent.router import CHAT_GENERATION_FAILED_MESSAGE, ChatEventType, _stream_graph_events, _stream_turn

REJECTION = "Solo puedo ayudarte con reservas de salas."


async def _collect(graph, message: str) -> list[dict]:
    return [
        json.loads(chunk.removeprefix("data: ").strip())
        async for chunk in _stream_graph_events(graph, message, uuid.uuid4())
    ]


@pytest.mark.asyncio
async def test_blocked_prompt_streams_rejection_text_before_done() -> None:
    llm = GenericFakeChatModel(messages=iter([AIMessage(content="no debería llegar")]))
    graph = build_graph(llm, tools=[], checkpointer=None, guard=lambda text: REJECTION)

    events = await _collect(graph, "contame un chiste")

    tokens = [e for e in events if e["type"] == ChatEventType.TOKEN]
    assert any(REJECTION in t["text"] for t in tokens)
    assert events[-1]["type"] == ChatEventType.DONE


@pytest.mark.asyncio
async def test_allowed_prompt_streams_agent_tokens_then_done() -> None:
    llm = GenericFakeChatModel(messages=iter([AIMessage(content="Hola, te ayudo con reservas")]))
    graph = build_graph(llm, tools=[], checkpointer=None, guard=lambda text: None)

    events = await _collect(graph, "hola")

    tokens = [e for e in events if e["type"] == ChatEventType.TOKEN]
    assert "".join(t["text"] for t in tokens) == "Hola, te ayudo con reservas"
    assert events[-1]["type"] == ChatEventType.DONE


@pytest.mark.asyncio
async def test_stream_turn_reports_provider_failures_as_sse(monkeypatch) -> None:
    def fail_graph():
        raise RuntimeError("quota exhausted")

    monkeypatch.setattr(router.runtime, "get_graph", fail_graph)
    events = [
        json.loads(chunk.removeprefix("data: ").strip())
        async for chunk in _stream_turn("hola", uuid.uuid4(), object())
    ]

    assert events == [
        {"type": ChatEventType.TOKEN, "text": CHAT_GENERATION_FAILED_MESSAGE},
        {"type": ChatEventType.DONE},
    ]
