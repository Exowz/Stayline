"""Real stdio MCP client helpers shared by server tests."""

import json
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from agents.mcp import MCPServerStdio

from stayline.servers.results import ToolError, parse_tool_error


@asynccontextmanager
async def open_server(
    module: str, db_path: str, extra_env: dict | None = None
) -> AsyncIterator[MCPServerStdio]:
    """Start a module over stdio and yield its connected MCP client."""
    env = {**os.environ, "STAYLINE_DB": db_path, **(extra_env or {})}
    async with MCPServerStdio(
        {"command": sys.executable, "args": ["-m", module], "env": env}
    ) as server:
        yield server


async def call(server: MCPServerStdio, tool: str, args: dict) -> dict | list:
    """Call a tool and decode its successful Python value."""
    result = await server.call_tool(tool, args)
    assert not result.is_error, result.content
    structured = result.structured_content
    if structured is not None:
        if isinstance(structured, dict) and set(structured) == {"result"}:
            return structured["result"]
        return structured
    values = [json.loads(item.text) for item in result.content]
    return values[0] if len(values) == 1 else values


async def error(server: MCPServerStdio, tool: str, args: dict) -> ToolError:
    """Call a tool and parse a typed or validation error."""
    result = await server.call_tool(tool, args)
    assert result.is_error, result.content
    return parse_tool_error(result.content[0].text)


async def tool_schemas(server: MCPServerStdio) -> dict[str, dict]:
    """Map each tool name to its input schema."""
    return {tool.name: tool.input_schema for tool in await server.list_tools()}
