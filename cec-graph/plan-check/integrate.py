"""
Integration step (Stages 2 + 3 + 4 across all rule packs).

1. Validate every rule pack: check schema fields, graph node IDs resolve
2. Canonicalize predicates across all packs → vocabulary.json
3. Build all-rules.json (merged, with canonical predicates)
4. Run engine on sample facts against the merged rules

Usage:
  integrate.py
"""

import json
import sys
from pathlib import Path
from networkx.readwrite import json_graph

import canonicalize
import engine


PLAN_DIR = Path(__file__).parent
GRAPH_PATH = PLAN_DIR.parent / 'graphify-out' / 'graph.json'


def load_graph_ids() -> set[str]:
    data = json.loads(GRAPH_PATH.read_text())
    G = json_graph.node_link_graph(data, edges='links')
    return set(G.nodes())


def validate_pack(pack: dict, graph_ids: set[str]) -> dict:
    """Return {'ok': bool, 'errors': list, 'rule_count': int}"""
    errors = []
    rules = pack.get('rules', [])
    for r in rules:
        rid = r.get('id', '?')
        for f in ('cite', 'title', 'verbatim', 'jurisdiction', 'severity'):
            if not r.get(f):
                errors.append(f'{rid}: missing field "{f}"')
        sn = r.get('section_node')
        if sn and sn not in graph_ids:
            errors.append(f'{rid}: section_node "{sn}" not in graph')
        for d in r.get('depends_on') or []:
            if d not in graph_ids:
                errors.append(f'{rid}: depends_on "{d}" not in graph')
    return {'ok': not errors, 'errors': errors, 'rule_count': len(rules)}


def merge_packs(packs: list[dict]) -> dict:
    """Merge multiple rule packs into one document."""
    merged_rules = []
    pack_index = {}
    for p in packs:
        for r in p.get('rules', []):
            r2 = dict(r)
            r2['_rule_pack'] = p.get('rule_pack')
            r2['_community_id'] = p.get('community_id')
            merged_rules.append(r2)
        pack_index[p.get('rule_pack')] = p.get('community_id')
    return {
        'schema_version': '0.1',
        'source_corpus': '2022 California Residential Code (Title 24 Part 2.5)',
        'rule_pack': 'merged_all_communities',
        'pack_index': pack_index,
        'rules': merged_rules,
    }


def main():
    graph_ids = load_graph_ids()

    # Find all rule packs (exclude the merged all_rules.json which we generate ourselves)
    pack_paths = sorted(p for p in PLAN_DIR.glob('*_rules.json') if p.name != 'all_rules.json')
    print(f'Found {len(pack_paths)} rule pack files')

    # Validate
    all_packs = []
    total_rules = 0
    total_errors = 0
    print('\n=== Validation ===')
    for path in pack_paths:
        pack = json.loads(path.read_text())
        result = validate_pack(pack, graph_ids)
        total_rules += result['rule_count']
        total_errors += len(result['errors'])
        mark = '✅' if result['ok'] else '⚠️ '
        print(f'  {mark} {path.name:55s}  {result["rule_count"]:>3} rules, {len(result["errors"])} errors')
        if result['errors']:
            for e in result['errors'][:3]:
                print(f'         {e}')
            if len(result['errors']) > 3:
                print(f'         ... +{len(result["errors"])-3} more')
        all_packs.append(pack)

    print(f'\nTotal: {total_rules} rules, {total_errors} validation issues')

    # Canonicalize
    print('\n=== Canonicalization ===')
    canonical_dir = PLAN_DIR / 'canonical'
    canonical_dir.mkdir(exist_ok=True)
    canonicalize.main(pack_paths, canonical_dir)

    # Load canonicalized vocabulary for the report
    vocab = json.loads((canonical_dir / 'vocabulary.json').read_text())

    # Merge all canonical packs
    canonical_paths = sorted(canonical_dir.glob('*_rules.canonical.json'))
    canonical_packs = [json.loads(p.read_text()) for p in canonical_paths]
    merged = merge_packs(canonical_packs)
    merged_path = PLAN_DIR / 'all_rules.json'
    merged_path.write_text(json.dumps(merged, indent=2))
    print(f'\nMerged → {merged_path.name}: {len(merged["rules"])} rules from {len(canonical_packs)} packs')

    # Run engine on sample facts against the merged rules
    facts_path = PLAN_DIR / 'sample-facts' / 'wui-dwelling-with-pv.json'
    if facts_path.exists():
        print(f'\n=== Engine run on sample project ===')
        report = engine.run(facts_path, merged_path)
        out_path = PLAN_DIR / 'sample-facts' / 'all-violations.json'
        out_path.write_text(json.dumps(report, indent=2))
        s = report['summary']
        print(f'Project: {report["project"].get("address", "<unknown>")}')
        print(f'  rules evaluated: {s["rules_evaluated"]}')
        print(f'  rules fired:     {s["rules_fired"]}')
        print(f'  evidence items:  {s["evidence_items_required"]}')

    # Final summary
    print('\n=== Final summary ===')
    print(f'  rule packs:        {len(pack_paths)}')
    print(f'  total rules:       {total_rules}')
    print(f'  validation errors: {total_errors}')
    print(f'  vocabulary:        {vocab["predicate_count"]} predicates ({vocab["alias_count"]} aliases merged)')
    print(f'  by category:       {vocab["by_category"]}')


if __name__ == '__main__':
    main()
