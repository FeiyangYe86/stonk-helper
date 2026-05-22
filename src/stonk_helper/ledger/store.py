from importlib.resources import files
from pathlib import Path

import duckdb


class LedgerStore:
    """Portfolio + tax ledger (DuckDB). Source of truth for positions, lots, disposals, FX."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(str(self.db_path))
        self._apply_schema()

    def _apply_schema(self) -> None:
        ddl = (
            files("stonk_helper.ledger")
            .joinpath("migrations/0001_initial.sql")
            .read_text()
        )
        self._conn.execute(ddl)
        row = self._conn.execute("SELECT max(version) FROM schema_version").fetchone()
        if row is None or row[0] is None:
            self._conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (1, current_timestamp)"
            )

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        return self._conn

    def close(self) -> None:
        self._conn.close()
