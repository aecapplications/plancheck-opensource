# Contributing to PlanCheck

Contributions are welcome: pipeline and webapp fixes, rule packs for the
remaining CEC and CBC prompts, and new California code books. By
contributing you agree that your work is licensed under the Apache License
2.0 (see `LICENSE`).

## Ground rule: no code-book text

The California code books are copyrighted, and their text is never
committed. You need your own copy of a code PDF to build a graph or
extract rule packs. Rule packs may cite sections and paraphrase
requirements; they must not reproduce code text. Don't commit PDFs,
`*-graph/chapters/`, or text copied from a code book into any field,
including prompts, tests, and docs.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r webapp/requirements.txt
python tools/parity_gate.py      # should print PARITY OK
```

To work on a book's graph or rule packs, rebuild its chapter text from
your PDF:

```bash
python tools/split_chapters.py build --book cec --pdf <your CEC PDF>
python tools/split_chapters.py check --book cec
```

## Adding rule packs or a new code book

Follow the `add-code-book` skill in `.claude/skills/add-code-book/`. In
Claude Code, run `/add-code-book <book>`; without Claude Code, read
`SKILL.md` and its `reference/` files. To see where each book stands and
what's next:

```bash
python .claude/skills/add-code-book/scripts/book_status.py
```

## Pull request checklist

Run each of these and include the results in the PR description.

- [ ] **No code text.** `python tools/strip_verbatim.py`, then
      `python tools/strip_verbatim.py --check` prints "no `verbatim` quotes".
- [ ] **Audit**, run with the book's `chapters/` rebuilt locally:
      `python tools/audit_verbatim.py --max-run 30` reports 0 files over
      the limit. Paraphrase anything it flags.
- [ ] **Rule packs validate.**
      `python .claude/skills/add-code-book/scripts/validate_pack.py <book>-graph/plan-check/c<cid>_*_rules.json`
      prints OK for every new pack, and step 6 (`fixup_ids.py`,
      `normalize_clauses.py`, `integrate.py`) reports 0 validation issues.
- [ ] **Parity.** `python tools/parity_gate.py` prints `PARITY OK`. If you
      changed pipeline output on purpose, explain why and regenerate with
      `--update` in the same PR.
- [ ] **Sample facts.** The book's `sample-facts/` fixtures still fire the
      expected rules (`python engine.py sample-facts/<fixture>.json
      all_rules.json /tmp/v.json` in `<book>-graph/plan-check/`).
- [ ] **Docs.** For a new book: a manifest
      (`<book>-graph/chapters.manifest.json`), a section in
      `.claude/skills/add-code-book/reference/books.md`, and a row in the
      README's "Code books" table.

Keep the four shared pipeline files (`engine.py`, `integrate.py`,
`normalize_clauses.py`, `render_report.py`) byte-identical across books, and
keep every set iteration sorted so output stays deterministic.
