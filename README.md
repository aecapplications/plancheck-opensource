# PlanCheck

Automated plan checking for California Title 24 building codes. Upload a
plan-set PDF; PlanCheck extracts structured project facts from the drawings
and notes with Claude, runs a deterministic rule engine against one or more
code books, and flags each sheet with cited, evidence-backed compliance
findings.

## Code books

| Book | Code | Rules | Status |
|---|---|---|---|
| CRC | 2022 California Residential Code (Title 24 Part 2.5) | 263 | complete corpus |
| CEC | 2022 California Electrical Code (Title 24 Part 3) | 442 | 9 of 41 rule packs extracted |
| CBC | 2022 California Building Code (Title 24 Part 2) | — | dispatch-ready (36 packs / 781 sections) |

A book becomes selectable in the UI automatically once its rule corpus
exists on disk — no code changes (see `webapp/books.py`).

## How it works

```
PDF upload
  ├─ classify     every page → sheet type + project metadata   (shared, once)
  └─ per selected book, concurrently:
       text pass      notes/schedules → candidate facts (verbatim quotes)
       vision pass    drawings → candidate facts (visual observations)
       reconcile      vocabulary-enforce, merge, resolve conflicts
       decompose      expand facts via the book's predicate table
       engine         fire the book's rules (deterministic, no LLM)
       chain          group fired rules into compliance chains
       report         per-sheet flags + markdown report
```

Each book lives in `<book>-graph/`: per-chapter text extracts
(`chapters/`, not distributed — see [Code-book text](#code-book-text)), a
knowledge graph built from them (`graphify-out/graph.json`), and the
plan-check pipeline + rule corpus (`plan-check/`). The webapp
(`webapp/`) is book-agnostic: a registry (`webapp/books.py`) resolves each
book's paths, prompts, and pipeline modules at runtime.

## Running

Requires Python ≥ 3.10.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r webapp/requirements.txt

# Live (LLM extraction; ~$2 per selected book per upload)
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn webapp.app:app --port 8000

# Free end-to-end test mode (no API key, no LLM calls; loads sample facts)
EXTRACTOR_FAKE=1 uvicorn webapp.app:app --port 8000
```

Open http://127.0.0.1:8000, pick the code books to check, and drop in a PDF.
Guardrails and model settings live in `webapp/config.py`.

### API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/books` | Registered books, availability, rule counts |
| POST | `/api/jobs` | Upload PDF (multipart `file`, repeated `books` fields) |
| GET | `/api/jobs` | List jobs |
| GET | `/api/jobs/{id}` | Status, per-book progress |
| GET | `/api/jobs/{id}/books/{book}/result\|report\|facts` | Per-book artifacts |
| GET | `/api/jobs/{id}/result\|report\|facts` | First selected book (legacy) |
| GET | `/api/jobs/{id}/pages/{n}.png` | Rendered page image |
| DELETE | `/api/jobs/{id}` | Delete a job and its artifacts |

Job artifacts land in `webapp/jobs/<id>/` (untracked): shared
`upload.pdf`, `pages/`, `classification.json`, plus
`books/<book>/{facts,violations,chains,result}.json`, `report.md`,
`usage.jsonl`.

## Testing

- **Parity gate**: `tests/parity-baseline/` holds a byte-diff reference for
  the CRC pipeline — see its README. Any change to the pipeline must keep a
  FAKE-mode job byte-identical to it. `python tools/parity_gate.py` runs the
  whole gate (server, upload, compare) in one step.
- **Engine smoke**: each book ships `plan-check/sample-facts/`;
  e.g. `cd cec-graph/plan-check && python engine.py
  sample-facts/commercial-fitout-wireways.expanded.json all_rules.json /tmp/v.json`.

## Adding or extending a code book

`docs/adding-a-code-book.md` is the runbook: split the code PDF into
chapters, graphify, scaffold `plan-check/`, generate extraction prompts with
`tools/make_dispatch.py`, extract rule packs (one agent session per pack),
integrate, and the webapp picks the book up automatically.

## Working on this repo with Claude

The project skill `.claude/skills/add-code-book/` is the entry point for
onboarding a new book or extracting more rule packs — it defers to the
runbook above. Rule extraction is the one LLM-paid step (~$2–5 per pack);
everything else is deterministic Python.

## License

The PlanCheck source code, rule packs, and knowledge graphs are licensed
under the Apache License 2.0 (`LICENSE`). `tests/parity-baseline/sample.pdf`
is a third-party work under CC BY-SA 4.0 — see `NOTICE`.

## Code-book text

The California code books themselves are not part of this repository.
`*-graph/chapters/` (the per-chapter text extracts the graphs and rule packs
were built from) and the source code PDFs are excluded. Rule packs carry
section citations and structured, paraphrased requirements — not the code
text. Checking plans needs no code text: the webapp runs entirely from the
committed rule packs.

To rebuild a graph or extract new rule packs, obtain the code publication
yourself and regenerate `chapters/` from it. Each book ships a
`chapters.manifest.json` (filenames and page ranges, no text):

```bash
python tools/split_chapters.py build --book cec --pdf <your CEC PDF>
```

Contributions must not add code text. Extraction quotes each section in a
`verbatim` field as a working aid; `python tools/strip_verbatim.py` removes
those quotes before committing (`--check` verifies), and
`python tools/audit_verbatim.py --max-run 30` (run with `chapters/` present)
catches long verbatim runs in any field and publisher license footers.

