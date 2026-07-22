"""Streaming chat endpoint for the room-booking conversational agent.

The LLM is built lazily, on first use, rather than at import time: eagerly
constructing it (as `init_chat_model` does) requires a live
`GOOGLE_API_KEY`, which is unavailable while running the test suite and
would otherwise break every test that imports `app.adapters.web.main`.
The checkpointer stays `None` here; a Postgres-backed one (`.setup()` run
during the app's lifespan) is wired in at integration time.
"""
import json
import uuid
from collections.abc import AsyncIterator, Sequence
from enum import StrEnum
from functools import lru_cache
from typing import Any, Literal, cast

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from app.adapters.agent import context
from app.adapters.agent.graph import AGENT_NODE, GUARD_NODE, TOOLS_NODE, build_graph
from app.adapters.agent.guard import make_guard
from app.adapters.agent.tools import BOOKING_CANCELLED_MESSAGE, BOOKING_CREATED_PREFIX, make_tools
from app.adapters.web.deps import get_booking_service, get_current_user
from app.core.config import settings
from app.domain.services.booking_service import BookingService

SSE_MEDIA_TYPE = "text/event-stream"
BOOKING_MUTATING_TOOLS = frozenset({"create_booking", "cancel_booking"})
BOOKING_SUCCESS_MARKERS = (BOOKING_CREATED_PREFIX, BOOKING_CANCELLED_MESSAGE)

StreamMode = Literal["messages", "updates"]
# NOTE: langgraph only treats stream_mode as *multi-mode* (yielding
# `(mode, payload)` pairs) when it is a `list`; a tuple is interpreted as a
# single mode spec, which silently drops the mode label and breaks unpacking.
GRAPH_STREAM_MODES: Sequence[StreamMode] = ["messages", "updates"]


class ChatEventType(StrEnum):
    """The `type` field of every event streamed over `/chat`."""

    TOKEN = "token"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    BOOKING_CHANGED = "booking_changed"
    DONE = "done"


class ChatIn(BaseModel):
    """A single chat turn submitted by the authenticated user."""

    message: str


router = APIRouter(tags=["chat"])


@lru_cache(maxsize=1)
def _get_llm() -> BaseChatModel:
    """Build the chat model on first use (requires `GOOGLE_API_KEY`)."""
    return init_chat_model(settings.llm_model)


@router.post("/chat")
async def chat(
    body: ChatIn,
    uid: uuid.UUID = Depends(get_current_user),
    svc: BookingService = Depends(get_booking_service),
) -> StreamingResponse:
    """Stream one agent turn as Server-Sent Events.

    `uid` comes from the verified JWT and is injected into
    `config["configurable"]["user_id"]`; it is never read from `body`.
    """
    return StreamingResponse(_stream_turn(body.message, uid, svc), media_type=SSE_MEDIA_TYPE)


async def _stream_turn(message: str, uid: uuid.UUID, svc: BookingService) -> AsyncIterator[str]:
    """Run one graph turn, yielding SSE-formatted agent events."""
    tools = make_tools(svc, context.current_user_id)
    graph = build_graph(_get_llm(), tools, checkpointer=None, guard=make_guard())
    async for event in _stream_graph_events(graph, message, uid):
        yield event


async def _stream_graph_events(
    graph: CompiledStateGraph, message: str, uid: uuid.UUID
) -> AsyncIterator[str]:
    """Stream one graph turn as SSE events, ending with a `done` event."""
    config: RunnableConfig = {"configurable": {"user_id": str(uid), "thread_id": f"user-{uid}"}}
    graph_input = {"messages": [HumanMessage(content=message)]}
    async for mode, payload in graph.astream(
        graph_input, config=config, stream_mode=GRAPH_STREAM_MODES
    ):
        for event in _events_for(cast("StreamMode", mode), payload):
            yield event
    yield _sse(ChatEventType.DONE)


def _events_for(mode: StreamMode, payload: Any) -> list[str]:
    """Dispatch one `astream` chunk to the matching per-mode formatter.

    `astream`'s multi-mode overload only widens to `dict[str, Any] | Any` in
    langgraph's stubs; each mode's real shape is asserted here.
    """
    if mode == "messages":
        return _message_event(payload)
    return _update_events(cast("dict[str, dict[str, list[BaseMessage]]]", payload))


def _message_event(payload: Any) -> list[str]:
    """Turn one `messages`-mode chunk into `token` events from the agent node.

    `payload` is typed `Any`: `astream(..., stream_mode=[...])` (multi-mode)
    only widens to `dict[str, Any] | Any` in langgraph's own type stubs, so
    each mode's shape is validated here rather than at the call site.
    """
    message, metadata = payload
    if metadata.get("langgraph_node") != AGENT_NODE or not message.text:
        return []
    return [_sse(ChatEventType.TOKEN, text=message.text)]


def _update_events(payload: dict[str, dict[str, list[BaseMessage]]]) -> list[str]:
    """Turn one `updates`-mode chunk into stream events.

    Covers the guard's static rejection (emitted as `token`, since it never
    passes through the LLM and so never appears as agent-node tokens) plus the
    agent's `tool_start`/`tool_end`/`booking_changed` events.
    """
    events: list[str] = []
    guard_update = payload.get(GUARD_NODE)
    if guard_update:
        events.extend(_guard_rejection_events(guard_update.get("messages", [])))
    agent_update = payload.get(AGENT_NODE)
    if agent_update:
        events.extend(_tool_start_events(agent_update["messages"][-1]))
    tools_update = payload.get(TOOLS_NODE)
    if tools_update:
        for tool_message in tools_update["messages"]:
            if isinstance(tool_message, ToolMessage):
                events.extend(_tool_end_events(tool_message))
    return events


def _guard_rejection_events(messages: list[BaseMessage]) -> list[str]:
    """Emit the guard's rejection text as `token` events, so a blocked prompt
    reaches the client instead of only a bare `done`."""
    return [_sse(ChatEventType.TOKEN, text=message.text) for message in messages if message.text]


def _tool_start_events(last_message: BaseMessage) -> list[str]:
    """Emit one `tool_start` per tool call the agent just requested."""
    tool_calls = getattr(last_message, "tool_calls", None) or []
    return [_sse(ChatEventType.TOOL_START, tool=call["name"], args=call["args"]) for call in tool_calls]


def _tool_end_events(tool_message: ToolMessage) -> list[str]:
    """Emit `tool_end`, plus `booking_changed` if a mutation just succeeded."""
    events = [_sse(ChatEventType.TOOL_END, tool=tool_message.name, result=tool_message.text)]
    if _booking_was_mutated(tool_message):
        events.append(_sse(ChatEventType.BOOKING_CHANGED, tool=tool_message.name))
    return events


def _booking_was_mutated(tool_message: ToolMessage) -> bool:
    """Return True if a booking-mutating tool reports success (not a domain error)."""
    is_mutating_tool = tool_message.name in BOOKING_MUTATING_TOOLS
    looks_successful = tool_message.text.startswith(BOOKING_SUCCESS_MARKERS)
    return is_mutating_tool and looks_successful


def _sse(event_type: ChatEventType, **fields: object) -> str:
    """Format a single Server-Sent Event payload."""
    return f"data: {json.dumps({'type': str(event_type), **fields})}\n\n"
