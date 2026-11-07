# PlanCheck webapp — PDF plan-check submission

Upload an architect's plan-set PDF; the app extracts project facts from the
drawings and notes, runs the existing CRC plan-check pipeline
(`../crc-graph/plan-check/`), and flags each sheet for code compliance.

## Pipeline

```
PDF upload
  │
  ├─ Pass A  classify    every page → sheet type / ID + project metadata
  ├─ Pass B  text        notes/schedules/cover → candidate facts (verbatim quotes)
  ├─ Pass C  vision      per drawing sheet → candidate facts (visual observations)
  └─ Pass D  reconcile   vocab-enforce + merge + conflict-resolve → facts.json + provenance
        │
        ▼
  decompose → engine → chain → render_report   (imported from ../crc-graph/plan-check/)
        │
        ▼
  result.json: per-sheet flags (cite, severity, evidence, evidence_required)
```

Extraction uses the Anthropic API (`claude-opus-4-8`): a base64 PDF/image is sent
per pass, and the 712-predicate canonical vocabulary
(`vocabulary.json` ∪ `predicate_decomposition.json`) is a prompt-cached system
block reused across every call. The model may only emit predicates from that
vocabulary; `reconcile` enforces it as a hard allowlist.

## Run

```bash
# from the PlanCheck repo root
pip install -r webapp/requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn webapp.app:app --port 8000
# open http://127.0.0.1:8000
```

### Test the flow without the API

```bash
EXTRACTOR_FAKE=1 uvicorn webapp.app:app --port 8000
```

`EXTRACTOR_FAKE=1` skips all LLM passes and loads
`../crc-graph/plan-check/sample-facts/full-sfr-truckee.json` with synthetic per-page
provenance, so the upload → progress → results flow can be exercised for free.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET  | `/` | Upload UI |
| POST | `/api/jobs` | Upload PDF (multipart `file`) → `{job_id}` |
| GET  | `/api/jobs/{id}` | Job status + phase + progress |
| GET  | `/api/jobs/{id}/result` | Per-sheet flags (result.json) |
| GET  | `/api/jobs/{id}/report` | Markdown plan-check report |
| GET  | `/api/jobs/{id}/facts` | Extracted facts.json (with provenance) |
| GET  | `/api/jobs/{id}/pages/{n}.png` | Rendered page image |

## Job artifacts

Each job writes `webapp/jobs/<id>/`: `upload.pdf`, `pages/page_N.png`,
`classification.json`, `candidates.json`, `rejected.json`, `facts.json`,
`expanded.json`, `violations.json`, `chains.json`, `report.md`, `result.json`,
`usage.jsonl` (per-call token usage + cost estimate), `status.json`.

## Guardrails

`config.py`: ≤60 pages, ≤80 MB, vision images ≤2576px long edge, 3 concurrent
vision calls, confidence threshold 0.6 (below → "needs review", not asserted).
