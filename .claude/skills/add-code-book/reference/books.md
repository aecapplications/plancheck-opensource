# Per-book notes

These are stable facts about each book. For current progress, run
`scripts/book_status.py`; this file deliberately records none.

## CRC — 2022 California Residential Code (Title 24 Part 2.5)

- This is the reference book. The parity baseline (`tests/parity-baseline/`)
  is a CRC FAKE-mode job, so any pipeline change must keep it
  byte-identical (`python tools/parity_gate.py`).
- Its 21 dispatch prompts are **hand-authored**. Never run
  `make_dispatch.py` on `crc-graph`.
- `decompose.py` uses the older `any_of_capture_sdcs` variant, which is
  CRC-only. New books copy cec's.
- Chapter manifest bookmark level: 1. Large chapters are split `_a`/`_b`.
- About half of its packs predate the dispatch template and use free-text
  `tested_per` values (e.g. `"ASTM E119"`), so `validate_pack.py` flags
  them. That's known legacy; don't rewrite them unless asked. New packs for
  any book must pass.

## CEC — 2022 California Electrical Code (Title 24 Part 3)

- This is the **canonical donor** for step 3 scaffolding and for
  `predicate_decomposition.json` and sample-facts shape.
- Prompts come from `make_dispatch.py` (`_CEC_META`). Typical remaining
  work is step 5 in batches, then step 6, growing
  `predicate_decomposition.json` when new predicate families need bridging
  to extracted facts.
- Cites look like `210.8(A)(1)`; the model jurisdiction is `model_NEC`.
- Chapter manifest bookmark level: 1.

## CBC — 2022 California Building Code (Title 24 Part 2)

- The graph and dispatch prompts exist (`_CBC_META`, label-free path) and
  are current. Don't regenerate the prompts unless the graph or the
  `make_dispatch.py` template changes; if you do, check that `git diff` is
  limited to the intended change.
- Node ids look like `ch15_section_1501_general`. Adapt `chain.py`'s three
  pieces to that convention (see [scaffold.md](scaffold.md)).
- `webapp/extractor/prompts/cbc.py` has stub prompts. Replace them with
  vocabulary-grounded ones in step 8. The `Book` entry exists with
  `sample_facts=None`; set it once step 7 has produced a facts file.
- Rough extraction budget: $60–150 for all packs.
- Chapter manifest bookmark level: 2.

## CALGreen — Title 24 Part 11 (not started)

- Run the full workflow from step 1. Expect a smaller corpus than CBC. The
  bookmark level for `init` is unknown: start at 1 and follow the tool's
  hints.
- Add a `calgreen-graph` entry to `BOOK_META` in `tools/make_dispatch.py`
  at step 4.
- Rough total: $90–200 (graphify $25–60 plus extraction).
