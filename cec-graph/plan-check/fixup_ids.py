"""
Auto-fixup of validation errors in extracted rule packs.

Strategy:
  Pass 1 — collect every missing ID from every rule pack (section_node, depends_on)
  Pass 2 — fuzzy-match each missing ID against existing graph node IDs (CEC):
              a) direct / case-insensitive match
              b) table/figure: match by bare section-number core within a table/figure node
              c) standards: match a code/agency node by token (nec/nfpa/ul/...)
              d) section: graph id whose trailing section-number core equals this one
  Pass 3 — write remap.json (alias → canonical)
  Pass 4 — auto-create new graph nodes for any unresolvable IDs that look legitimate
              (real-looking section, table, figure, or std identifier)
  Pass 5 — apply remap to every rule pack (with .pre-fixup backup)
  Pass 6 — re-validate; report error delta
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from networkx.readwrite import json_graph
import networkx as nx


PLAN_DIR = Path(__file__).parent
GRAPH_PATH = PLAN_DIR.parent / 'graphify-out' / 'graph.json'
PACK_GLOB = '*_rules.json'  # both wui and c?? packs


def load_graph():
    data = json.loads(GRAPH_PATH.read_text())
    return data, json_graph.node_link_graph(data, edges='links')


def collect_missing_ids(packs: list[tuple[Path, dict]], graph_ids: set[str]) -> dict[str, list[str]]:
    """Return {missing_id: [rule_id, rule_id, ...]} across all packs."""
    missing = defaultdict(list)
    for path, pack in packs:
        for r in pack.get('rules', []):
            rid = f'{path.stem}::{r["id"]}'
            sn = r.get('section_node')
            if sn and sn not in graph_ids:
                missing[sn].append(rid)
            for d in r.get('depends_on') or []:
                if d not in graph_ids:
                    missing[d].append(rid)
    return missing


# `_`-delimited token match — `\b` does NOT fire next to `_` (a regex word char),
# so `\bnec\b` never matches inside `..._code_nec`.
STD_TOKEN_RE = re.compile(r'(?:^|_)(nec|nfpa|ul|ansi|astm|ieee|nema|iec|api|asme)(?:_|$)')


def section_core(s: str) -> str:
    """Bare section-number token of a CEC id or cite.

    `..._article_300_..._300_3_b_1` → `300_3_b_1`;  `210.8(A)(1)` → `210_8_a_1`.
    """
    if not s:
        return ''
    # cite form (210.8(A)(1)) → underscores
    if re.match(r'^\d+\.\d', s) or '(' in s:
        return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')
    # id form: trailing run of digit-led tokens + interleaved single letters
    parts = s.lower().split('_')
    core = []
    for tok in reversed(parts):
        if re.fullmatch(r'\d+[a-z]?', tok) or (len(tok) == 1 and tok.isalpha() and core):
            core.append(tok)
        else:
            break
    core.reverse()
    return '_'.join(core)


def normalize_candidate(candidate: str) -> list[str]:
    """Generate alternate forms of a candidate ID for fuzzy matching."""
    forms = {candidate, candidate.lower()}
    core = section_core(candidate)
    if core:
        forms.add(core)
    return list(forms)


def find_match(missing_id: str, graph_ids: set[str], graph_id_index: dict[str, list[str]]) -> str | None:
    """Try to match a missing ID to an existing CEC graph ID. Returns the canonical ID or None."""
    # Layer 1 — direct (case-insensitive) match
    for form in normalize_candidate(missing_id):
        if form in graph_ids:
            return form
    lower_index = {nid.lower(): nid for nid in graph_ids}
    if missing_id.lower() in lower_index:
        return lower_index[missing_id.lower()]

    core = section_core(missing_id)

    # Layer 2 — table/figure: match by core within a table/figure node
    s = missing_id.lower()
    if 'table' in s or 'figure' in s:
        marker = '_table_' if 'table' in s else '_figure_'
        for existing in graph_ids:
            el = existing.lower()
            if marker in el and core and el.endswith('_' + core):
                return existing

    # Layer 3 — standards / referenced codes: match by token
    if STD_TOKEN_RE.search(s) or any(c.isupper() for c in missing_id):
        for existing in graph_ids:
            el = existing.lower()
            if ('_agency_' in el or STD_TOKEN_RE.search(el)) and core and core in el:
                return existing

    # Layer 4 — section: graph id whose trailing section-number equals this core
    if core:
        hits = [nid for nid in graph_ids if section_core(nid) == core]
        if len(hits) == 1:
            return hits[0]
        # prefer the shortest id (least stem cruft) when several share a core
        if hits:
            return min(hits, key=len)

    return None


def looks_legitimate(missing_id: str) -> str | None:
    """Decide whether a missing ID is genuinely a real CEC entity worth creating.

    Returns the inferred type ('section', 'table', 'figure', 'standard') or None.
    """
    s = missing_id.lower()
    if '_table_' in s or s.startswith('table'):
        return 'table'
    if '_figure_' in s or s.startswith('figure'):
        return 'figure'
    if '_agency_' in s or STD_TOKEN_RE.search(s) or any(c.isupper() for c in missing_id):
        return 'standard'
    # section: a dotted cite (210.8) or an id with a trailing section-number core
    if re.match(r'^\d+\.\d', s) or section_core(s):
        return 'section'
    return None


def derive_label(missing_id: str, kind: str, rule_packs: list[dict]) -> str:
    """Best-effort label for a new node."""
    # If a rule names this as its section_node, use its cite + title
    for pack in rule_packs:
        for r in pack.get('rules', []):
            if r.get('section_node') == missing_id:
                return f'{r.get("cite", missing_id)} {r.get("title","")[:40]}'.strip()
    core = section_core(missing_id)
    if kind == 'section':
        # 300_3_b_1 → 300.3(B)(1)-ish dotted form
        cite = re.sub(r'_([a-z])(?=_|$)', r'(\1)', core).replace('_', '.').upper()
        return cite or missing_id
    if kind == 'standard':
        return missing_id.replace('_code_', ' ').replace('_agency_', ' ').upper().replace('_', ' ').strip()
    if kind == 'table':
        return 'Table ' + core.replace('_', '.')
    if kind == 'figure':
        return 'Figure ' + core.replace('_', '.')
    return missing_id


def main():
    data, G = load_graph()
    graph_ids = set(G.nodes())
    graph_id_index = {nid: nid for nid in graph_ids}

    # Load all packs
    pack_paths = sorted(PLAN_DIR.glob(PACK_GLOB))
    # exclude all_rules.json (merged) from per-pack fixup
    pack_paths = [p for p in pack_paths if p.name != 'all_rules.json']
    packs = [(p, json.loads(p.read_text())) for p in pack_paths]

    print(f'Loaded {len(packs)} rule packs, graph has {len(graph_ids)} nodes')

    # Pass 1
    missing = collect_missing_ids(packs, graph_ids)
    print(f'\nPass 1: {len(missing)} unique missing IDs across all packs')

    # Pass 2 — fuzzy match
    remap = {}      # missing_id → canonical_id (already in graph)
    unresolved = {} # missing_id → (kind, [rule refs])
    for mid, refs in missing.items():
        m = find_match(mid, graph_ids, graph_id_index)
        if m:
            remap[mid] = m
        else:
            kind = looks_legitimate(mid)
            if kind:
                unresolved[mid] = (kind, refs)
    print(f'Pass 2: {len(remap)} resolved by fuzzy match, {len(unresolved)} unresolved-but-legitimate')
    print(f'        {len(missing) - len(remap) - len(unresolved)} unresolvable (will leave as-is)')

    # Pass 3 — write remap.json
    fixup_dir = PLAN_DIR / '.fixup'
    fixup_dir.mkdir(exist_ok=True)
    (fixup_dir / 'remap.json').write_text(json.dumps(remap, indent=2, sort_keys=True))
    (fixup_dir / 'unresolved.json').write_text(json.dumps(
        {k: {'kind': v[0], 'rule_count': len(v[1]), 'sample_rules': v[1][:3]}
         for k, v in unresolved.items()}, indent=2, sort_keys=True))

    # Pass 4 — auto-create graph nodes for unresolved-but-legitimate
    new_node_count = 0
    for mid, (kind, refs) in unresolved.items():
        label = derive_label(mid, kind, [p for _, p in packs])
        file_type = 'document' if kind in ('section', 'table', 'figure') else 'paper'  # standards = 'paper' (closest existing type)
        G.add_node(mid, label=label, file_type=file_type, source_file='', auto_added=True, kind=kind)
        new_node_count += 1
    print(f'Pass 4: added {new_node_count} new nodes to graph (auto_added=true)')

    # Save augmented graph
    if new_node_count > 0:
        # Backup
        Path(str(GRAPH_PATH) + '.before-fixup').write_text(GRAPH_PATH.read_text())
        out = {
            'directed': data.get('directed', False),
            'multigraph': data.get('multigraph', False),
            'graph': data.get('graph', {}),
            'nodes': [{'id': n, **d} for n, d in G.nodes(data=True)],
            'links': [{'source': u, 'target': v, **d} for u, v, d in G.edges(data=True)],
        }
        GRAPH_PATH.write_text(json.dumps(out, indent=2))

    # Pass 5 — apply remap to every rule pack
    print(f'\nPass 5: applying remap to {len(packs)} rule packs')
    fixes_applied = 0
    for path, pack in packs:
        # backup
        backup = path.parent / '.fixup' / (path.stem + '.pre-fixup.json')
        backup.write_text(path.read_text())
        for r in pack.get('rules', []):
            if r.get('section_node') in remap:
                r['_was_section_node'] = r['section_node']
                r['section_node'] = remap[r['section_node']]
                fixes_applied += 1
            if r.get('depends_on'):
                new_deps = []
                for d in r['depends_on']:
                    if d in remap:
                        new_deps.append(remap[d])
                        fixes_applied += 1
                    else:
                        new_deps.append(d)
                r['depends_on'] = new_deps
        path.write_text(json.dumps(pack, indent=2))
    print(f'Applied {fixes_applied} ID fixes total')

    # Pass 6 — re-validate
    # reload graph IDs (new nodes added)
    graph_ids = set(G.nodes())
    new_packs = [(p, json.loads(p.read_text())) for p in pack_paths]
    final_missing = collect_missing_ids(new_packs, graph_ids)
    print(f'\nPass 6: {len(final_missing)} missing IDs remain after fixup')
    if final_missing:
        print('Sample remaining issues:')
        for mid in list(final_missing.keys())[:10]:
            print(f'  {mid:40s}  ({len(final_missing[mid])} rules)')


if __name__ == '__main__':
    main()
