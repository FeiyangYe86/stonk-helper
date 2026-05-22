-- AUD-per-USD rates, snapped on trade date (RBA).
CREATE TABLE IF NOT EXISTS fx_rates (
    rate_date    DATE   PRIMARY KEY,
    aud_per_usd  DOUBLE NOT NULL,
    source       TEXT   NOT NULL DEFAULT 'RBA'
);

-- Every IBKR execution. Source of truth for trade history.
CREATE TABLE IF NOT EXISTS fills (
    fill_id        TEXT   PRIMARY KEY,         -- IBKR exec ID
    order_id       TEXT   NOT NULL,
    symbol         TEXT   NOT NULL,
    side           TEXT   NOT NULL,            -- BUY | SELL
    quantity       DOUBLE NOT NULL,
    price_usd      DOUBLE NOT NULL,
    commission_usd DOUBLE NOT NULL DEFAULT 0,
    executed_at    TIMESTAMP NOT NULL,         -- UTC
    trade_date     DATE   NOT NULL,            -- Sydney calendar — drives FX + CGT
    aud_per_usd    DOUBLE NOT NULL,            -- snapped at trade_date
    proceeds_usd   DOUBLE NOT NULL,            -- signed: +SELL, -BUY
    proceeds_aud   DOUBLE NOT NULL,
    strategy       TEXT,
    account        TEXT   NOT NULL,
    raw            JSON                         -- full IBKR exec for forensics
);

-- Open + closed parcels. FIFO by default; specific-ID supported via explicit selection.
CREATE TABLE IF NOT EXISTS lots (
    lot_id              TEXT   PRIMARY KEY,
    symbol              TEXT   NOT NULL,
    acquired_at         TIMESTAMP NOT NULL,
    acquired_date       DATE   NOT NULL,       -- for CGT holding period (Sydney)
    quantity_open       DOUBLE NOT NULL,
    quantity_orig       DOUBLE NOT NULL,
    cost_usd            DOUBLE NOT NULL,       -- per share
    cost_aud            DOUBLE NOT NULL,       -- per share, AUD at acquired_date
    commission_usd      DOUBLE NOT NULL DEFAULT 0,
    acquisition_fill_id TEXT   NOT NULL,
    account             TEXT   NOT NULL,
    strategy            TEXT
);

-- A disposal closes (part of) a lot. One row per (lot, sell fill) pair.
CREATE TABLE IF NOT EXISTS disposals (
    disposal_id       TEXT   PRIMARY KEY,
    lot_id            TEXT   NOT NULL REFERENCES lots(lot_id),
    fill_id           TEXT   NOT NULL REFERENCES fills(fill_id),
    disposed_at       TIMESTAMP NOT NULL,
    disposed_date     DATE   NOT NULL,
    quantity          DOUBLE NOT NULL,
    proceeds_usd      DOUBLE NOT NULL,         -- total, net of commission
    proceeds_aud      DOUBLE NOT NULL,
    cost_base_usd     DOUBLE NOT NULL,         -- total
    cost_base_aud     DOUBLE NOT NULL,
    gain_loss_usd     DOUBLE NOT NULL,
    gain_loss_aud     DOUBLE NOT NULL,
    holding_days      INTEGER NOT NULL,
    discount_eligible BOOLEAN NOT NULL         -- >= 365 days, individual taxpayer
);

-- US dividends. Withholding feeds the AU foreign income tax offset (FITO).
CREATE TABLE IF NOT EXISTS dividends (
    dividend_id     TEXT   PRIMARY KEY,
    symbol          TEXT   NOT NULL,
    pay_date        DATE   NOT NULL,
    gross_usd       DOUBLE NOT NULL,
    withholding_usd DOUBLE NOT NULL,
    net_usd         DOUBLE NOT NULL,
    aud_per_usd     DOUBLE NOT NULL,
    gross_aud       DOUBLE NOT NULL,
    withholding_aud DOUBLE NOT NULL,
    net_aud         DOUBLE NOT NULL,
    account         TEXT   NOT NULL
);

-- Splits, mergers, spin-offs. Applied to lots by the ledger; raw payload kept for audit.
CREATE TABLE IF NOT EXISTS corporate_actions (
    ca_id          TEXT PRIMARY KEY,
    symbol         TEXT NOT NULL,
    effective_date DATE NOT NULL,
    ca_type        TEXT NOT NULL,              -- SPLIT | MERGER | SPIN_OFF | NAME_CHANGE
    payload        JSON NOT NULL
);

CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER  PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL
);
