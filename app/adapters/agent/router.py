"""Streaming chat endpoint for the room-booking conversational agent.

The graph is compiled once and reused across requests (see
`app.adapters.agent.runtime`) so its checkpointer can persist conversation
state between turns. Each request injects its per-request `BookingService`
and the acting `user_id` into `config["configurable"]`, and pins the
checkpoint thread to that user via `thread_id`, so a turn sees the messages
of the previous turns in the same conversation.
"""
import json
import logging
import uuid
from collections.abc import AsyncIterator, Sequence
from enum import StrEnum
from typing import Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from app.adapters.agent import runtime
from app.adapters.agent.graph import AGENT_NODE, GUARD_NODE, TOOLS_NODE
from app.adapters.agent.tools import BOOKING_CANCELLED_MESSAGE, BOOKING_CREATED_PREFIX
from app.adapters.web.deps import get_booking_service, get_current_user
from app.core.config import settings
from app.domain.services.booking_service import BookingService

logger = logging.getLogger(__name__)

SSE_MEDIA_TYPE = "text/event-stream"
BOOKING_MUTATING_TOOLS = frozenset({"create_booking", "cancel_booking"})
BOOKING_SUCCESS_MARKERS = (BOOKING_CREATED_PREFIX, BOOKING_CANCELLED_MESSAGE)
CHAT_NOT_CONFIGURED_MESSAGE = "El asistente no está disponible por el momento."
CHAT_GENERATION_FAILED_MESSAGE = "No pude completar la respuesta en este momento. Probá de nuevo en unos minutos."

StreamMode = Literal["custom", "updates"]
# NOTE: langgraph only treats stream_mode as *multi-mode* (yielding
# `(mode, payload)` pairs) when it is a `list`; a tuple is interpreted as a
# single mode spec, which silently drops the mode label and breaks unpacking.
GRAPH_STREAM_MODES: Sequence[StreamMode] = ["custom", "updates"]


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
    if not settings.google_api_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, CHAT_NOT_CONFIGURED_MESSAGE)
    return StreamingResponse(_stream_turn(body.message, uid, svc), media_type=SSE_MEDIA_TYPE)


async def _stream_turn(message: str, uid: uuid.UUID, svc: BookingService) -> AsyncIterator[str]:
    """Run one turn on the reused, checkpointed graph, yielding SSE events."""
    try:
        async for event in _stream_graph_events(runtime.get_graph(), message, uid, svc):
            yield event
    except Exception:
        # The HTTP response has already started, so communicate provider failures as SSE.
        logger.exception("Chat generation failed")
        yield _sse(ChatEventType.TOKEN, text=CHAT_GENERATION_FAILED_MESSAGE)
        yield _sse(ChatEventType.DONE)


async def _stream_graph_events(
    graph: CompiledStateGraph,
    message: str,
    uid: uuid.UUID,
    svc: BookingService | None = None,
) -> AsyncIterator[str]:
    """Stream one graph turn as SSE events, ending with a `done` event.

    `thread_id` pins the conversation to the acting user so the checkpointer
    replays earlier turns; `booking_service` carries the request-scoped service
    the tools resolve at call time. `svc` is optional so guard/plain-chat tests
    can drive a tools-less graph without a service.
    """
    configurable: dict[str, Any] = {"user_id": str(uid), "thread_id": f"user-{uid}"}
    if svc is not None:
        configurable["booking_service"] = svc
    config: RunnableConfig = {"configurable": configurable}
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
    if mode == "custom":
        return _custom_events(payload)
    return _update_events(cast("dict[str, dict[str, list[BaseMessage]]]", payload))


def _custom_events(payload: Any) -> list[str]:
    """Turn text forwarded by the agent node into token SSE events."""
    if not isinstance(payload, dict) or payload.get("type") != "token":
        return []
    text = payload.get("text")
    return [_sse(ChatEventType.TOKEN, text=text)] if isinstance(text, str) and text else []


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
