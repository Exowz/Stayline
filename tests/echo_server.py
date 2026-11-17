"""Small MCP server for exercising the shared stdio client helpers."""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from stayline.servers.results import tool_error


mcp = MCPServer("echo")


@mcp.tool()
def echo_dict() -> dict:
    """Return a small dictionary."""
    return {"value": "hello"}


@mcp.tool()
def echo_list() -> list[dict]:
    """Return a list of dictionaries."""
    return [{"value": "first"}, {"value": "second"}]


@mcp.tool()
def fail() -> dict:
    """Raise a typed error for the client tests."""
    raise tool_error("not_found", "nope")


@mcp.tool()
def patterned(contract_id: Annotated[str, Field(pattern=r"^C-\d{4}$")]) -> dict:
    """Return a valid contract identifier."""
    return {"contract_id": contract_id}


if __name__ == "__main__":
    mcp.run()
