"""Compiles the agent graph once and wires its conversation checkpointer.

Memory between turns needs a *single* compiled graph reused across requests,
backed by a checkpointer keyed on `thread_id`. Re-arming the graph per request
with `checkpointer=None` (the old behaviour) discarded all state, so the agent
never remembered anything the user said in an earlier turn.

`AsyncPostgresSaver` persists that state across restarts in a real deployment;
tests and local runs without Postgres fall back to an in-process `MemorySaver`.
The LLM is still built lazily (on first request), so importing this module
never requires a live `GOOGLE_API_KEY` — which keeps the test suite importable.
"""
import contextlib
from collections.abc import AsyncIterator
from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from app.adapters.agent import context
from app.adapters.agent.graph import build_graph
from app.adapters.agent.guard import make_guard
from app.adapters.agent.tools import make_tools
from app.core.config import settings

# The single compiled graph reused across requests. Set once during the app
# lifespan (Postgres-backed), or built lazily with a `MemorySaver` fallback.
_graph: CompiledStateGraph | None = None


@lru_cache(maxsize=1)
def _get_llm() -> BaseChatModel:
    """Build the chat model on first use (requires `GOOGLE_API_KEY`)."""
    return init_chat_model(settings.llm_model)


def compile_graph(
    checkpointer: BaseCheckpointSaver, llm: BaseChatModel | None = None
) -> CompiledStateGraph:
    """Compile the agent graph against `checkpointer`, resolving deps per call.

    `llm` is injectable so tests can compile with a stub model; production
    passes `None` and the real, lazily-built model is used.
    """
    tools = make_tools(context.current_booking_service, context.current_user_id)
    return build_graph(llm or _get_llm(), tools, checkpointer=checkpointer, guard=make_guard())


def set_graph(graph: CompiledStateGraph) -> None:
    """Install the reused graph (called from the app lifespan)."""
    global _graph
    _graph = graph


def get_graph() -> CompiledStateGraph:
    """Return the reused compiled graph, lazily building a `MemorySaver`-backed
    one if the lifespan never installed a checkpointed graph (local fallback)."""
    global _graph
    if _graph is None:
        _graph = compile_graph(MemorySaver())
    return _graph


def _use_postgres() -> bool:
    """True when a Postgres URL is configured and we are not under test."""
    return not settings.testing and settings.database_url.startswith("postgres")


def _pg_conn_string() -> str:
    """Translate the SQLAlchemy URL into a psycopg connection string.

    `AsyncPostgresSaver` talks to psycopg directly, which does not understand
    SQLAlchemy's `+psycopg` driver marker, so it is stripped here.
    """
    return settings.database_url.replace("+psycopg", "")


@contextlib.asynccontextmanager
async def lifespan_graph() -> AsyncIterator[None]:
    """Install the reused graph for the app's lifetime, wiring the checkpointer.

    With Postgres configured, opens an `AsyncPostgresSaver`, runs its `.setup()`
    (creating the checkpoint tables if missing) and keeps the connection open
    for the whole app lifetime; otherwise falls back to an in-process
    `MemorySaver`.
    """
    if _use_postgres():
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        async with AsyncPostgresSaver.from_conn_string(_pg_conn_string()) as saver:
            await saver.setup()
            set_graph(compile_graph(saver))
            yield
    else:
        set_graph(compile_graph(MemorySaver()))
        yield
