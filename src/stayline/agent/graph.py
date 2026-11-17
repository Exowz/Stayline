"""Build the guarded LangGraph state machine."""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from stayline.agent.nodes import make_nodes
from stayline.agent.router import router
from stayline.agent.state import AgentState


def build_graph(harness, llm, store=None, checkpointer=None) -> CompiledStateGraph:
    """Compile the async graph with a checkpointer for approvals."""
    nodes = make_nodes(harness, llm, store)
    graph = StateGraph(AgentState)
    destinations = {
        "prepare": ("approve", "think"),
        "approve": ("write", "think"),
        "write": ("prepare", "give_up", "verify"),
    }
    for name, node in nodes.items():
        graph.add_node(name, node, destinations=destinations.get(name))
    graph.add_edge(START, "recall")
    graph.add_edge("recall", "think")
    graph.add_conditional_edges("think", router, {
        "__end__": END,
        "give_up": "give_up", "remind": "remind", "remember": "remember",
        "prepare": "prepare", "read_tool": "read_tool",
    })
    for name in ("remind", "remember", "read_tool", "verify"):
        graph.add_edge(name, "think")
    graph.add_edge("give_up", END)
    return graph.compile(checkpointer=checkpointer or InMemorySaver())
