# Steps 4–5: dispatch prompts and rule-pack extraction

## Step 4 — Dispatch

```bash
python tools/make_dispatch.py --graph-dir <book>-graph [--min-nodes 10]
```

This writes `plan-check/.dispatch_plan.json` and one extraction prompt per
rule-bearing graph community in `plan-check/.prompts/c<cid>.txt`.

- It needs `chapters/`, because it resolves each community's source files
  from them. It exits with the rebuild command if they are missing.
- Output is deterministic. On an unchanged graph, re-running only changes
  prompts when the template in `make_dispatch.py` has changed. Review
  `git diff` after re-running.
- **Never run it on `crc-graph`.** CRC's 21 prompts are hand-authored and
  regenerating them would overwrite them.
- It works with or without `graphify-out/.graphify_labels.json`. Without
  it, community labels are synthesized from chapter stems and section
  titles.
- Always run and edit `tools/make_dispatch.py`.
  `cec-graph/plan-check/make_dispatch.py` is a backward-compatibility shim
  that forwards to it.
- A new book needs a `BOOK_META` entry in `tools/make_dispatch.py`; copy the
  `_CEC_META` or `_CBC_META` shape. Fields: `corpus_long`, `corpus_short`,
  `cite_example`, `model_jurisdiction`, `amendment_note`, `domain_name`,
  `conventions` (predicate-naming examples), `evidence_examples`,
  `cite_re`, `std_tokens`, `header_prefixes`. Without one, `DEFAULT_META`
  produces generic prompts.
- Check the skip list it prints. Only reference material (definitions
  chapters, indexes) should be skipped.

## Step 5 — Extract rule packs

Run one agent session per prompt. The session reads the chapter files the
prompt lists and writes `plan-check/c<cid>_<label>_rules.json` in the
shared rule schema; the schema is spelled out inside every prompt.

Pick the next prompts with the command below. "The next N" means its first
N ids, unless the user names specific packs.

```bash
python .claude/skills/add-code-book/scripts/book_status.py <book> --remaining
```

Run this loop per pack:

1. **Preflight.** If this fails, rebuild the chapters (step 1). Never let a
   session extract from memory:
   ```bash
   python tools/split_chapters.py check --book <book> --prompt c<cid>.txt
   ```
2. **Extract.** Give the session the full prompt file. Run independent packs
   as parallel subagents (one prompt each) when doing a batch.
3. **Validate**, and repeat until it passes. This checks that the file
   parses, that required fields are present, and that every
   `section_node`, `depends_on`, and `tested_per` is a node id in this
   book's `graph.json`:
   ```bash
   python .claude/skills/add-code-book/scripts/validate_pack.py <book>-graph/plan-check/c<cid>_*_rules.json
   ```
   On FAIL, send the errors back to the extraction session (or fix the ids
   from the prompt's lists yourself) and re-validate. Only integrate
   packs that pass.

Extraction quotes each section's load-bearing sentence in `verbatim`. That
anchors the model, and it is the only place the code text may appear.
Requirement fields (`title`, `intent`, `requires`, `evidence_required`)
must paraphrase rather than copy long passages.

Budget about 200–400k tokens ($2–5) per pack. Packs are independent:
extract them in any order and run step 6 after each batch.
