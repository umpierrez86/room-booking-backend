"""Tests for the agent runtime lifecycle."""
import pytest

from app.adapters.agent import runtime


@pytest.mark.asyncio
async def test_lifespan_defers_graph_compilation_until_first_chat(monkeypatch) -> None:
    runtime._graph = None
    runtime._checkpointer = None
    monkeypatch.setattr(runtime, "_use_postgres", lambda: False)

    def fail_if_compiled(*_args: object, **_kwargs: object):
        raise AssertionError("the LLM graph must not compile during startup")

    monkeypatch.setattr(runtime, "compile_graph", fail_if_compiled)

    async with runtime.lifespan_graph():
        assert runtime._graph is None
        assert runtime._checkpointer is not None

    assert runtime._graph is None
    assert runtime._checkpointer is None
