"""
Auto-fixup of validation errors in extracted rule packs.

Strategy:
  Pass 1 — collect every missing ID from every rule pack (section_node, depends_on)
  Pass 2 — fuzzy-match each missing ID against existing graph node IDs:
              a) strip 'section_' prefix
              b) ALLCAPS_FOO_BAR → std_foo_bar lowercase
              c) try with/without trailing qualifier (e.g. '_wind', '_seismic')
              d) longest-prefix match
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


def normalize_candidate(candidate: str) -> list[str]:
    """Generate alternate forms of a candidate ID for fuzzy matching."""
    forms = {candidate}
    # strip 'section_' prefix
    if candidate.startswith('section_'):
        forms.add(candidate[len('section_'):])
    else:
        forms.add('section_' + candidate)
    # ALLCAPS or mixed → lowercase std_ form
    if any(c.isupper() for c in candidate):
        lower = candidate.lower()
        forms.add(lower)
        if not lower.startswith(('std_', 'section_', 'table_', 'figure_', 'r')):
            forms.add('std_' + lower)
        # AWPA_U1 → std_awpa_u1
        forms.add('std_' + re.sub(r'[^a-z0-9]+', '_', lower).strip('_'))
    # table_/figure_ prefix swap
    for p in ('table_', 'figure_'):
        if candidate.startswith(p):
            forms.add(candidate[len(p):])
        else:
            forms.add(p + candidate)
    return list(forms)


def find_match(missing_id: str, graph_ids: set[str], graph_id_index: dict[str, list[str]]) -> str | None:
    """Try to match a missing ID to an existing graph ID. Returns the canonical ID or None."""
    # Layer 1 — try every alternate form for direct match
    for form in normalize_candidate(missing_id):
        if form in graph_ids:
            return form

    # Layer 2 — strip trailing qualifier suffixes ('_wind', '_seismic', '_general', ...)
    # e.g. section_r301_2_1 → section_r301_2_1_wind exists
    base = missing_id[len('section_'):] if missing_id.startswith('section_') else missing_id
    for form in (missing_id, 'section_' + base, base):
        for existing in graph_ids:
            if existing.startswith(form + '_'):
                # Only accept if the suffix is a single qualifier word
                tail = existing[len(form) + 1:]
                if '_' not in tail and len(tail) <= 12:
                    return existing

    # Layer 3 — for table/figure, drop double-paren-style (e.g. r905_10_3 → table_r905_10_3)
    if 'table' in missing_id or 'figure' in missing_id:
        suffix = missing_id.replace('table_', '').replace('figure_', '')
        for existing in graph_ids:
            if existing.endswith(suffix) and ('table' in existing or 'figure' in existing):
                return existing

    # Layer 4 — ALLCAPS standards: AWPA_U1 → std_awpa_u1
    if any(c.isupper() for c in missing_id):
        canon = 'std_' + re.sub(r'[^a-z0-9]+', '_', missing_id.lower()).strip('_')
        if canon in graph_ids:
            return canon

    return None


def looks_legitimate(missing_id: str) -> str | None:
    """Decide whether a missing ID is genuinely a real entity worth creating.

    Returns the inferred type ('section', 'table', 'figure', 'standard') or None.
    """
    s = missing_id.lower()
    if re.match(r'^(section_)?r\d{2,4}', s):
        return 'section'
    # Appendix sections: ah_105_1, au_103, section_ah_105_1, etc.
    if re.match(r'^(section_)?[a-z]{1,3}_?\d{2,4}', s):
        return 'section'
    # Appendix headers: section_appendix_ar, appendix_au, etc.
    if 'appendix_' in s:
        return 'section'
    if s.startswith('table_'):
        return 'table'
    if s.startswith('figure_'):
        return 'figure'
    if s.startswith('std_') or any(c.isupper() for c in missing_id):
        return 'standard'
    return None


def derive_label(missing_id: str, kind: str, rule_packs: list[dict]) -> str:
    """Best-effort label for a new node."""
    # If a rule has cite that matches this ID's section pattern, use cite as label
    s = missing_id.lower().replace('section_', '').replace('table_', '').replace('figure_', '')
    for pack in rule_packs:
        for r in pack.get('rules', []):
            if r.get('section_node') == missing_id:
                return f'{r.get("cite", missing_id)} {r.get("title","")[:40]}'.strip()
    # Reconstruct from ID
    if kind == 'section':
        # r322_1 → R322.1
        m = re.match(r'^(section_)?([a-z]+)?(\d+)(_\d+)*', s)
        # Just clean it up
        cleaned = re.sub(r'^section_', '', s).upper().replace('_', '.')
        return cleaned
    if kind == 'standard':
        return missing_id.replace('std_', '').upper().replace('_', ' ')
    if kind == 'table':
        return 'TABLE ' + s[len('table_'):].upper().replace('_', '.')
    if kind == 'figure':
        return 'Figure ' + s[len('figure_'):].upper().replace('_', '.')
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
