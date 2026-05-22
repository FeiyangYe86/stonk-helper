#!/usr/bin/env python3
"""
Run one review agent against the current PR and post the result as a comment.

Usage: review_agent.py <agent-name>
  agent-name: template | architecture | safety | code-quality

Required env vars:
  ANTHROPIC_API_KEY  - Claude API key
  GH_TOKEN           - GitHub token (picked up automatically by gh CLI)
  PR_NUMBER          - Pull request number
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import anthropic

# template uses Haiku (fast + cheap for a completeness check).
# Substantive reviews use Sonnet.
_MODELS: dict[str, str] = {
    "template": "claude-haiku-4-5",
    "architecture": "claude-sonnet-4-6",
    "safety": "claude-sonnet-4-6",
    "code-quality": "claude-sonnet-4-6",
}

_HEADERS: dict[str, str] = {
    "template": "🔖 PR Template Review",
    "architecture": "🏗️ Architecture Review",
    "safety": "🛡️ Safety Review",
    "code-quality": "🔍 Code Quality Review",
}

_DIFF_CHAR_LIMIT = 15_000


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


def _pr_metadata(pr_number: str) -> dict[str, object]:
    out = _run(
        ["gh", "pr", "view", pr_number, "--json",
         "title,body,additions,deletions,changedFiles"]
    )
    return json.loads(out)  # type: ignore[no-any-return]


def _pr_diff(pr_number: str) -> str:
    diff = _run(["gh", "pr", "diff", pr_number])
    if len(diff) > _DIFF_CHAR_LIMIT:
        return diff[:_DIFF_CHAR_LIMIT] + f"\n\n[diff truncated — {len(diff):,} chars total]"
    return diff


def _read(path: str) -> str:
    p = Path(path)
    return p.read_text() if p.exists() else f"(file not found: {path})"


def _build_message(agent: str, meta: dict[str, object], diff: str) -> str:
    title = meta.get("title") or "(no title)"
    body = meta.get("body") or "(no description provided)"
    additions = meta.get("additions", 0)
    deletions = meta.get("deletions", 0)
    changed = meta.get("changedFiles", 0)

    parts = [
        f"**PR title:** {title}",
        f"**Stats:** +{additions} / -{deletions} lines, {changed} file(s) changed",
        "",
        "## PR description",
        str(body),
    ]

    if agent != "template":
        parts += ["", "## Diff", "```diff", diff, "```"]
        parts += ["", "## ARCHITECTURE.md", _read("ARCHITECTURE.md")]
        parts += ["", "## CLAUDE.md", _read("CLAUDE.md")]

    return "\n".join(parts)


def _post_comment(pr_number: str, agent: str, review: str) -> None:
    body = (
        f"### {_HEADERS[agent]}\n\n"
        f"{review}\n\n"
        f"---\n"
        f"*Posted by the `{agent}` review agent.*"
    )
    subprocess.run(
        ["gh", "pr", "comment", pr_number, "--body", body],
        check=True,
    )


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in _MODELS:
        sys.exit(f"Usage: review_agent.py <{'|'.join(_MODELS)}>")

    agent = sys.argv[1]
    pr_number = os.environ["PR_NUMBER"]
    system_prompt = Path(f".github/review-agents/{agent}.md").read_text()

    meta = _pr_metadata(pr_number)
    diff = _pr_diff(pr_number) if agent != "template" else ""
    user_message = _build_message(agent, meta, diff)

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=_MODELS[agent],
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    block = response.content[0]
    if not isinstance(block, anthropic.types.TextBlock):
        sys.exit(f"Unexpected response block type: {type(block)}")

    _post_comment(pr_number, agent, block.text)


if __name__ == "__main__":
    main()
