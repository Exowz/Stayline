"""Shared database and stdio server fixtures."""

from pathlib import Path

import pytest

from stayline.backend.db import reset_from_seed
from tests.helpers import open_server


@pytest.fixture
def seeded_db(tmp_path: Path) -> str:
    """Reset a database from the base seed and return its path."""
    db_path = str(tmp_path / "stayline.sqlite")
    seed_path = Path(__file__).resolve().parents[1] / "seeds" / "base.json"
    reset_from_seed(str(seed_path), db_path)
    return db_path


@pytest.fixture
async def justice(seeded_db: str):
    """Connect to the justice reference server when requested."""
    async with open_server("stayline.servers.justice_reference", seeded_db) as server:
        yield server


@pytest.fixture
async def insurer(seeded_db: str):
    """Connect to the insurer contracts server when requested."""
    async with open_server("stayline.servers.insurer_contracts", seeded_db) as server:
        yield server


@pytest.fixture
async def harness(seeded_db: str):
    """Open the harness against the available insurer and echo servers."""
    from stayline.agent.harness import Harness
    from stayline.config import load_settings

    modules = ("stayline.servers.insurer_contracts", "tests.echo_server")
    async with Harness(load_settings(db_path=seeded_db), modules=modules) as client:
        yield client
