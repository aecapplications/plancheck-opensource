"""
Dispatch-plan + extraction-prompt generator for any code-book graph.

Reads a book's graphify output, picks the rule-bearing communities, and emits
one LLM rule-extraction prompt per community plus a machine-readable dispatch
plan. Generalized from cec-graph/plan-check/make_dispatch.py (which is now a
shim over this tool) so CBC, CALGreen, and future books need no new code.

Usage:
  python tools/make_dispatch.py --graph-dir cec-graph [--min-nodes N]

Reads (under --graph-dir):
  graphify-out/graph.json             — the knowledge graph (node-link)
  graphify-out/.graphify_labels.json  — community-id → human label (OPTIONAL;
                                        labels are synthesized from dominant
                                        chapter-file stems / section-title
                                        tokens when the file is absent)
  chapters/*.txt|*.md                 — referenced by the prompts (not parsed)

Writes (under --graph-dir/plan-check/, created if needed):
  .dispatch_plan.json   — [{cid, label, out_filename, n_sections, ...}, ...]
  .prompts/c<cid>.txt   — one rule-extraction prompt per selected community

Selection: communities with >= --min-nodes nodes (default 10), skipping any
with zero rule-bearing sections.

NOTE: this generator does NOT run any LLM. Feed the emitted prompts to a
model to produce the c<cid>_*_rules.json packs (see .claude/skills/add-code-book/).

Node classification (off id + label, since many nodes have null source_location):
  table     — id has _table_  or label starts "Table"
  figure    — id has _figure_ or label starts "Figure"
  standard  — id has _agency_ or a standards token (book-specific set)
  term      — id has _term_   or label "(defined term)"
  header    — label/source_location starts with a header prefix (reference)
  section   — label or source_location leads with a cite      (RULE-BEARING)
  other     — everything else                                 (reference)
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from networkx.readwrite import json_graph

REPO_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# Per-book metadata. The cec-graph entry reproduces the original generator's
# strings and regexes EXACTLY — regenerating CEC's dispatch plan must be a
# byte-level no-op. Unknown graph dirs fall back to DEFAULT_META.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class BookMeta:
    corpus_long: str          # intro sentence: "...rule pack from the <this>"
    corpus_short: str         # container "source_corpus" value
    cite_example: str
    model_jurisdiction: str   # e.g. model_NEC / model_IBC
    amendment_note: str       # parenthetical for the California-amendment rule
    domain_name: str          # "electrical domain" etc.
    conventions: str          # bullet lines under "Predicate naming conventions"
    evidence_examples: str    # parenthetical list for evidence_required guidance
    cite_re: str              # leading-cite regex for section detection
    std_tokens: str           # standards tokens for the standard classifier
    header_prefixes: tuple = ("Article",)
    # Books whose section nodes are labeled "Section 1501 General": strip the
    # word and accept a bare section number as a cite. Off for CEC (parity).
    strip_section_word: bool = False
    bare_cite_re: str | None = None


# `_`-delimited token match — `\b` does NOT work because `_` is a regex word
# char, so `\bnec\b` never fires inside `..._code_nec`.
_CEC_META = BookMeta(
    corpus_long=("2022 California Electrical Code (Title 24 Part 3, which "
                 "adopts the 2020 NEC with California amendments)"),
    corpus_short="2022 California Electrical Code (Title 24 Part 3)",
    cite_example="210.8(A)(1)",
    model_jurisdiction="model_NEC",
    amendment_note="CEC-specific or HCD/SFM-marked section",
    domain_name="electrical domain",
    conventions="""- Specific over generic: `in_wet_location` not `in_bad_spot`; `is_class_i_division_1` not `is_hazardous`
