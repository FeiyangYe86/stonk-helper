<!--
All four sections are mandatory. "N/A" is only acceptable with a one-line
justification. See CONTRIBUTING.md for the full process and CLAUDE.md for the
agent contract.
-->

## 1. Purpose

<!--
Why does this change exist? What problem does it solve, and why now?
Link to the relevant section of ARCHITECTURE.md, an open question in §9,
or an external issue.
-->

## 2. Edge cases & behaviour

<!--
What edge cases were considered, and how does the code behave under each?
At minimum think about:
- bad / missing / malformed input
- partial failure (broker disconnect, stale data feed, LLM API down)
- concurrency or re-entrancy
- boundary conditions (AU FY rollover, empty positions, zero-quantity fills,
  daylight-saving transitions, first-time runs against an empty store)
- explicitly note anything NOT handled, with rationale
-->

## 3. Tests

<!--
What tests were added or changed? Cover both the happy path and the edge
cases above. If something can't be unit-tested (e.g. live broker round-trip),
document the manual verification: commands run, expected vs observed.
-->

## 4. Tradeoffs

<!--
What did you weigh? What was deferred? Any known limitations or follow-up
work? Reference ARCHITECTURE.md §9 if a new open question is being introduced.
-->

---

### Pre-merge checklist

- [ ] `ruff check .` clean
- [ ] `mypy` clean
- [ ] `pytest -q` green
- [ ] ARCHITECTURE.md updated if the design changed
- [ ] No secrets, `data/`, or `logs/` committed
- [ ] PR is single-purpose; unrelated changes split out
