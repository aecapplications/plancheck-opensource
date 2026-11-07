# CRC parity baseline

Byte-diff reference for the CRC plan-check pipeline. Any change anywhere in
the pipeline (webapp orchestration, plan-check scripts, registry) must keep a
FAKE-mode CRC job **byte-identical** to the artifacts in this directory —
this gate has protected every restructuring of the codebase, and it works
because the pipeline is fully deterministic (all set iterations in
`chain.py`/`decompose.py` are sorted; no seed pinning needed).

## Contents

- `sample.pdf` — the input plan set: "Marilyn's Farmhouse" by Jay Osborne
  (FreeFarmhouse.com), CC BY-SA 4.0 — see `NOTICE`. In FAKE mode only its
  page count (19) affects the artifacts.
- `facts.json`, `expanded.json`, `violations.json`, `chains.json`,
  `report.md`, `result.json` — the six expected artifacts
- `CHECKSUMS.txt` — sha256 of all six

Expected summary: **rules_fired=22, pages_flagged=15, chains=11** (facts come
from `crc-graph/plan-check/sample-facts/full-sfr-truckee.json`, the CRC
FAKE-mode fixture).

## Running the gate

One step: `python tools/parity_gate.py` (add `--update` to regenerate the
baseline after an intentional change). The manual procedure it automates:

```bash
EXTRACTOR_FAKE=1 uvicorn webapp.app:app --port 8000   # from the repo root
```

Upload `tests/parity-baseline/sample.pdf` **with the filename
`baseline-sample.pdf`** (result.json embeds the upload filename, so reusing
it keeps the diff clean), CRC selected (the default). When the job is done,
its artifacts are in `webapp/jobs/<job_id>/books/crc/` — byte-compare all six
against this directory:

```bash
cd webapp/jobs/<job_id>/books/crc && shasum -a 256 -c ../../../../../tests/parity-baseline/CHECKSUMS.txt
```

All six must report OK. Scripted upload, if preferred over the UI:

```bash
curl -s -F "file=@tests/parity-baseline/sample.pdf;filename=baseline-sample.pdf;type=application/pdf" \
     http://127.0.0.1:8000/api/jobs
```

## Diff rules

- `violations.json`, `chains.json`, `report.md`, `facts.json`,
  `expanded.json`: must match byte-for-byte, no exceptions.
- `result.json`: must currently match byte-for-byte too. If a future change
  legitimately adds new top-level keys (e.g. usage/aggregation metadata),
  compare `result.json` with those new keys excluded — every pre-existing
  key must still match exactly. Never exclude anything under `summary`,
  `pages`, `chains`, `unmapped_rules`, or `needs_review`.

## Regenerating the baseline

Only after an *intentional*, reviewed change to pipeline output: run the gate
procedure above, verify the differences are exactly the intended ones, then
copy the six artifacts from `books/crc/` over this directory and refresh
`CHECKSUMS.txt` (`shasum -a 256 <the six files> > CHECKSUMS.txt`) in the same
commit as the change that motivated it — or let
`python tools/parity_gate.py --update` do all of that.
