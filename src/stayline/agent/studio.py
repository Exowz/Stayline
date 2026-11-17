"""Lazy LangGraph Studio entry point for the local agent."""

from contextlib import asynccontextmanager

from stayline.agent.graph import build_graph
from stayline.agent.harness import Harness
from stayline.agent.llm import LLM, OpenRouterLLM
from stayline.config import Settings, load_settings


@asynccontextmanager
async def build_studio_graph(
    settings: Settings, llm: LLM, modules: tuple[str, ...] | None = None,
):
    """Open the tools and yield a graph without an owned checkpointer."""
    harness_args = {"modules": modules} if modules is not None else {}
    async with Harness(settings, **harness_args) as harness:
        yield build_graph(harness, llm, checkpointer=None)


@asynccontextmanager
async def agent():
    """Load the default Studio graph when entered."""
    settings = load_settings()
    async with build_studio_graph(settings, OpenRouterLLM(settings)) as graph:
        yield graph
