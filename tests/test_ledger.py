from pathlib import Path

from stonk_helper.ledger.store import LedgerStore

EXPECTED_TABLES = {
    "fx_rates",
    "fills",
    "lots",
    "disposals",
    "dividends",
    "corporate_actions",
    "schema_version",
}


def test_schema_creates_all_tables(ledger: LedgerStore) -> None:
    rows = ledger.conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
    ).fetchall()
    names = {r[0] for r in rows}
    assert names >= EXPECTED_TABLES


def test_schema_version_recorded(ledger: LedgerStore) -> None:
    rows = ledger.conn.execute("SELECT version FROM schema_version").fetchall()
    assert rows == [(1,)]


def test_re_open_does_not_duplicate_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "ledger.duckdb"
    s1 = LedgerStore(path)
    s1.close()
    s2 = LedgerStore(path)
    rows = s2.conn.execute("SELECT count(*) FROM schema_version").fetchall()
    s2.close()
    assert rows == [(1,)]
