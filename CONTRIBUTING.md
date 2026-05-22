# Contributing to stonk-helper

This is a single-operator personal trading system. Even so — and especially
because changes touch money — **every change goes through a pull request**. No
direct commits to `main`.

This document is the canonical workflow. The PR template at
[.github/pull_request_template.md](.github/pull_request_template.md) is the
description contract. Agents (Claude Code etc.) follow the additional rules in
[CLAUDE.md](CLAUDE.md).

## Branching

`main` is the only long-lived branch and is protected (configure on GitHub: no
direct pushes, PR + green CI required to merge).

Feature branches use a typed prefix:

| Prefix      | Use for                                    |
|-------------|--------------------------------------------|
| `feat/`     | new functionality                          |
| `fix/`      | bug fix                                    |
| `refactor/` | no behaviour change                        |
| `chore/`    | tooling, deps, infra, CI                   |
| `docs/`     | docs only                                  |
| `test/`     | tests only                                 |

Each PR is **single-purpose**. If you find yourself writing "also..." in the
description, split the PR.

## Workflow per change

```bash
git switch main && git pull
git switch -c feat/<short-description>

# ... make changes ...

ruff check .
mypy
pytest -q

git push -u origin feat/<short-description>
gh pr create   # uses the template automatically
```

## PR description — the four mandatory sections

Every PR must answer, substantively:

1. **Purpose** — why this change exists; link to ARCHITECTURE.md or §9 open
   questions.
2. **Edge cases & behaviour** — what was considered (bad input, partial
   failure, concurrency, boundaries) and what is explicitly *not* handled.
3. **Tests** — what was added/changed, plus any manual verification for things
   that can't be unit-tested (e.g. live broker round-trip).
4. **Tradeoffs** — what was weighed, what was deferred, known limitations.

"N/A" is allowed only with a one-line justification. Empty sections are a
review blocker.

## Quality gates

CI (`.github/workflows/ci.yml`) runs on every PR and on pushes to `main`:

- `ruff check .` — lint + import order
- `mypy` — strict typing across `src/` and `tests/`
- `pytest -q` — unit tests

All three must pass before merge. Run them locally first; CI is the second
line of defence, not the first.

## Design changes

If a PR changes the design described in [ARCHITECTURE.md](ARCHITECTURE.md),
update it **in the same PR**. The doc and the code must not drift.

New uncertainties or trade-offs that aren't resolved by the PR go into
ARCHITECTURE.md §9 (open questions).

## Things never to commit

- Secrets, API keys, IBKR credentials, `.env`
- Anything under `data/`, `logs/`, or any `*.duckdb` / `*.sqlite`
- Real trading data, even paper-account exports
- `run_mode: live` as a default in any committed config

The `.gitignore` covers the common cases; double-check before adding new files.

## Merge strategy

Squash merge into `main`. The squashed commit message uses the PR title and
the PR description (sections 1–4) as the body, giving `git log` a usable
audit trail.

## Releases

Tag `v0.x.y` after a meaningful chunk of work lands. Phase boundaries from
ARCHITECTURE.md §8 are good moments for tags.
