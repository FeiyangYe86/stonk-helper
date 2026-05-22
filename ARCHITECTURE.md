# stonk-helper — Architecture

A personal multi-agent system for trading US equities (Nasdaq + S&P) through IBKR, with research, risk control, AU tax reporting, and a learning loop. Single-user, runs on the owner's hardware, no external users.

This document is the canonical high-level design. Code is not yet written. Open questions are tracked in §9.

---

## 1. Goals

1. Place trades on IBKR (paper + live) from system-generated signals.
2. Maintain a complete, reconciled record of positions, lots, trades, dividends, corporate actions, and FX, in both USD and AUD.
3. Produce ATO-ready outputs at end of Australian financial year (30 June) for myTax / accountant handoff.
4. Run pluggable trading strategies behind a stable interface so strategies can be added, removed, A/B-tested, or shadow-run without touching the rest of the system.
5. Continuously analyze Nasdaq/S&P constituents across technicals, fundamentals, macro, geopolitics, and news, and feed structured insights to the strategy layer.
6. Learn from its own predictions: every call is scored after a defined horizon, lessons are captured, and future reasoning retrieves relevant lessons via RAG.

## 2. Non-goals

- Multi-user / multi-tenant. Single operator, single account.
- Providing financial advice to anyone else. Outputs are personal-use only.
- High-frequency or low-latency trading. The system operates on minute-to-day bar cadence, not sub-second.
- Asset classes beyond US-listed equities and ETFs in v1. (Options, futures, crypto are out of scope until explicitly added.)
- Auto-generation of tax filings. The system produces the schedule; the human (or their accountant) files it.

## 3. Design principles

