"""Typed results and errors shared by the MCP servers."""

import json
from typing import Any, Literal

from mcp.server.mcpserver.exceptions import ToolError as McpToolError
from pydantic import BaseModel, ValidationError


ErrorCode = Literal[
    "ambiguous_match",
    "authority_mismatch",
    "contract_not_found",
    "stale_version",
    "active_seizure",
    "duplicate_notice",
    "operation_not_permitted",
    "invalid_argument",
    "not_found",
    "timeout",
    "rate_limited",
    "conflict",
    "internal",
]


class ToolError(BaseModel):
    """A typed error returned by a tool."""

    code: ErrorCode
    message: str
    retryable: bool = False
    outcome_unknown: bool = False


class ToolResult(BaseModel):
    """A typed tool response."""

    ok: bool
    data: Any | None = None
    error: ToolError | None = None


def tool_error(
    code: ErrorCode,
    message: str,
    retryable: bool = False,
    outcome_unknown: bool = False,
) -> McpToolError:
    """Wrap a typed error in the MCP exception."""
    error = ToolError(
        code=code,
        message=message,
        retryable=retryable,
        outcome_unknown=outcome_unknown,
    )
    return McpToolError(error.model_dump_json())


def parse_tool_error(text: str) -> ToolError:
    """Read a typed error from an MCP exception message."""
    start = text.find("{")
    if start >= 0:
        try:
            payload, _ = json.JSONDecoder().raw_decode(text[start:])
            return ToolError.model_validate(payload)
        except (ValueError, ValidationError):
            pass
    return ToolError(code="internal", message=text)