- Numeric thresholds inline: `circuit_rating_>=_20a`, `voltage_to_ground_>_277v`, `conductor_size_<_8_awg`
- Boolean facts: `is_gfci_protected`, `is_dwelling_unit_receptacle`, `is_metallic_raceway`""",
    evidence_examples=("panel schedules, conductor/conduit specs, listing "
                       "labels, calculations, test reports, one-line diagrams"),
    cite_re=r'^(\d+\.\d+(?:\.\d+)*(?:\([A-Za-z0-9]+\))*)',
    std_tokens=r'(?:^|_)(nec|nfpa|ul|ansi|astm|ieee|nema|iec|api|asme)(?:_|$)',
    header_prefixes=("Article",),
)

_CBC_META = BookMeta(
    corpus_long=("2022 California Building Code (Title 24 Part 2, based on "
                 "the 2021 IBC with California amendments)"),
    corpus_short="2022 California Building Code (Title 24 Part 2)",
    cite_example="1010.1.2",
    model_jurisdiction="model_IBC",
    amendment_note="CBC-specific or state-agency-marked section, e.g. [DSA], [OSHPD], [SFM], or an -A/-B suffixed chapter",
    domain_name="building domain",
    conventions="""- Specific over generic: `is_group_r2_occupancy` not `is_residentialish`; `is_type_va_construction` not `is_wood`
- Numeric thresholds inline: `occupant_load_>=_50`, `travel_distance_>_250_ft`, `fire_separation_distance_<_10_ft`
- Boolean facts: `is_sprinklered_nfpa13`, `is_rated_corridor`, `is_accessible_route`""",
    evidence_examples=("code analysis, occupancy/egress plans, rated assembly "
                       "details and listings, occupant load and travel "
                       "distance calculations, accessibility details"),
    cite_re=r'^([A-Z]{0,2}\d+[A-Z]{0,2}(?:[-.][0-9A-Za-z]+)+(?:\([A-Za-z0-9]+\))*)',
    std_tokens=(r'(?:^|_)(nfpa|ul|ansi|astm|ieee|asce|aci|aisc|awc|tms|'
                r'ashrae|iapmo|iec|asme|awpa|doc|gypsum)(?:_|$)'),
    header_prefixes=("Article", "Chapter", "Part", "Appendix", "Division"),
    strip_section_word=True,
    bare_cite_re=r'^([A-Z]{0,2}\d{3,4}[A-Z]{0,2})\b',
)

DEFAULT_META = BookMeta(
    corpus_long="the code corpus this graph was built from",
    corpus_short="(see graph source)",
    cite_example="101.2.1",
    model_jurisdiction="model_code",
    amendment_note="California-specific or state-agency-marked section",
    domain_name="code domain",
    conventions="""- Specific over generic: name the exact condition the code text states
- Numeric thresholds inline: `some_measure_>=_20`, `distance_<_10_ft`
- Boolean facts: `is_<specific_thing>`, `has_<specific_feature>`""",
    evidence_examples=("plans, schedules, calculations, listings, details, "
                       "and reports a plan-checker would look for"),
    cite_re=_CBC_META.cite_re,
    std_tokens=_CBC_META.std_tokens,
    header_prefixes=_CBC_META.header_prefixes,
)

BOOK_META = {
    "cec-graph": _CEC_META,
    "cbc-graph": _CBC_META,
    "crc-graph": BookMeta(
        corpus_long=("2022 California Residential Code (Title 24 Part 2.5, "
                     "based on the 2021 IRC with California amendments)"),
        corpus_short="2022 California Residential Code (Title 24 Part 2.5)",
        cite_example="R507.3",
        model_jurisdiction="model_IRC",
        amendment_note="CRC-specific or HCD/SFM-marked section",
        domain_name="residential building domain",
        conventions="""- Specific over generic: `in_wildland_urban_interface_fire_area` not `in_fire_zone`
