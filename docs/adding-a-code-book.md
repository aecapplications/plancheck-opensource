# Adding a code book to PlanCheck

The repeatable path from a code PDF to a book the webapp checks plans
against. Each numbered step is independently resumable and sized for one
agent session (or one sitting); a book needs **no webapp code changes**
beyond step 8 — availability flips on automatically when its artifacts
exist.

Throughout, `<book>` is the short lowercase id (`cec`, `cbc`, `calgreen`)
and the book lives in `<book>-graph/` at the repo root.

## Code-book text is local-only

The code books are copyrighted and are **not distributed** with PlanCheck.
Each book ships `<book>-graph/chapters.manifest.json` (chapter filenames,
titles, PDF page ranges — no text) instead of `chapters/`. Anything that
reads code text — graphify (step 2), dispatch (step 4), rule extraction
(step 5) — needs `chapters/` rebuilt locally from **your own copy** of the
code PDF first:

```bash
python tools/split_chapters.py build --book cec --pdf <your CEC PDF>
python tools/split_chapters.py check --book cec    # every referenced file present?
```

The manifest records the printing it was built from (`source.page_count`);
`build` refuses a PDF with a different page count unless `--force`, since a
different printing shifts the page ranges. Steps 3 and 6–9 run from committed
artifacts and need no code text.

Two rules keep the public repository free of code text:

- Rule packs may cite and paraphrase, never reproduce. Extraction still
  quotes each section in `verbatim` (it anchors the model), so run
  `python tools/strip_verbatim.py` before committing, and
  `python tools/strip_verbatim.py --check` to confirm.
- `python tools/audit_verbatim.py --max-run 30` (with `chapters/` present)
  must pass — it catches long verbatim runs in any field and publisher
  license footers.

## Anatomy of a finished book

```
<book>-graph/
  chapters/                 # per-chapter text extracts of the code PDF
  graphify-out/graph.json   # knowledge graph (+ report, cost log)
  plan-check/
    engine.py integrate.py normalize_clauses.py render_report.py   # byte-shared
    decompose.py chain.py fixup_ids.py canonicalize.py             # book-adapted
    .dispatch_plan.json .prompts/c<cid>.txt                        # from tools/make_dispatch.py
    c<cid>_<label>_rules.json ...                                  # extracted rule packs
    all_rules.json canonical/vocabulary.json                       # from integrate.py
    predicate_decomposition.json                                   # hand-authored
    sample-facts/*.json                                            # at least one
webapp/extractor/prompts/<book>.py                                 # extraction prompts
webapp/books.py                                                    # one REGISTRY entry
```

## 1. Acquire & split the PDF

Put the code PDF at `<book>-graph/` (leave it untracked — source PDFs are
copyrighted and never committed). Draft a chapter manifest from the PDF's
bookmarks, edit it, then build `chapters/` from it:

```bash
python tools/split_chapters.py init --book <book> --pdf <book>-graph/<file>.pdf --level 1
#   edit <book>-graph/chapters.manifest.json
python tools/split_chapters.py build --book <book> --pdf <book>-graph/<file>.pdf
```

Pick `--level` by the PDF's bookmark depth for chapters (CRC and CEC: 1;
CBC: 2 — the tool lists the levels present if the one you ask for is
empty). In the manifest, drop front matter and indexes, split very
large chapters into page ranges (`_a`/`_b` suffixes, as CRC does), and keep
an `NN_`- or `chNN_`-style filename prefix — graphify and the dispatch tool
both key off it. The three committed manifests are worked examples. Commit
the manifest; `chapters/` stays out of the public repo (it is gitignored
there).

## 2. Graphify

```
/graphify <book>-graph/chapters --obsidian
```

Produces `<book>-graph/graphify-out/graph.json`, `GRAPH_REPORT.md`, and the
obsidian vault (the vault and caches are generated locally but not versioned —
only graph.json, GRAPH_REPORT.md, and cost.json are committed). Budget ~3–3.5M agent tokens for a full code book (observed:
CBC logged ~1.42M for 11 of 26 chunks).

## 3. Scaffold plan-check/

