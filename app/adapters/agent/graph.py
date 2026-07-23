"""In-process ReAct-style graph: guard -> agent <-> tools.

The graph never reimplements booking rules: `tools` wrap `BookingService`,
and the guard rejects off-topic/injection input before the LLM ever runs.
"""
from collections.abc import Callable
from typing import Annotated, TypedDict, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.config import get_stream_writer
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from app.adapters.agent.prompt import make_system_prompt
from app.core.config import settings

GUARD_NODE = "guard"
AGENT_NODE = "agent"
TOOLS_NODE = "tools"

GuardFn = Callable[[str], str | None]


class AgentState(TypedDict):
    """Conversation state threaded through the graph."""

    messages: Annotated[list[BaseMessage], add_messages]


def build_graph(
    llm: BaseChatModel,
    tools: list[BaseTool],
    checkpointer: BaseCheckpointSaver | None,
    guard: GuardFn,
) -> CompiledStateGraph:
    """Compile the `guard -> agent <-> tools` graph.

    `tools=[]` yields a guard/agent-only graph (used to test the guard and
    the plain-chat path with an LLM stub, without wiring `ToolNode`).
    """
    llm_with_tools = llm.bind_tools(tools) if tools else llm

    def guard_node(state: AgentState) -> dict[str, list[BaseMessage]]:
        rejection = guard(state["messages"][-1].text)
        if rejection is None:
            return {}
        return {"messages": [AIMessage(content=rejection)]}

    def route_after_guard(state: AgentState) -> str:
        return END if isinstance(state["messages"][-1], AIMessage) else AGENT_NODE

    async def agent_node(state: AgentState) -> dict[str, list[BaseMessage]]:
        """Keep one complete graph message while forwarding text immediately."""
        messages: list[BaseMessage] = [
            SystemMessage(content=make_system_prompt(settings.app_timezone)),
            *state["messages"],
        ]
        writer = get_stream_writer()
        response: BaseMessage | None = None
        async for chunk in llm_with_tools.astream(messages):
            if chunk.text:
                writer({"type": "token", "text": chunk.text})
            response = cast(BaseMessage, chunk if response is None else response + chunk)

        if response is None:
            raise RuntimeError("The language model returned no response")
        return {"messages": [response]}

    def route_after_agent(state: AgentState) -> str:
        tool_calls = getattr(state["messages"][-1], "tool_calls", None)
        return TOOLS_NODE if tool_calls else END

    graph = StateGraph(AgentState)
    graph.add_node(GUARD_NODE, guard_node)
    graph.add_node(AGENT_NODE, agent_node)
    graph.add_edge(START, GUARD_NODE)
    graph.add_conditional_edges(GUARD_NODE, route_after_guard)

    if tools:
        graph.add_node(TOOLS_NODE, ToolNode(tools))
        graph.add_conditional_edges(AGENT_NODE, route_after_agent)
        graph.add_edge(TOOLS_NODE, AGENT_NODE)
    else:
        graph.add_edge(AGENT_NODE, END)

    return graph.compile(checkpointer=checkpointer)
