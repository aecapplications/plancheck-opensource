---
name: add-code-book
description: Onboards a new California code book (e.g. CALGreen) into PlanCheck or extends an existing one (CBC, CEC, CRC). Covers rebuilding local chapter text from the user's PDF, graphifying, scaffolding plan-check/, dispatching and extracting rule packs, integrating them, registering the book in the webapp, and verifying with the parity gate. Use when the user asks to add or onboard a code book, extract or continue rule packs ("run the next CEC packs"), integrate rule packs, or check how far a book's onboarding has got.
argument-hint: "[book-id, e.g. cec | cbc | calgreen]"
---

# Add or extend a code book

Book requested: $ARGUMENTS. If that is blank, infer the book from the
request or ask. `<book>` below is the short lowercase id; the book lives in
`<book>-graph/` at the repo root.

## Start here

1. Check where the book stands:
   ```bash
   python .claude/skills/add-code-book/scripts/book_status.py <book>
   ```
   It checks every step's artifacts on disk and prints `next: step N`.
   Begin at that step. Don't assume progress from memory or older docs.
2. Read [reference/books.md](reference/books.md) for the book's quirks
   (hand-authored CRC prompts, CBC id conventions, donor files).

## Guardrails

- **Code text stays local.** Source PDFs are never committed anywhere.
  `<book>-graph/chapters/` is copyrighted text. The **private** repo tracks
  it as the full-fidelity copy, so commit a new book's chapters there. A
  **public** clone gitignores it, and it never goes public. Before any step
  that reads code text (1, 2, 4, 5), run `python tools/split_chapters.py check --book <book>`. If
  files are missing, ask the user for the path to their PDF and run
  `python tools/split_chapters.py build --book <book> --pdf <path>`. Never
  write rules from memory, and never fetch code text from the web.
- **Shared files stay byte-identical.** `engine.py`, `integrate.py`,
  `normalize_clauses.py`, and `render_report.py` are identical across
  books. Never parameterize them.
- **Graph ids are copied, never invented.** Every `section_node`,
  `depends_on`, and `tested_per` entry in a rule pack must be a node id from
  the prompt's lists. `scripts/validate_pack.py` checks this.
- **Ask before spending.** Get the user's go-ahead before graphify (about
  $25–60 per book), before extracting more than the packs they asked for
  (about $2–5 each), and before any live webapp run.
- **Never run `tools/make_dispatch.py` on `crc-graph`.** Its prompts are
  hand-authored.
- **Stay deterministic.** Every set iteration in a book's `chain.py` and
  `decompose.py` is sorted. The parity gate depends on byte-identical
  output.
