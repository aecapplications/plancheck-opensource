---
name: add-code-book
description: Onboard a new California code book into PlanCheck, or extend an existing one — extract rule packs, integrate them, and verify. Trigger on "add a code book", "onboard <book>", "extract rule packs", "run the next CEC/CBC packs", "integrate rule packs".
---

# Add or extend a code book

`docs/adding-a-code-book.md` is the single source of truth — follow its
numbered steps for the situation at hand. This skill is the entry point and
guardrail summary, not a replacement for the runbook.

## First: code-book text is local-only

`<book>-graph/chapters/` is not distributed. Before any step that reads code
text (graphify, dispatch, extraction), run
`python tools/split_chapters.py check --book <book>`. If it reports missing
files, ask the user for the path to their copy of the code PDF and run
`python tools/split_chapters.py build --book <book> --pdf <path>` — never
proceed by writing rules from memory, and never fetch code text from the web.

## Which steps apply

- **Brand-new book** (e.g. CALGreen): runbook steps 1–9 in order.
- **CBC** (graph + dispatch exist): rebuild chapters, then steps 3–9; see
  runbook Appendix A.
- **CEC** (live, 9/41 packs done): rebuild chapters, then steps 5–6 per
  batch of packs; see Appendix B.

## Non-negotiable invariants (from the runbook)

1. `engine.py`, `integrate.py`, `normalize_clauses.py`, `render_report.py`
   stay **byte-identical across books** — never parameterize them.
2. Rule extraction: every `section_node` / `depends_on` value is a graph node
   id copied **verbatim** from the dispatch prompt's lists — never invented.
   Every rule quotes its load-bearing source sentence in `verbatim` — a
   local working aid only: run `python tools/strip_verbatim.py` before
   committing to the public repo (`--check` must pass). Output must parse
   with `json.load` before a session reports done. Preflight each session
   with `split_chapters.py check --book <book> --prompt c<cid>.txt`.
3. **Never run `tools/make_dispatch.py --graph-dir crc-graph`** — crc's 21
   prompts are hand-authored and regeneration clobbers them.
4. All set iterations in book-adapted `chain.py`/`decompose.py` stay sorted
   (deterministic output across processes; the parity gate depends on it).
5. After every integrate: the CRC parity gate (`python tools/parity_gate.py`)
   must still pass byte-identical, and each book's `sample-facts/` must fire
   its expected rule counts.
6. No code text in commits: `python tools/audit_verbatim.py --max-run 30`
   (with chapters present) passes — no long verbatim runs in any field, no
   publisher license footers. Paraphrase; cite sections.

## Key commands

```bash
python tools/split_chapters.py build --book <book> --pdf <path>   # local chapters/
python tools/split_chapters.py check --book <book> [--prompt c07.txt]
python tools/make_dispatch.py --graph-dir <book>-graph      # step 4
# step 5: one agent session per plan-check/.prompts/c<cid>.txt
cd <book>-graph/plan-check && \
  python fixup_ids.py && python normalize_clauses.py && python integrate.py   # step 6
python tools/strip_verbatim.py && python tools/strip_verbatim.py --check    # public repo, before commit
python tools/parity_gate.py
```

Rule packs are independent — extract in any order, integrate per batch, and
the webapp picks up new rule counts automatically (`webapp/books.py`
availability is file-based). Budget ~$2–5 per pack session.
