# Adding a code book to PlanCheck

The runbook now lives in the Claude Code project skill
[`.claude/skills/add-code-book/`](../.claude/skills/add-code-book/SKILL.md).
It is plain Markdown, so you can follow it by hand too:

- [`SKILL.md`](../.claude/skills/add-code-book/SKILL.md): the workflow
  checklist, guardrails, core commands, and verification.
- [`reference/`](../.claude/skills/add-code-book/reference/): step-by-step
  detail for each phase, plus per-book notes.
- [`scripts/book_status.py`](../.claude/skills/add-code-book/scripts/book_status.py):
  shows where each book stands and the next step to run.

In Claude Code, run `/add-code-book <book>`, or just ask (for example "run
the next CEC packs").
