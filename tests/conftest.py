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
