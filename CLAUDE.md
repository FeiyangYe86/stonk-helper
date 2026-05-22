# Claude Code — project contract

You are working in a personal trading system. Money and tax records depend on
this code. Follow the contract below for every change.

## Source of truth

- **Design:** [ARCHITECTURE.md](ARCHITECTURE.md) — canonical. Update it in the
  same PR if a change alters the design.
- **Process:** [CONTRIBUTING.md](CONTRIBUTING.md) — branching, quality gates,
  merge strategy.
- **PR template:** [.github/pull_request_template.md](.github/pull_request_template.md).

Read CONTRIBUTING.md before making your first change in a session.

## Hard rules

1. **Never commit to `main`.** Always work on a typed feature branch
   (`feat/`, `fix/`, `refactor/`, `chore/`, `docs/`, `test/`).
2. **Every change ships via a PR.** Even tiny ones. The PR description must
   fill all four template sections substantively.
3. **Run the quality gates locally before opening the PR:**
   ```bash
   ruff check .
   mypy
   pytest -q
   ```
   If any fails, fix it before pushing.
4. **PR is single-purpose.** Split unrelated work into separate PRs.
5. **No `--no-verify`, no `--amend` on shared commits, no force-push to `main`.**
6. **Never commit** secrets, `.env`, `data/`, `logs/`, `*.duckdb`, `*.sqlite`,
   or real trading data.

## The four PR sections — what "substantive" means

Reviewers (including future you / future agents) rely on the description to
audit the change without re-reading every diff. So:

1. **Purpose** — name the problem and link the design context. Don't restate
   the diff.
2. **Edge cases & behaviour** — at minimum address: bad/missing input, partial
   failure, concurrency, boundaries (FY rollover, DST, empty stores). State
   what is explicitly *not* handled and why.
3. **Tests** — name the new tests and which edge cases they cover. For things
   that can't be unit-tested (live broker, LLM calls), record the manual
   verification: commands, expected vs observed.
4. **Tradeoffs** — what was weighed, what was deferred, what limitations
   remain. If a new open question emerges, add it to ARCHITECTURE.md §9 in
   the same PR.

If a section is genuinely "N/A", say so with a one-line reason.

## Safety rails specific to this system

- The trade path (signal → risk gate → broker) must remain deterministic. No
  LLM calls on the order-submission path.
- Changes to risk limits (when the Risk Gate exists) go through their own PR.
  Never bundle limit changes with feature work.
- Never default `run_mode` to `live` in committed config.
- Don't bypass the Ledger or Event Store to mutate state directly. All state
  changes flow through their services.

## Design principles to honour

From ARCHITECTURE.md §3, in priority order:

1. **Agents interpret; services act.** Only label something an "agent" if it
   needs LLM judgment. Deterministic logic is a service.
2. **Event-sourced.** State changes are events, not direct mutations.
3. **Deterministic trade path.** No LLM on the path from signal to broker.
4. **Fail closed.** On any uncertainty, stop trading and alert. Never guess.

## Code standards

- Python 3.12+, strict mypy, ruff (`E,F,I,N,UP,B,SIM,RUF`).
- Pydantic for typed data on interfaces; no untyped dicts in public APIs.
- One-line docstrings where useful; no decorative comment blocks.
- Tests live in `tests/`, use `tmp_path` for I/O, no network calls in unit tests.

## When in doubt

Ask the human. A clarifying question is cheaper than a wrong-shape PR.
