# Steps 6–8: integrate, decomposition, webapp pickup

## Step 6 — Fix up and integrate

```bash
cd <book>-graph/plan-check
python fixup_ids.py && python normalize_clauses.py && python integrate.py
```

- `fixup_ids.py` fuzzy-matches node ids that don't resolve against
  `graph.json` and writes `.fixup/remap.json` and `.fixup/unresolved.json`.
  It may add legitimate-looking missing nodes to `graph.json`, after saving
  a `.before-fixup` backup.
- `normalize_clauses.py` rewrites `applies_when` and exception clauses into
  the engine's canonical forms.
- `integrate.py` validates every pack, runs `canonicalize.py` itself
  (`canonical/*.canonical.json`, `canonical/vocabulary.json`), and merges
  everything into `all_rules.json`. Don't run `canonicalize.py` on its own;
  called without arguments it only prints usage and exits 1. Its built-in
  engine run uses a hard-coded CRC fixture (`wui-dwelling-with-pv.json`),
  so it only fires for CRC. For other books, check sample facts with the
  engine CLI (step 9).

**Feedback loop:** read `integrate.py`'s `Total: … validation issues` line
and `.fixup/unresolved.json`. Fix any pack with issues and re-run step 6.
Only move on when it reports 0 issues.

`fixup_ids.py` can add nodes to the committed `graph.json`. Review
`git diff --stat <book>-graph/graphify-out/graph.json` and keep only
additions that look like real sections, tables, or standards. The
`.before-fixup` backup is gitignored.

A new book can integrate before step 7 exists: `integrate.py` only needs
the packs and the graph.

Restart the webapp after integrating, because vocabulary caches live per
process.

## Step 7 — `predicate_decomposition.json` and sample facts

- `predicate_decomposition.json` holds alias groups, compound predicates,
  and regex decomposition patterns that bridge extracted facts to rule
  predicates. Start from cec's, which has the generalized shape, and keep
  it small. Grow it when integration or live runs show predicate families
  that never fire.
- `sample-facts/` needs at least one realistic facts file that fires rules.
  cec's `commercial-fitout-wireways.json` is the template. It is the book's
  FAKE-mode fixture for `EXTRACTOR_FAKE=1`.

The webapp makes a book available once `all_rules.json`,
`canonical/vocabulary.json`, and `predicate_decomposition.json` all exist
(`webapp/books.py:available`). The book then shows up in `/api/books` and
in the upload checkboxes.

## Step 8 — Webapp pickup

- Write `webapp/extractor/prompts/<book>.py` with `SYSTEM_INSTRUCTIONS`,
  `TEXT_PROMPT`, `VISION_PROMPTS`, `VISION_DEFAULT`, and
  `RECONCILE_PROMPT`. Copy `cec.py`'s shape, and ground the content in the
  book's actual vocabulary (`canonical/vocabulary.json`) so every prompt
  targets predicates that can fire. Register it in
  `webapp/extractor/prompts/__init__.py` by adding it to both the
  `from . import ...` line and the `_MODULES` dict.
- Add or complete the `Book` entry in `webapp/books.py`: `id`, `label`,
  `short`, `graph_dir`, `prompts_module`, and `sample_facts` (the filename
  in `sample-facts/`, not `None`).
- If the book's plan sets have sheet types the classifier doesn't know,
  extend `SheetType` in `webapp/extractor/schemas.py` and route them in
  `DRAWING_TYPES` / `TEXT_TYPES`. Any schema change invalidates the
  server-side structured-output grammar cache. The startup warm-up
  (`webapp/extractor/warmup.py`) recompiles it automatically.
