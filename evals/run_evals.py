"""Manual LangSmith runner for the room-booking agent's tool-selection evals.

Run with: `uv run python -m evals.run_evals`
Requires `GOOGLE_API_KEY` (LLM) and `LANGSMITH_API_KEY` (reporting). Hits the
real LLM, so this is a quality-check script, not a CI gate: the CI-covered
piece is `evals.evaluators.tool_match`, already exercised by
`tests/evals/test_evaluators.py`.

A `BookingService` wired with in-memory fakes (seeded with rooms A-E) plays
the target's domain layer, so tool calls are real but never touch prod data.
"""
import uuid
from collections.abc import Callable
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langsmith import Client
from langsmith.evaluation import evaluate

from app.adapters.agent.graph import build_graph
from app.adapters.agent.guard import make_guard
from app.adapters.agent.tools import make_tools
from app.adapters.system_clock import SystemClock
from app.adapters.web.metrics import NoOpMetrics
from app.core.config import settings
from app.domain import timeutils as tu
from app.domain.entities import Room
from app.domain.services.booking_service import BookingService
from evals.dataset import CASES
from evals.evaluators import parse_judge_score, tool_match
from tests.fakes import InMemoryBookingRepository, InMemoryRoomCatalog

DATASET_NAME = "room-booking-agent"
DATASET_DESCRIPTION = "Natural-language requests mapped to the expected agent tool call."
EXPERIMENT_PREFIX = "tool-match"
ROOM_CAPACITIES = {"A": 4, "B": 6, "C": 6, "D": 8, "E": 10}
EVAL_THREAD_ID = "eval"

# LLM-as-judge rubric: scores the agent's final answer on clarity, correctness
# and on-topic-ness for room bookings. Kept terse and asks for a bare number so
# `parse_judge_score` has the least to disambiguate.
JUDGE_PROMPT = (
    "Sos un evaluador de calidad de un asistente de reservas de salas. "
    "Puntuá la RESPUESTA del asistente frente al PEDIDO del usuario: "
    "¿es clara, correcta y on-topic sobre reservas de salas? "
    "Respondé SOLO con un número entre 0 y 1 (1 = excelente, 0 = mala).\n\n"
    "PEDIDO:\n{input}\n\nRESPUESTA:\n{response}\n\nPuntaje:"
)

Target = Callable[[dict[str, Any]], dict[str, Any]]
Evaluator = Callable[[Any, Any], dict[str, Any]]


def _seeded_service() -> BookingService:
    """Build a `BookingService` over in-memory fakes seeded with rooms A-E."""
    rooms = [Room(code, capacity) for code, capacity in ROOM_CAPACITIES.items()]
    return BookingService(
        InMemoryBookingRepository(), InMemoryRoomCatalog(rooms), SystemClock(), NoOpMetrics(),
        settings.app_timezone, tu.parse_hhmm(settings.booking_start), tu.parse_hhmm(settings.booking_end),
    )


def _make_target(svc: BookingService, user_id: uuid.UUID) -> Target:
    """Build a LangSmith target: runs one agent turn, returns its tool calls."""
    llm = init_chat_model(settings.llm_model)
    graph = build_graph(llm, make_tools(svc, lambda: user_id), checkpointer=None, guard=make_guard())

    def target(inputs: dict[str, Any]) -> dict[str, Any]:
        result = graph.invoke(
            {"messages": [HumanMessage(content=inputs["input"])]},
            config={"configurable": {"user_id": str(user_id), "thread_id": EVAL_THREAD_ID}},
        )
        calls = [
            {"name": call["name"], "args": call["args"]}
            for message in result["messages"]
            for call in getattr(message, "tool_calls", None) or []
        ]
        return {"tool_calls": calls, "response": _message_text(result["messages"][-1])}

    return target


def _message_text(message: BaseMessage) -> str:
    """Return a message's text content, whatever its content shape."""
    text = getattr(message, "text", None)
    return text() if callable(text) else str(text or message.content)


def correct_tool(run: Any, example: Any) -> dict[str, Any]:
    """LangSmith evaluator: delegates to the pure, unit-tested `tool_match`."""
    ok = tool_match(
        run.outputs["tool_calls"], example.outputs["expected_tool"], example.outputs["expected_args"]
    )
    return {"key": "correct_tool", "score": 1.0 if ok else 0.0}


def _make_response_quality(judge: BaseChatModel) -> Evaluator:
    """Build an LLM-as-judge evaluator scoring the agent's final response 0..1."""

    def response_quality(run: Any, example: Any) -> dict[str, Any]:
        prompt = JUDGE_PROMPT.format(
            input=example.inputs["input"], response=run.outputs["response"]
        )
        reply = judge.invoke([HumanMessage(content=prompt)])
        return {"key": "response_quality", "score": parse_judge_score(_message_text(reply))}

    return response_quality


def _ensure_dataset(client: Client) -> None:
    """Create the LangSmith dataset from `CASES`, unless it already exists."""
    if client.has_dataset(dataset_name=DATASET_NAME):
        return
    dataset = client.create_dataset(DATASET_NAME, description=DATASET_DESCRIPTION)
    client.create_examples(
        dataset_id=dataset.id,
        inputs=[{"input": case["input"]} for case in CASES],
        outputs=[
            {"expected_tool": case["expected_tool"], "expected_args": case["expected_args"]}
            for case in CASES
        ],
    )


def run_evals() -> None:
    """Seed the LangSmith dataset (if needed) and evaluate the agent against it."""
    client = Client()
    _ensure_dataset(client)
    svc = _seeded_service()
    target = _make_target(svc, uuid.uuid4())
    response_quality = _make_response_quality(init_chat_model(settings.llm_model))
    evaluate(
        target,
        data=DATASET_NAME,
        evaluators=[correct_tool, response_quality],
        client=client,
        experiment_prefix=EXPERIMENT_PREFIX,
    )


if __name__ == "__main__":
    run_evals()
