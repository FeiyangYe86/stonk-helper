import json
import sqlite3
from collections.abc import Iterator
from importlib.resources import files
from pathlib import Path
from typing import Any

from ..clock import utcnow
from .types import Event, EventAdapter


class EventStore:
    """Append-only event log backed by SQLite (WAL mode)."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        self._apply_schema()

    def _apply_schema(self) -> None:
        ddl = (
            files("stonk_helper.events")
            .joinpath("migrations/0001_initial.sql")
            .read_text()
        )
        self._conn.executescript(ddl)
        current = self._conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        if current is None:
            self._conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (1, ?)",
                (utcnow().isoformat(),),
            )
        self._conn.commit()

    def append(self, event: Event) -> int:
        full = event.model_dump(mode="json")
        cur = self._conn.execute(
            """
            INSERT INTO events (occurred_at, recorded_at, event_type, event_version,
                                aggregate, correlation_id, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.occurred_at.isoformat(),
                utcnow().isoformat(),
                event.event_type,
                event.event_version,
                event.aggregate,
                event.correlation_id,
                json.dumps(full),
            ),
        )
        self._conn.commit()
        assert cur.lastrowid is not None
        return int(cur.lastrowid)

    def replay(self, event_type: str | None = None) -> Iterator[dict[str, Any]]:
        sql = (
            "SELECT id, occurred_at, event_type, event_version, "
            "aggregate, correlation_id, payload FROM events"
        )
        params: tuple[Any, ...] = ()
        if event_type:
            sql += " WHERE event_type = ?"
            params = (event_type,)
        sql += " ORDER BY id ASC"
        for row in self._conn.execute(sql, params):
            yield {
                "id": row[0],
                "occurred_at": row[1],
                "event_type": row[2],
                "event_version": row[3],
                "aggregate": row[4],
                "correlation_id": row[5],
                "payload": json.loads(row[6]),
            }

    def replay_typed(self, event_type: str | None = None) -> Iterator[Event]:
        for row in self.replay(event_type):
            yield EventAdapter.validate_python(row["payload"])

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    def close(self) -> None:
        self._conn.close()
