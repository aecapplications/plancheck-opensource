# plan-check

An automated building-code plan-check engine. Given a knowledge graph of the
**California Residential Code (CRC)** (built upstream by `graphify`, in
`../graphify-out/graph.json`) plus a description of a building project, it fires
the applicable code rules, links them into citation **chains**, and emits a
reviewer-ready Markdown report with an evidence checklist. Results can
optionally be fed back into the graph and an Obsidian vault.

## How it works

```
 CRC graph (../graphify-out/graph.json)
        │
        │  rule extraction (LLM, per graph community → .prompts/, .dispatch_plan.json)
        ▼
 c00…c24_*_rules.json   ──fixup_ids──▶ normalize_clauses ──▶ canonicalize ──▶ all_rules.json
                                                                                   │
 project facts (sample-facts/<project>.json)                                       │
        │                                                                          │
        ▼  decompose.py (expand facts to fixed point)                              │
 <project>.expanded.json ───────────────────────┐                                 │
                                                 ▼                                 ▼
                                            engine.py  ◀──────────────────────── rules
                                                 │  (evaluate applies_when / exceptions)
                                                 ▼
                                           violations.json
                                                 │
                                                 ▼  chain.py (walk depends_on edges)
                                            chains.json
                                                 │
                                                 ▼  render_report.py
                                       <project>-review.md
```

## Data

| Path | What it is |
|---|---|
| `c00_…json` … `c24_…json`, `wui_rules.json` | Rule packs, one per graph community (e.g. Wind/Seismic Bracing, Climate Criteria & Foundations, PV Systems & Roof Coverings). Each rule has `cite`, `title`, `intent`, `applies_when`, `requires`, `exceptions`, `evidence_required`, `depends_on`. |
| `all_rules.json` | Merged corpus of every pack (canonicalized predicates). |
| `canonical/` + `canonical/vocabulary.json` | Rule packs after predicate spellings are unified to a canonical vocabulary. |
| `predicate_decomposition.json` | Alias groups and compound predicates (e.g. `in_sdc_d0_or_d1 = any_of[d0, d1]`) used to expand a project's declared facts. |
| `sample-facts/` | Example projects (LA ADU, Truckee SFR, WUI dwelling) as `predicates` / `false_predicates` JSON, plus their expanded facts, violations, chains, and rendered `*-review.md` reports. |

Hidden working dirs: `.prompts/` (extraction prompts), `.dispatch_plan.json` /
`.dispatch_manifest.json` (extraction job plan), `.normalize/` & `.fixup/`
(pre-transform backups), `.skip-traces/` (per-project skipped-rule traces),
`.predicate_survey.json`.

## Scripts

Run from this directory. Requires `networkx`.

1. **`fixup_ids.py`** — fuzzy-repairs broken graph node IDs / `depends_on` references in the extracted packs against the real graph (writes `.fixup/` backups + `remap.json`).
2. **`normalize_clauses.py`** — normalizes all `applies_when` / `exception` clauses to a single canonical form the engine understands (`.normalize/` backups).
3. **`canonicalize.py <rules.json…>`** — merges spelling variants of predicates across packs → `vocabulary.json` + `*.canonical.json`.
4. **`integrate.py`** — validates every pack against the graph, canonicalizes, builds `all_rules.json`, and runs the engine on the sample facts.
5. **`decompose.py <facts.json> <rules.json> <expanded_facts.json>`** — expands declared atomic facts into the full composite predicate set (aliases + decomposition, to a fixed point).
6. **`engine.py <facts.json> <rules.json> [out.json]`** — core evaluator: matches each rule's `applies_when` (`any_of` / `all_of` / `not`) against the fact set, suppresses rules whose exceptions match, emits violations with cites + required evidence.
7. **`chain.py <all_rules.json> <violations.json> <out.json>`** — walks `depends_on` edges (networkx) to group fired rules into compliance chains (weakly-connected components), dedupes evidence, flags cross-pack chains and terminal standards.
8. **`render_report.py <facts.json> <rules.json> <violations.json> <chains.json> <out.md>`** — renders the final Markdown plan-check report (summary table, per-chain rule cards, evidence checklists).

### Feeding results back (optional)

- **`connect_graphify.py`** — adds project/chain nodes into `../graphify-out/graph.json` (backup at `.before-plancheck`) and annotates rule nodes with where they fired/were skipped; writes `.skip-traces/`.
- **`wire_obsidian.py <facts.json> <rules.json> <violations.json> <chains.json>`** — creates Obsidian vault notes so chains appear as an overlay on the graph view.
- **`threshold_sweep.py`** — sweeps the `min_graph_confidence` threshold and reports chain-compression metrics.

## End-to-end example

```bash
# Expand a project's facts, run the engine, chain, and render a report.
python decompose.py     sample-facts/urban-infill-adu-la.json all_rules.json \
                        sample-facts/urban-infill-adu-la.expanded.json
python engine.py        sample-facts/urban-infill-adu-la.expanded.json all_rules.json \
                        /tmp/violations.json
python chain.py         all_rules.json /tmp/violations.json /tmp/chains.json
python render_report.py sample-facts/urban-infill-adu-la.expanded.json all_rules.json \
                        /tmp/violations.json /tmp/chains.json sample-facts/la-adu-review.md
```

See `sample-facts/la-adu-review.md` and `sample-facts/truckee-sfr-review.md` for
rendered output.

## A note on provenance

The rule packs were LLM-extracted from CRC code sections (one job per graph
community; see `.prompts/` and `.dispatch_plan.json`) and then mechanically
validated/canonicalized by the scripts above. Citations and evidence items
should be spot-checked against the source code before relying on a report.