Copy from **cec-graph/plan-check/** (the canonical donor):

- `engine.py`, `integrate.py`, `normalize_clauses.py`, `render_report.py` —
  **verbatim, and they must stay byte-identical across books.** The webapp
  loads each book's own copy via importlib (webapp/books.py); the shared
  contract is what keeps behavior uniform. Do not parameterize them.
- `decompose.py` — copy verbatim (cec's generalized `any_of_capture`
  pattern; crc's older `any_of_capture_sdcs` variant is CRC-only).
- `chain.py` — copy, then adapt exactly three book-specific pieces to the
  book's node-id convention (everything else must stay identical to cec's):
  1. `_section_core()` — reduce a node id to its bare section-number token
  2. `keep_relations` — the graphify relation types worth chaining across
  3. `is_terminal()` — what counts as a leaf citation (tables, figures,
     referenced standards) in this book's id scheme
- `fixup_ids.py`, `canonicalize.py` — copy and adapt to the same id
  convention (they normalize rule-pack node references before integrate).

Keep every set iteration sorted — chain/decompose must stay deterministic
across processes (no bare set iteration); the byte-diff parity gates depend
on it.

## 4. Dispatch

```
python tools/make_dispatch.py --graph-dir <book>-graph [--min-nodes 10]
```

Emits `plan-check/.dispatch_plan.json` + one extraction prompt per
rule-bearing community in `plan-check/.prompts/`. Needs `chapters/` (it
resolves each community's source files from them) and exits with an error if
the directory is missing or empty. Output is deterministic: re-running on an
unchanged graph only changes prompts if the template in `make_dispatch.py`
changed. Works with or without
`graphify-out/.graphify_labels.json` — labels are synthesized from chapter
stems / section titles when absent. **Do not run the generator on crc-graph**:
its 21 prompts were hand-authored before the tool existed (extraction is
long done) and regeneration would clobber them. If the book isn't in the tool's
`BOOK_META`, add an entry (corpus names, cite regex, standards tokens,
predicate-convention examples); sanity-check the skip list it prints —
only reference material (definitions chapters, indexes) should be skipped.

## 5. Rule-pack extraction (agent sessions)

One session per community prompt: feed `plan-check/.prompts/c<cid>.txt` to
a model; it reads the chapter files and writes
`plan-check/c<cid>_<label>_rules.json` in the shared rule schema.

- Preflight every session:
  `python tools/split_chapters.py check --book <book> --prompt c<cid>.txt`.
  A session whose source files are missing must stop, not extract from
  memory (the prompts say so too).
- Before committing packs to the public repo:
  `python tools/strip_verbatim.py` (strips the `verbatim` quotes) and the
  audit above.

- Invariant: every `section_node` and `depends_on` entry must resolve to a
  node id in that book's `graph.json` — copied verbatim, never invented.
- Budget ≈ 200–400k tokens (~$2–5) per pack. Packs are independent; extract
  incrementally in any order and re-run step 6 after each batch.

## 6. Canonicalize & integrate

```
cd <book>-graph/plan-check
python fixup_ids.py && python normalize_clauses.py && python canonicalize.py && python integrate.py
```

Produces `all_rules.json` and `canonical/vocabulary.json`. Re-run after
every new rule pack — rule counts grow, and the webapp picks the new corpus
up on its next job with no restart-sensitive state (vocab caches are
per-process; restart the server after integrating).

## 7. Author predicate_decomposition.json + sample facts

- `predicate_decomposition.json`: alias groups, compound predicates, and
  regex decomposition patterns for the domain (start from cec's — it is the
  generalized shape — and keep it small; grow it as extraction reveals what
  models actually emit).
- `sample-facts/`: at least one realistic facts file that fires rules
  (cec's `commercial-fitout-wireways.json` is the template). This powers
  `EXTRACTOR_FAKE=1` testing and is the book's FAKE-mode fixture.

## 8. Webapp pickup

- Write `webapp/extractor/prompts/<book>.py` — `SYSTEM_INSTRUCTIONS`,
  `TEXT_PROMPT`, `VISION_PROMPTS`, `VISION_DEFAULT`, `RECONCILE_PROMPT`
  (copy cec.py's shape; ground the content in the book's actual vocabulary
  so every prompt targets predicates that can fire). Register it in
  `webapp/extractor/prompts/__init__.py`.
- Add the `Book` entry in `webapp/books.py` (id, label, short, graph_dir,
  prompts_module, sample_facts filename).
- If the book's plan sets have sheet types the classifier doesn't know,
  extend `SheetType` in `webapp/extractor/schemas.py` and route them in
  `DRAWING_TYPES`/`TEXT_TYPES`. Note: any schema change invalidates the
  server-side structured-output grammar cache — the startup warm-up
  (webapp/extractor/warmup.py) recompiles automatically.

Availability flips on automatically once `all_rules.json`,
`canonical/vocabulary.json`, and `predicate_decomposition.json` exist —
the book appears in `/api/books` and the upload checkboxes.

## 9. Verify

1. Engine CLI on sample facts:
   `python engine.py sample-facts/<x>.json all_rules.json /tmp/v.json` —
   expect the intended rules to fire.
2. `EXTRACTOR_FAKE=1 python3 -m uvicorn webapp.app:app` — upload any PDF
   with the new book selected: per-book progress, results chips, report.
3. CRC regression: a CRC-only FAKE job must remain byte-identical to the
   parity baseline (see `tests/parity-baseline/README.md` for the procedure).
4. One live run on a representative plan set (~$2/book): confirm extraction
   emits vocabulary predicates (check `books/<book>/rejected.json` is small)
   and flags land on sensible sheets.

---

## Appendix A — CBC (steps 3–9 remain)

First rebuild `cbc-graph/chapters/` (`split_chapters.py build --book cbc`).
The graph exists (`cbc-graph/graphify-out/`, 2,769 nodes) and step 4 is
done: `tools/make_dispatch.py --graph-dir cbc-graph` emits 36 packs / 781
rule-bearing sections (label-free path). Remaining: scaffold plan-check
(step 3 — adapt chain's three pieces to CBC ids like
`ch15_section_1501_general`), extract packs (step 5, ~$60–150 total),
integrate, author the decomposition table + a sample-facts file, replace the
stub prompts in `webapp/extractor/prompts/cbc.py` with vocabulary-grounded
ones, and verify.

## Appendix B — CEC (steps 5–6 remain)

First rebuild `cec-graph/chapters/` (`split_chapters.py build --book cec`).
Everything through step 4 is done and the book is live with 9 of 41 packs
(442 rules): Article 378 wireways plus the Tier 1 wave — branch circuits
(c07), grounded conductor identification/use (c16/c19), luminaires &
appliance circuits (c22), load calculations (c24), GFCI (c28), working space
(c29), receptacles & switches (c31). Remaining: run step 5 for the other ~32
prompts in `cec-graph/plan-check/.prompts/` (~$65–160 total), re-running
step 6 after each batch and growing `predicate_decomposition.json` where new
predicate families need bridging to extracted facts.

## Appendix C — CALGreen (full runbook)

Start at step 1 with the CALGreen (Title 24 Part 11) PDF. Expect a smaller
corpus than CBC. Add a `calgreen-graph` entry to `tools/make_dispatch.py`'s
`BOOK_META` at step 4. Estimated total ~$90–200 (graphify ~$25–60 +
extraction).
