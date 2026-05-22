# stonk-helper

Personal multi-agent system for trading US equities (Nasdaq + S&P) via IBKR, with
research, risk control, AU tax reporting, and a learning loop. Single-user.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the canonical design.

**Status:** Phase 1 — foundations. Event store + ledger schemas, time/config/logging
primitives, test harness. Broker connection and first paper order: next step.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/) (or use `python -m venv` + `pip`).

```bash
uv venv
uv pip install -e ".[dev]"
```

## Test

```bash
uv run pytest
```

## Layout

```
src/stonk_helper/
  clock.py              UTC / Australia-Sydney / America-New_York helpers, AU FY math
  config.py             YAML config loading (Pydantic-validated)
  logging.py            structlog wiring
  events/               Append-only event store (SQLite, WAL)
  ledger/               Portfolio + tax ledger (DuckDB)
config/                 Runtime config (default.yaml)
docker-compose.yml      IB Gateway container (paper / live)
tests/                  Pytest
ARCHITECTURE.md         Canonical design doc
```

## Run modes

`config.run_mode`: `paper` | `shadow` | `live`. Live requires explicit confirmation
at process start — see ARCHITECTURE.md §6.3.

## License

Personal use only. Not for redistribution or external advice — see ARCHITECTURE.md §6.8.
