from collections.abc import Iterator
from pathlib import Path

import pytest

from stonk_helper.events.store import EventStore
from stonk_helper.ledger.store import LedgerStore


@pytest.fixture
def event_store(tmp_path: Path) -> Iterator[EventStore]:
    store = EventStore(tmp_path / "events.sqlite")
    yield store
    store.close()


@pytest.fixture
def ledger(tmp_path: Path) -> Iterator[LedgerStore]:
    store = LedgerStore(tmp_path / "ledger.duckdb")
    yield store
    store.close()
