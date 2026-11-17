"""Check the shared stdio client helpers against a small MCP server."""

import pytest

from stayline.backend.db import snapshot
from tests.helpers import call, error, open_server, tool_schemas


@pytest.fixture
async def echo_server(seeded_db):
    """Connect to the local echo server over stdio."""
    async with open_server("tests.echo_server", seeded_db) as server:
        yield server


def test_seeded_db_starts_from_base(seeded_db):
    assert snapshot(seeded_db)["requests"]["R-0001"] == "pending"


async def test_call_returns_dict(echo_server):
    assert await call(echo_server, "echo_dict", {}) == {"value": "hello"}


async def test_call_returns_list(echo_server):
    assert await call(echo_server, "echo_list", {}) == [{"value": "first"}, {"value": "second"}]


async def test_error_parses_typed_error(echo_server):
    result = await error(echo_server, "fail", {})
    assert result.code == "not_found"
    assert result.message == "nope"


async def test_error_handles_pattern_validation(echo_server):
    result = await error(echo_server, "patterned", {"contract_id": "wrong"})
    assert result.code == "internal"


async def test_tool_schemas_include_pattern(echo_server):
    schemas = await tool_schemas(echo_server)
    assert schemas["patterned"]["properties"]["contract_id"]["pattern"] == r"^C-\d{4}$"