- **No code text in commits.** Rule packs cite and paraphrase. The
  `verbatim` field is a local extraction aid only (see "Before committing:
  no code text").

## What a finished book looks like

```
<book>-graph/
  chapters.manifest.json         # committed: filenames + page ranges, no text
  chapters/                      # code text: private repo only, rebuilt from the user's PDF
  graphify-out/graph.json        # knowledge graph (+ GRAPH_REPORT.md, cost.json)
  plan-check/
    engine.py integrate.py normalize_clauses.py render_report.py   # byte-shared
    decompose.py chain.py fixup_ids.py canonicalize.py             # book-adapted
    .dispatch_plan.json .prompts/c<cid>.txt                        # make_dispatch.py
    c<cid>_<label>_rules.json                                      # extracted packs
    all_rules.json canonical/vocabulary.json                       # integrate.py
    predicate_decomposition.json sample-facts/*.json               # hand-authored
webapp/extractor/prompts/<book>.py   +   a Book entry in webapp/books.py
```

## Workflow

Copy this checklist into your response and tick items off as you go.
Brand-new books start at step 1; existing books start where `book_status.py`
says.

```
- [ ] 1 Manifest + local chapters/     → reference/chapters-and-graph.md
- [ ] 2 Graphify                       → reference/chapters-and-graph.md
- [ ] 3 Scaffold plan-check/           → reference/scaffold.md
- [ ] 4 Dispatch prompts               → reference/dispatch-and-extraction.md
- [ ] 5 Extract rule packs             → reference/dispatch-and-extraction.md
- [ ] 6 Fix up + integrate             → reference/integrate-and-webapp.md
- [ ] 7 Decomposition + sample facts   → reference/integrate-and-webapp.md
- [ ] 8 Webapp pickup + docs           → reference/integrate-and-webapp.md
- [ ] 9 Verify                         → below
```

Read the linked reference before doing a step. Commands assume the repo
root unless they `cd`. `/graphify` is a skill, not a shell command, and it
writes into the current directory. Run `cd <book>-graph` in the main
session's Bash tool first, then invoke it. Don't delegate it to a subagent,
whose shell may start elsewhere. The core commands:

```bash
python tools/split_chapters.py build --book <book> --pdf <path>         # 1 (existing manifest)
# 2: cd <book>-graph, then invoke the skill: /graphify chapters --obsidian
python tools/make_dispatch.py --graph-dir <book>-graph                  # 4
python tools/split_chapters.py check --book <book> --prompt c<cid>.txt  # 5 preflight, every pack
python .claude/skills/add-code-book/scripts/validate_pack.py <pack>.json  # 5 validate, every pack
cd <book>-graph/plan-check && \
  python fixup_ids.py && python normalize_clauses.py && python integrate.py   # 6
```

Step 5 is the usual recurring task: one agent session per
`plan-check/.prompts/c<cid>.txt`, about $2–5 each. "The next N packs" means
the first N ids from `book_status.py <book> --remaining`, unless the user
names specific ones. Extract the batch (packs are independent, so run them
in parallel), and validate each pack. Record the step 9 engine baseline (if
the book already has `all_rules.json` and a fixture), then run step 6 once
for the batch, then run the automated checks in step 9.

## Step 9: verify (feedback loop)

Fix and re-run until every check passes, and only then report the work as
done. Checks 1, 2, and 4 are automated; run them after every extraction
batch. Check 3 needs a browser: run it, or ask the user to, when a book
first becomes available or webapp code changed.

1. **Engine on sample facts.** For each fixture `book_status.py` lists,
   compare the `fired:` count (printed on stderr) with the baseline you
   recorded **before** step 6, running the same command against the old
   `all_rules.json`. It must not drop unexpectedly, and new packs should add
   rules their sections imply. A new book has no baseline until its first
   fixture exists (step 7). Then the check is that `fired:` is above 0 for
   its fixture, and it becomes the baseline for later batches:
   ```bash
   cd <book>-graph/plan-check && python engine.py sample-facts/<fixture>.json all_rules.json /tmp/v.json 2>&1 | grep -E "evaluated|fired"
   ```
2. **CRC parity gate.** It must print `PARITY OK`:
   ```bash
   python tools/parity_gate.py
   ```
3. **FAKE-mode UI run.** Run `EXTRACTOR_FAKE=1 uvicorn webapp.app:app
   --port 8000` and upload any PDF with the book selected. Expect per-book
   progress, results chips, and a report.
4. **Status.** `book_status.py <book>` shows the expected rows checked and
   `webapp availability: AVAILABLE` once steps 6–7 are done.

A live run on a representative plan set (about $2 per book, needs
`ANTHROPIC_API_KEY`) is the final check: `books/<book>/rejected.json` should
be small, and flags should land on sensible sheets. Ask the user before
spending on it.

## Publishing to the public repo

Only from the **private** repo, after committing. This publishes, so ask
the user first:

```bash
rm -rf /tmp/pc-release && python tools/export_public.py /tmp/pc-release --sync-to ../plancheck-opensource
```

The export drops `chapters/` (manifests stay), strips `verbatim` quotes,
regenerates and checks the parity baseline, and audits for code text. If the
audit flags a requirement field, paraphrase it in the private repo, commit,
and re-run the whole command. The export refuses a non-empty destination,
which is why it starts with `rm -rf`. `--sync-to` then mirrors the result into the public clone
(refusing a dirty clone or the private repo) and prints its `git status`.
Check that a new `<book>-graph/` has a manifest and no `chapters/`, then
commit and push from the clone.

## Committing

Commit at each milestone: the manifest (step 1), the graph (step 2), the
scaffold (step 3), the dispatch prompts (step 4), and each extraction batch
after step 6 and the step 9 checks pass. Stage the book's whole
`<book>-graph/` change set, not just the packs. `git status <book>-graph`
should show every file below as staged:

- the new `c<cid>_*_rules.json` packs;
- step 6 outputs: `.fixup/`, `.normalize/`, `canonical/`, `all_rules.json`;
- any reviewed `graphify-out/graph.json` additions from `fixup_ids.py`;
- in the private repo only, new `chapters/` files.

Never stage PDFs, `webapp/jobs/`, or graphify caches; `.gitignore` covers
them. Ask before committing if the user didn't request it.

## Before committing: no code text

To tell which repo you're in, look for `*-graph/chapters/` in
`git ls-files`. If it's listed, this is the private repo; if it isn't, this
is a public clone.

- **Public clone:** strip the quotes, then audit. Paraphrase anything the
  audit flags and re-run it.
  ```bash
  python tools/strip_verbatim.py && python tools/strip_verbatim.py --check
  python tools/audit_verbatim.py --max-run 30     # needs chapters/ present
  ```
- **Private repo:** commit packs with their quotes; `strip_verbatim.py`
  refuses to run here. Running the audit directly would flag the quotes
  themselves. Instead, check that requirement fields don't copy long
  passages with a scratch export, which strips and then audits:
  ```bash
  python tools/export_public.py /tmp/plancheck-export-check --worktree && rm -rf /tmp/plancheck-export-check
  ```