- Numeric thresholds inline: `stories_>=_3`, `deck_height_>_30_in`
- Boolean facts: `has_attached_garage`, `is_bedroom`, `has_egress_window`""",
        evidence_examples=("floor plans, framing plans, foundation details, "
                           "schedules, energy forms, manufacturer listings"),
        cite_re=r'^([A-Z]{0,2}\d+[A-Z]{0,2}(?:[-.][0-9A-Za-z]+)+(?:\([A-Za-z0-9]+\))*)',
        std_tokens=_CBC_META.std_tokens,
        header_prefixes=_CBC_META.header_prefixes,
        strip_section_word=True,
        bare_cite_re=_CBC_META.bare_cite_re,
    ),
}


def slugify(s: str) -> str:
    s = re.sub(r'[—–-]+', ' ', s.lower())
    s = re.sub(r'[^a-z0-9]+', '_', s)
    return s.strip('_')[:60]


class Dispatcher:
    def __init__(self, graph_dir: Path, meta: BookMeta):
        self.graph_dir = graph_dir
        self.meta = meta
        self.plan_dir = graph_dir / 'plan-check'
        self.prompts_dir = self.plan_dir / '.prompts'
        self.graph_path = graph_dir / 'graphify-out' / 'graph.json'
        self.labels_path = graph_dir / 'graphify-out' / '.graphify_labels.json'
        self.chapters_dir = graph_dir / 'chapters'
        self.cite_re = re.compile(meta.cite_re)
        self.std_re = re.compile(meta.std_tokens)
        self.bare_cite_re = (re.compile(meta.bare_cite_re)
                             if meta.bare_cite_re else None)

    # ---- node classification ------------------------------------------- #
    def cite_of(self, node: dict) -> str | None:
        """Leading section cite from the label (preferred) or source_location."""
        for src in (node.get('label') or '', node.get('source_location') or ''):
            s = src.strip()
            if self.meta.strip_section_word:
                s = re.sub(r'^Section\s+', '', s)
            m = self.cite_re.match(s)
            if m:
                return m.group(1)
            if self.bare_cite_re:
                m = self.bare_cite_re.match(s)
                if m:
                    return m.group(1)
        return None

    def classify(self, node: dict) -> str:
        i = node['id'].lower()
        lab = node.get('label') or ''
        sl = node.get('source_location') or ''
        if '_table_' in i or lab.startswith('Table'):
            return 'table'
        if '_figure_' in i or lab.startswith('Figure'):
            return 'figure'
        if '_agency_' in i or self.std_re.search(i):
            return 'standard'
        if '_term_' in i or '(defined term)' in lab.lower():
            return 'term'
        if lab.startswith(self.meta.header_prefixes) or sl.startswith(self.meta.header_prefixes):
            return 'header'
        if self.cite_of(node):
            return 'section'
        return 'other'

    # ---- chapter-file resolution ---------------------------------------- #
    def chapter_index(self) -> dict[str, str]:
        """Map a chapter file's leading token ('06', 'ch15', 'appa') → its
        relative path. Many nodes have an empty `source_file`; their chapter
        is recoverable from the node id's leading token."""
        idx = {}
        for pattern in ('*.txt', '*.md'):
            for p in sorted(self.chapters_dir.glob(pattern)):
                m = re.match(r'^([a-z0-9]+)_', p.name)
                if m:
                    idx[m.group(1)] = f'chapters/{p.name}'
        return idx

    def source_files_for(self, nodes: list[dict], chap_idx: dict[str, str]) -> list[str]:
        files = {n.get('source_file') for n in nodes if n.get('source_file')}
        for n in nodes:
            m = re.match(r'^([a-z0-9]+)_', n['id'])
            if m and m.group(1) in chap_idx:
                files.add(chap_idx[m.group(1)])
        return sorted(files)

    # ---- label synthesis (when .graphify_labels.json is absent) ---------- #
    def synthesize_label(self, cid: int, nodes: list[dict],
                         sections: list[dict]) -> str:
        stems = Counter()
        for n in nodes:
            name = Path(n.get('source_file') or '').name
            m = re.match(r'^[a-z0-9]+_(.+)\.(?:txt|md)$', name)
            if m:
                stems[m.group(1)] += 1
        if stems:
            stem = stems.most_common(1)[0][0]
            return stem.replace('_', ' ').title()[:70]
        # Fall back to the most common meaningful tokens in section titles.
        toks = Counter()
        for s in sections:
            title = self.cite_re.sub('', (s.get('label') or '').strip()).strip()
            for w in re.findall(r'[A-Za-z]{4,}', title)[:5]:
                toks[w.lower()] += 1
        if toks:
            return ' '.join(w.title() for w, _ in toks.most_common(3))
        return f'Community {cid}'

    # ---- prompt --------------------------------------------------------- #
    def build_prompt(self, cid: int, label: str, out_filename: str,
                     sections: list[dict], tables: list[dict], terms: list[dict],
                     standards: list[dict], source_files: list[str]) -> str:
        meta = self.meta
        plan_dir = self.plan_dir

        def row(n):
            return f'  {n["id"]:<60}  {(n.get("label") or "").strip()[:60]}'

        # Repo-relative paths so prompts carry no machine-local prefixes.
        files_block = '\n'.join(
            str((plan_dir.parent / f).relative_to(REPO_ROOT)) for f in source_files) or '  (none)'
        sec_block = '\n'.join(row(n) for n in sections) or '  (none)'
        ref_nodes = tables + terms
        ref_block = '\n'.join(row(n) for n in ref_nodes) or '  (none)'
        std_block = '\n'.join(row(n) for n in standards) or '  (none — no referenced standards in this community)'
        out_path = (plan_dir / out_filename).relative_to(REPO_ROOT)
        extracted_from = json.dumps([Path(f).name for f in source_files])
        n_lo = max(8, len(sections) // 4)
        n_hi = max(n_lo + 4, len(sections))
        section_node_example = sections[0]["id"] if sections else "..._210_8_a_1"

        return f'''You are a plan-check rule extraction subagent. The graph community "{label}" has been identified as a coherent rule pack from the {meta.corpus_long}. Your job is to read the source files and produce a structured rules.json file that a plan-check rule engine could execute.

Files to read in full:
{files_block}

If any file above is missing, STOP and report which ones — never write rules from memory. (Code-book text is not distributed; it is regenerated locally with tools/split_chapters.py.)

Output path (relative to the repo root): {out_path}

Rule-bearing sections to extract (one rule per section that contains a 'shall' requirement; some sections may yield multiple rules if they have distinct provisions):

{sec_block}

Other graph nodes in this community (tables, defined terms — DO NOT generate standalone rules for these, but reference them in `applies_when`, `requires`, or `depends_on` when the source text cites them):
{ref_block}

Standards / referenced codes available for `tested_per` and `depends_on` (use these existing graph IDs):
{std_block}

For each rule-bearing section produce a JSON rule object matching this schema:

{{
  "id": "rule_<section_normalized>",
  "cite": "{meta.cite_example}",
  "section_node": "<the graph node id from the list above, e.g. {section_node_example}>",
  "title": "<short imperative title>",
  "intent": "<one sentence WHY>",
  "applies_when": [ {{...predicate clauses, can nest with any_of/all_of/not...}} ],
  "requires": {{ "type": "<category>", ...structured constraints..., "tested_per": ["<std node id>"] }},
  "exceptions": [ {{ "id": "ex1", "applies_when": [...], "effect": "rule_does_not_apply" }} ],
  "evidence_required": [ "<concrete plan-check deliverable 1>", ... ],
  "depends_on": [ "<graph node ID>", ... ],
  "amends": null,
  "jurisdiction": "California" | "{meta.model_jurisdiction}",
  "severity": "required" | "advisory",
  "verbatim": "<the most load-bearing sentence quoted from source>"
}}

Predicate naming conventions ({meta.domain_name}):
- snake_case
{meta.conventions}
- Composite: any_of, all_of, not (with "of" or "clauses" key for nested)

Rules:
1. ONE rule per section unless the section has clearly distinct sub-provisions (then split with id suffix _a/_b).
2. Use the existing graph node IDs (listed above) for `section_node`, `tested_per`, `depends_on` — copy them verbatim.
3. EXTRACTED triggers only — do not invent conditions the code doesn't state.
4. ALWAYS quote the load-bearing sentence in `verbatim` (it anchors the extraction; tools/strip_verbatim.py removes it before anything is committed to the public repo).
5. `evidence_required`: 2-5 concrete deliverables a plan-checker would actually look for ({meta.evidence_examples}).
6. California amendments: set `jurisdiction: "California"` ({meta.amendment_note}); otherwise `"{meta.model_jurisdiction}"`.
7. Each exception is a separate object in `exceptions`.
8. If a section has no operative requirement (purely a header pointing to subsections), produce a "scope" rule capturing the trigger conditions for the subtree.

Wrap rules in this top-level container:

{{
  "schema_version": "0.1",
  "source_corpus": "{meta.corpus_short}",
  "rule_pack": "{label}",
  "community_id": {cid},
  "extracted_from_sections": {extracted_from},
  "rules": [ ... ]
}}

Aim for {n_lo}-{n_hi} rules. After writing the file, just confirm "wrote {out_filename} with N rules" and stop.
'''

    # ---- main ------------------------------------------------------------ #
    def run(self, min_nodes: int) -> None:
        data = json.loads(self.graph_path.read_text())
        G = json_graph.node_link_graph(data, edges='links')
        labels = (json.loads(self.labels_path.read_text())
                  if self.labels_path.exists() else None)
        if labels is None:
            print(f'{self.labels_path.name} not found — synthesizing community '
                  f'labels from chapter stems / section titles')
        chap_idx = self.chapter_index()
        if not chap_idx:
            # Without chapters/ every prompt would silently get an incomplete
            # "Files to read" list — and overwrite the committed prompts.
            raise SystemExit(
                f'{self.chapters_dir} is missing or empty. Code-book text is '
                f'not distributed; regenerate it from your own copy of the PDF:'
                f'\n  python tools/split_chapters.py build --book '
                f'{self.chapters_dir.parent.name.removesuffix("-graph")} '
                f'--pdf <path>')

        by_comm: dict[int, list[dict]] = defaultdict(list)
        for nid, attrs in G.nodes(data=True):
            node = {'id': nid, **attrs}
            by_comm[node.get('community')].append(node)

        selected = sorted(
            [c for c, ns in by_comm.items() if c is not None and len(ns) >= min_nodes],
            key=lambda c: -len(by_comm[c]),
        )

        self.plan_dir.mkdir(parents=True, exist_ok=True)
        self.prompts_dir.mkdir(exist_ok=True)
        plan = []
        skipped = []
        for cid in selected:
            nodes = by_comm[cid]
            buckets = defaultdict(list)
            for n in nodes:
                buckets[self.classify(n)].append(n)
            sections = sorted(buckets['section'], key=lambda n: self.cite_of(n) or n['id'])
            if labels is not None:
                label = labels.get(str(cid), f'Community {cid}')
            else:
                label = self.synthesize_label(cid, nodes, sections)
            if not sections:
                skipped.append((cid, label, len(nodes)))
                continue
            tables = sorted(buckets['table'], key=lambda n: n['id'])
            terms = sorted(buckets['term'] + buckets['other'], key=lambda n: n['id'])
            standards = sorted(buckets['standard'], key=lambda n: n['id'])
            source_files = self.source_files_for(nodes, chap_idx)

            out_filename = f'c{cid:02d}_{slugify(label)}_rules.json'
            prompt_rel = f'.prompts/c{cid:02d}.txt'

            prompt = self.build_prompt(cid, label, out_filename, sections,
                                       tables, terms, standards, source_files)
            (self.plan_dir / prompt_rel).write_text(prompt)

            plan.append({
                'cid': cid,
                'label': label,
                'out_filename': out_filename,
                'n_sections': len(sections),
                'n_tables': len(tables),
                'n_standards': len(standards),
                'n_files': len(source_files),
                'prompt_path': f'plan-check/{prompt_rel}',
                'description': f'Extract rules for c{cid}: {label[:55]}',
            })

        (self.plan_dir / '.dispatch_plan.json').write_text(json.dumps(plan, indent=2))

        print(f'min-nodes threshold: {min_nodes}')
        print(f'selected communities: {len(selected)}  →  emitted {len(plan)} prompt(s)')
        print(f'skipped (no rule-bearing sections): {len(skipped)}')
        for cid, lab, n in skipped:
            print(f'  cid {cid} (n={n}): {lab}')
        print(f'\nwrote {self.plan_dir / ".dispatch_plan.json"}')
        print(f'wrote {len(plan)} prompts to {self.prompts_dir}')
        total_sections = sum(p['n_sections'] for p in plan)
        print(f'total rule-bearing sections across packs: {total_sections}')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('--graph-dir', required=True,
                    help="book graph directory, e.g. cec-graph (relative to the repo root)")
    ap.add_argument('--min-nodes', type=int, default=10,
                    help='minimum community size to emit a pack for (default 10)')
    args = ap.parse_args(argv)

    graph_dir = Path(args.graph_dir)
    if not graph_dir.is_absolute():
        graph_dir = REPO_ROOT / graph_dir
    if not (graph_dir / 'graphify-out' / 'graph.json').is_file():
        ap.error(f'no graphify-out/graph.json under {graph_dir}')

    meta = BOOK_META.get(graph_dir.name, DEFAULT_META)
    Dispatcher(graph_dir, meta).run(args.min_nodes)


if __name__ == '__main__':
    main()
