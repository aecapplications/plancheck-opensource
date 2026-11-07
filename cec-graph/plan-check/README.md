# plan-check (CEC)

An automated building-code plan-check engine for the **2022 California Electrical
Code** (Title 24 Part 3, which adopts the 2020 NEC with California amendments).
Given the `graphify` knowledge graph in `../graphify-out/graph.json` plus a project's
facts, it fires the applicable code rules, links them into citation **chains**, and
emits a reviewer-ready Markdown report with an evidence checklist. It is a port of
`crc-graph/plan-check/` (California Residential Code), adapted to the CEC graph.

## Status

This directory contains the **pipeline, the dispatch generator's outputs, and
9 of 41 extracted rule packs (442 rules)** — Article 378 wireways plus the
Tier 1 wave (branch circuits, GFCI, receptacles, working space, load calcs,
grounded conductor). Remaining packs are produced by feeding the prompts in
`.prompts/` to an LLM (the one paid step; see *Extraction* below). Everything
else is deterministic Python.

```
 CEC graph (../graphify-out/graph.json, ../graphify-out/.graphify_labels.json)
        │
        ▼  make_dispatch.py                          ← DONE (deterministic, $0)
 .dispatch_plan.json + .prompts/c<cid>.txt
        │
        ▼  run each prompt through an LLM            ← YOU RUN THIS (the paid step)
 c<cid>_<slug>_rules.json  (one rule pack per community)
        │
        ▼  fixup_ids → normalize_clauses → canonicalize → integrate
 all_rules.json (+ canonical/, vocabulary.json)
        │
 project facts (sample-facts/<project>.json)
        │
        ▼  decompose → engine → chain → render_report
 <project>-review.md
```

## How CEC differs from CRC (what was adapted)

1. **Node-ID convention.** CRC used prefixes (`section_r602_10_6`, `std_*`,
   `table_*`). CEC uses `<chapter-file-stem>_<section>`, e.g.
   `06_chapter_3_..._article_300_..._300_3_b_1`, with tables as `..._table_110_28`,
   defined terms as `..._term_*`, and referenced codes/standards as `..._code_nec` /
   `..._agency_nfpa`. The bare section cite lives in the node `label`
   (`source_location` is often null). `chain.py` (`_section_core`, `is_terminal`) and
   `fixup_ids.py` (`section_core`, `looks_legitimate`, `find_match`) were rewritten
   for this convention.
   - Gotcha baked into the code: `_` is a regex *word* char, so `\bnec\b` never
     matches inside `..._code_nec`, and a bare `_code_` substring wrongly flags
     `general_code_provisions`. Standards detection therefore uses
     `(?:^|_)(nec|nfpa|...)(?:_|$)`, not `\b...\b` or `_code_`.
2. **Domain vocabulary.** `canonicalize.py` `CATEGORY_KEYWORDS` and
   `predicate_decomposition.json` were re-authored for the electrical domain
   (voltage/amperage classes, wet/damp/hazardous locations, wiring methods,
   listed/labeled equipment) — categories `LOCATION, EQUIPMENT, ELECTRICAL,
   WIRING_METHOD, PROCEDURAL`.
3. **Reproducible dispatch.** CRC's `.dispatch_plan.json` / prompts were
   hand-authored. Here `make_dispatch.py` generates them from the graph, keyed to
   the authoritative `../graphify-out/.graphify_labels.json` (community labels
   already map to CEC Articles, e.g. *"Wiring Methods — Article 300"*).

## Files

| Path | What it is |
|---|---|
| `make_dispatch.py` | **NEW** — reads the graph + community labels, selects rule-bearing communities, writes `.dispatch_plan.json` and one `.prompts/c<cid>.txt` extraction prompt per community. `--min-nodes N` (default 10 → 41 packs; 5 → ~81). |
| `.dispatch_plan.json` | Generated plan: `cid`, `label`, `out_filename`, `n_sections`, `n_files`, `prompt_path`. |
| `.prompts/c<cid>.txt` | Generated extraction prompts (one per community). |
| `predicate_decomposition.json` | Electrical-domain alias groups, compound predicates, regex patterns (used by `decompose.py`). |
| `engine.py` | Predicate evaluator (`any_of`/`all_of`/`not`, exceptions). Copied as-is. |
| `normalize_clauses.py` | Normalizes `applies_when` clause forms. Copied as-is. |
| `canonicalize.py` | Unifies predicate spellings → `vocabulary.json` (+ electrical taxonomy). |
| `decompose.py` | Expands declared facts to a fixed point via the decomposition table. |
| `chain.py` | Groups fired rules into compliance chains (CEC id/terminal logic). |
| `integrate.py` | Validates packs against graph IDs, canonicalizes, builds `all_rules.json`, runs engine on sample facts. Copied as-is. |
| `fixup_ids.py` | Fuzzy-repairs broken `section_node`/`depends_on` IDs against the graph (CEC id logic). |
| `render_report.py` | Renders the Markdown plan-check report. Copied as-is. |
| `wire_obsidian.py` | Writes chain notes into `../graphify-out/obsidian/`. Copied as-is. |
| `threshold_sweep.py` | Chain-compression metric sweep. Copied as-is. |

Every script resolves the graph at `PLAN_DIR.parent / 'graphify-out' / 'graph.json'`,
so no paths need editing.

## Extraction (the step you run)

Each `.prompts/c<cid>.txt` is a self-contained instruction to read the named
chapter file(s) under `../chapters/` and emit a `c<cid>_<slug>_rules.json` rule pack
(schema in the prompt: `id`, `cite`, `section_node`, `title`, `applies_when`,
`requires`, `exceptions`, `evidence_required`, `depends_on`, `jurisdiction`,
`severity`, `verbatim`). Run them via subagents, the Batches API, or any LLM. Then:

```bash
python fixup_ids.py                       # repair any unresolved graph IDs
python normalize_clauses.py               # canonicalize applies_when clause forms
python integrate.py                       # canonicalize + build all_rules.json + validate

# per project (once sample-facts exist):
python decompose.py     sample-facts/<proj>.json all_rules.json sample-facts/<proj>.expanded.json
python engine.py        sample-facts/<proj>.expanded.json all_rules.json /tmp/violations.json
python chain.py         all_rules.json /tmp/violations.json /tmp/chains.json
python render_report.py sample-facts/<proj>.expanded.json all_rules.json /tmp/violations.json /tmp/chains.json sample-facts/<proj>-review.md
```

Regenerate prompts at any time: `python make_dispatch.py [--min-nodes N]`.

## Notes / caveats

- **Annex examples.** A few communities pull in Annex D worked-example nodes (e.g.
  "13.1", "200.0"); the prompts say to extract only sections with `shall`
  requirements, so the extractor should skip non-normative examples.
- **`sample-facts/`** is not yet authored — create CEC project facts (electrical
  `predicates` / `false_predicates`) once rules exist; mirror the CRC sample-facts
  format.
- The rule packs are LLM-extracted; spot-check citations and evidence against the
  source code before relying on a report.