1. **Agents interpret; services act.** An "agent" is only used where LLM judgment is required (synthesis of ambiguous unstructured input). Anything deterministic — broker calls, ledger updates, strategy logic, risk checks, tax math — is a plain service. LLMs never have direct write access to money or state.
2. **Event-sourced core.** Every state change is an immutable event in an append-only log. Current state is a projection. This makes the system replayable, auditable, and gives the Learning Agent a clean substrate.
3. **Deterministic trade path.** From signal → risk gate → broker, the code path contains zero LLM calls. The trade path is testable, replayable, and explainable line-by-line.
4. **Fail closed.** On any uncertainty (data feed dropped, broker disconnected, risk limit ambiguous, LLM API down) the system halts new orders and alerts. It never guesses.
5. **Paper before shadow before live.** New strategies prove out on paper, then shadow-execute (decide-but-don't-send) against live data, then go live behind a feature flag.
6. **Owned data over scraped data.** Prefer paid, license-clear data feeds for anything load-bearing. Free/scraped sources are auxiliary.
7. **Cheap to run, expensive to fix.** Optimize for clarity and replayability over throughput. This is one person's portfolio, not a fund.

## 4. Component map

(See ASCII diagram at the head of the repo's README, mirrored from chat — services own state, agents interpret, orchestrator schedules.)

Two layers:

- **Agents (LLM)**: Research × 5, Learning, Tax-narrative.
- **Services (code)**: Orchestrator, Strategy Engine, Risk Gate, Broker, Portfolio & Ledger, Tax Reporter, Data Feed, Observability, Persistence.

---

## 5. Components

### 5.1 Orchestrator

**Type:** Service. No LLM.

Schedules everything: market-hours awareness (NYSE in AEDT/AEST), event-driven triggers (earnings releases, FOMC, breaking news), and cadence-based jobs (daily fundamentals refresh, intraday bar polling, EOD reconciliation, EOFY tax generation).

Routes events between components. Owns the run-mode flag (paper / shadow / live) and the kill-switch state.

Built on APScheduler for time-based jobs and a thin pub/sub event bus (Redis or in-process) for event-driven flow. Temporal is overkill for v1 — revisit if durability becomes a problem.

### 5.2 Research agents

**Type:** Agents (LLM). Read-only.

Five domain agents, each producing typed `Insight` records:

- **Technical** — runs on price/volume bars; outputs trend/momentum/volatility/breakout signals with quantitative backing. Note: most technicals don't need an LLM; the agent role is *judgment over conflicting indicators*, not computing RSI.
- **Fundamentals** — triggered on filings (10-K, 10-Q, 8-K) and earnings; reads structured XBRL plus the narrative MD&A; outputs quality / growth / valuation / red-flag insights.
- **Macro** — daily cadence; ingests FRED series, CPI/jobs prints, Fed minutes; outputs regime classification and rate-path expectations.
- **Geopolitics** — event-driven; reads curated news; outputs risk-on/off signals and sector-specific exposure flags (e.g. semi exposure to Taiwan, energy to Russia/ME).
- **News triage** — high-frequency cheap classifier (Haiku) over a news firehose; promotes only material items to the heavier agents.

Each agent retrieves relevant prior `Lesson`s from the Playbook before reasoning. Each `Insight` carries: symbol(s), thesis, confidence, time horizon, evidence pointers, agent version, model used, token cost.

### 5.3 Learning agent

**Type:** Agent (LLM). Post-hoc.

For every `Prediction` written by a research agent, schedules a verification job at `prediction.horizon`. After the horizon closes, the agent:

1. Computes the realized outcome from the ledger and price history.
2. Scores the prediction (binary hit/miss + magnitude error).
3. Writes a `Lesson` to the Playbook (vector store) explaining *why* it was right or wrong, tagged by regime, sector, signal type.
4. Optionally proposes adjustments to research-agent prompts (committed to a `prompt-revisions/` dir for human review — never auto-applied).

This is the only place where the system reasons about its own behavior. It runs offline, not on the trade path.

### 5.4 Strategy engine

**Type:** Service. No LLM.

Three-layer plugin architecture:

1. **Signal generator** (interface: `generate_signals(market_state, insights) -> List[Signal]`). Each strategy is a class registered under a name + semver. Examples: `dual_momentum_v1`, `quality_value_v2`, `news_reaction_v0`.
2. **Position sizer** — converts signals into target dollar weights. Defaults: vol-targeted with portfolio-level vol cap; Kelly-fraction available as an option (capped at quarter-Kelly).
3. **Execution policy** — picks order type and slicing (market / limit / TWAP / VWAP), with a configurable slippage model used identically in backtest and live.

The same `Signal → Order` code path runs in backtest, paper, shadow, and live, parameterized only by the data source and broker stub. Strategies are versioned; switching is a config change.

Ensembles are supported via a meta-strategy that consumes child signals and outputs combined orders.

### 5.5 Risk gate

**Type:** Service. No LLM. **Mandatory** on every order.

Hard, code-enforced limits:

- Max position size (% of equity, $ cap).
- Max sector / factor concentration.
- Max daily drawdown — breach triggers kill switch (flatten or freeze, configurable).
- Max orders / minute, max gross turnover / day.
- Do-not-trade list: halted symbols, earnings day if configured, symbols on a manual blacklist.
- Cooling-off after stop-out (no re-entry on same symbol for N minutes).
- HITL approval threshold: orders above $X notional or outside normal patterns pause and prompt the human.

Risk failures are loud: structured log + alert + the order is rejected with a reason code that the strategy can observe.

### 5.6 Broker service

**Type:** Service. No LLM. (Per earlier decision — this is a thin wrapper, not an agent.)

Wraps IBKR via `ib_async` against IB Gateway running in Docker. Responsibilities:

- Authenticate and maintain the gateway session (auto-restart for IBKR's daily auth quirk).
- Submit orders, handle partial fills, manage retries on transient errors.
- Stream positions, fills, account snapshots to the event store.
- Expose a clean async interface to the rest of the system.
- Run in **paper** or **live** mode based on the run-mode flag; the flag is read at submit time so a flip is immediate.

The broker service is the ONLY component allowed to talk to IBKR. Everything else goes through it.

### 5.7 Portfolio & ledger

**Type:** Service. No LLM. Source of truth.

Maintains:

- Trade ledger (every fill, in USD and AUD using RBA daily rate on trade date).
- Position book by lot (FIFO by default; specific-ID supported for tax-optimal disposals).
- Realized + unrealized P&L (per lot, per symbol, per strategy, per period).
- Dividends received (gross USD, withholding 15%, net USD, AUD-equivalent).
- Corporate actions (splits, mergers, spin-offs) — applied to lots automatically with manual override.
- Nightly reconciliation against IBKR snapshots. Mismatches halt trading and alert.

Storage: DuckDB for tabular data (fast analytical queries on the local file), Parquet for historical bars.

### 5.8 Tax service + narrative agent

**Type:** Mostly service. One thin LLM agent on top.

**Tax Reporter (service):** deterministic generator that produces, for any AU financial year (1 Jul – 30 Jun):

- Per-disposal CGT records: acquisition date, disposal date, holding period, cost base AUD, proceeds AUD, gain/loss AUD, discount eligibility flag.
- Aggregated capital gains (discounted method, other method) and capital losses carried forward.
- Foreign income summary: gross US dividends in AUD, US withholding tax in AUD (for the FITO claim).
- Trader-vs-investor signal: a heuristic flag based on activity (frequency, holding periods, intent indicators) — never a determination, always a flag for human/accountant judgment.
- Parcel-selection method audit trail (which lots were matched against which disposals, and why).

**Tax Narrative Agent (LLM):** takes the structured output and writes a plain-English schedule and cover note for the user's accountant, with caveats and assumptions clearly stated. Output is human-reviewed before sending.

### 5.9 Data layer

**Type:** Service. No LLM.

Three tiers of data, each with a clear source-of-truth:

- **Market data** — bars (1m/5m/1d), quotes, trades. Primary: IBKR live feed. Backfill: Polygon (paid). Stored as Parquet partitioned by symbol/date.
- **Fundamentals** — FMP or SimFin for normalized financials; SEC EDGAR for primary filings.
- **Macro** — FRED for US series, RBA for AUD/USD rates (needed for tax), ABS for AU-context if relevant.
- **News** — paid feed (Benzinga or similar) + curated RSS; X/Twitter signal optional and treated as low-trust.

A `MarketState` object is the canonical snapshot passed to strategies and research agents. It is reproducible from the event store + Parquet store, which is what makes backtests honest.

### 5.10 Observability

**Type:** Service. No LLM.

- Structured logs (JSON) to disk + optional ship to a hosted service.
- Metrics (Prometheus format, scraped by a local Grafana, or just SQLite + a static dashboard for v1): broker latency, order reject rate, P&L, drawdown, agent token spend per run, research-agent insight throughput, learning-agent hit rate.
- Alerts (Telegram or Slack) for: broker disconnects, risk breaches, kill-switch activations, ledger-reconciliation failures, LLM-cost-per-day breach, unusual drawdown.

Every alert has a documented response — see §6.5.

---

## 6. Cross-cutting concerns

### 6.1 Event sourcing & replay

All state changes are events: `OrderPlaced`, `OrderFilled`, `DividendReceived`, `InsightGenerated`, `PredictionScored`, `RiskBreached`, `RunModeChanged`, etc. Events are timestamped (UTC), versioned, and immutable. Projections (ledger, position book, P&L) rebuild from the log.

**Replay** is a first-class operation: given a date range, the system reconstructs `MarketState` at each tick and re-runs strategies — used both for backtesting new strategies and for asking "what would the new code have done last Tuesday."

### 6.2 Time zones

- Internal timestamps: UTC, always.
- Display to user: AEDT/AEST.
- Market context: ET (with DST handling — the US and AU DST schedules don't align, which silently shifts the AEDT–ET offset twice a year; the system handles this from a TZ database, never hard-coded offsets).
- Tax periods: AEST 30 June 23:59:59 — AU clock, not US.

### 6.3 Secrets & safety

- IBKR credentials, API keys, and trading-account identifiers live in a secret store (1Password CLI or macOS keychain), loaded at process start, never written to disk or logs.
- The live-trading flag requires a separate confirmation step on every system start.
- LLMs have read access to insights, market state, and ledger summaries — never to raw credentials or to the broker submit path.
- All outbound network traffic is logged for audit. Egress is restricted to a known allowlist (IBKR, data vendors, LLM provider, alert channel).

### 6.4 Cost tracking

Every LLM call, every data API call, and every commission is recorded as an event with cost in USD (and AUD-converted). Daily, weekly, and per-strategy cost-per-trade and cost-per-dollar-of-realized-P&L are reported. Cost budgets are configured per agent — exceeding them triggers an alert, not a hard stop (we want awareness, not paralysis).

### 6.5 Failure modes & degraded operation

Defined per component:

| Failure                          | Behavior                                                     |
|----------------------------------|--------------------------------------------------------------|
| IBKR Gateway disconnects         | Stop new orders. Keep tracking positions from last snapshot. Alert. Auto-reconnect with backoff. |
| Data feed stale (>N minutes)     | Mark `MarketState` stale. Strategies refuse to generate signals against stale data. Alert. |
| LLM API down                     | Research agents fail soft (skip cycle). Trade path unaffected. Tax narrative deferred. |
| Risk gate detects breach         | Kill switch: flatten or freeze (configurable). Alert. Manual reset required. |
| Ledger reconciliation mismatch   | Halt trading. Alert. Refuse to resume until human acknowledges. |
| Vector store unavailable         | Research agents run without prior lessons (degraded but functional). Alert. |

The system has one universal posture: **when in doubt, stop trading.**

### 6.6 Human-in-the-loop approval

Configurable thresholds (notional, % portfolio, deviation from norm) trigger an approval prompt over Telegram/Slack with the order details and the reasoning chain (which insights, which strategy, which sizer output). The human approves, rejects, or modifies. Timeout = reject. All approval interactions are events in the log.

### 6.7 Run modes

Three modes, one flag:

- **Paper** — orders go to IBKR's paper account. No real money. Full pipeline exercised.
- **Shadow** — orders are computed and logged but not sent. Used to evaluate new strategies against live conditions without execution cost or risk.
- **Live** — orders go to the live account. Requires explicit confirmation on system start and on every config change.

Strategies graduate paper → shadow → live based on observed performance over defined windows. Promotion is a manual step.

### 6.8 Compliance posture

This system trades the operator's personal capital only. It must not:

- Take instructions from, or send recommendations to, any other person.
- Publish or transmit its outputs externally without explicit user action.
- Hold itself out as providing financial advice.

The architecture enforces this by not having any external user-facing surface in v1. All outputs are local files or messages to the operator's own channels.

---

## 7. Tech stack

- **Language:** Python 3.12.
- **Agent orchestration:** LangGraph for the agent graph; APScheduler for time-based jobs.
- **Broker:** `ib_async` against IB Gateway in Docker.
- **Storage:** DuckDB (ledger + analytical queries), Parquet (historical bars), LanceDB or Chroma (vector store), SQLite (event log) — all single-file, local.
- **Models:** Claude Opus 4.7 for research/synthesis/postmortems, Claude Haiku 4.5 for news triage and cheap classification. Aggressive prompt caching.
- **Data vendors:** IBKR (live), Polygon (backfill), FMP or SimFin (fundamentals), FRED (macro), RBA (FX), Benzinga or similar (news).
- **Observability:** structured JSON logs, optional Prometheus + Grafana, Telegram bot for alerts.
- **Secrets:** 1Password CLI or macOS keychain.
- **Deployment:** Local Mac for dev. Always-on Mac mini or small VM (Hetzner) for live. Single Docker Compose file for the gateway + sidecars.

## 8. Build phases

Each phase produces a working system, not a stub.

1. **Foundations.** Repo scaffold, event store, ledger schema, IBKR paper-account read sync, one end-to-end paper order placed manually through the broker service.
2. **One strategy end-to-end.** A simple strategy (e.g. dual-momentum), backtester sharing the production code path, paper-trading it daily.
3. **Risk layer + kill switch + HITL approval.** Before any live trading.
4. **Tax reporter.** Built and tested against synthetic historical trades before EOFY 2026 (30 June 2026). Narrative agent on top.
5. **Research fan-out + Strategy Engine plugin interface.** Add fundamentals, technical, macro agents; refactor the v1 strategy to consume `Insight` records.
6. **Learning agent + Playbook RAG.** Score the history of insights produced in phase 5, populate the playbook, wire retrieval into research-agent prompts.
7. **Live mode.** Promote one well-behaved strategy from shadow to live, with small position sizes.

## 9. Open questions

To resolve before / during implementation:

- **Data vendor choice.** Polygon vs IBKR-only vs Alpaca for historical backfill. Cost vs quality trade-off.
- **Vector store.** LanceDB (newer, columnar, fits the Parquet-everything design) vs Chroma (more mature, simpler).
- **News firehose.** Paid (Benzinga ~ $100s/mo) vs scraped RSS + LLM triage (cheaper but flakier).
- **Trader vs investor classification.** Get a definitive view from an AU tax accountant before the system advises either way.
- **W-8BEN status.** Confirm it's on file with IBKR and the 15% rate applies, not 30%.
- **Backtest realism.** How aggressive a slippage and borrow-cost model is honest given the position sizes involved.
- **HITL latency.** What's the operator's tolerated response time? Drives the timeout-reject default.
- **Failure of the Mac mini / VM.** Is there a hot-spare strategy, or is "system down, no new trades" acceptable for a personal portfolio?

---

*This document is living. Update it when the design changes, not after.*
