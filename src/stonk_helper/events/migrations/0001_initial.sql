-- Append-only event log. Single table; payloads are JSON for forward compatibility.
CREATE TABLE IF NOT EXISTS events (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at    TEXT    NOT NULL,           -- ISO 8601 UTC, business time
    recorded_at    TEXT    NOT NULL,           -- ISO 8601 UTC, write time
    event_type     TEXT    NOT NULL,
    event_version  INTEGER NOT NULL,
    aggregate      TEXT,                       -- symbol / order_id / account
    correlation_id TEXT,                       -- groups related events across components
    payload        TEXT    NOT NULL            -- JSON; includes full event including type
);

CREATE INDEX IF NOT EXISTS idx_events_type        ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_aggregate   ON events(aggregate);
CREATE INDEX IF NOT EXISTS idx_events_occurred    ON events(occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_correlation ON events(correlation_id);

CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT    NOT NULL
);
