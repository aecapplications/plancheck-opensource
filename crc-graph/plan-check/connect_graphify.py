"""
Connect plan-check output back into the graphify graph.

For each project:
  1. Add a `project` node with metadata (address, sdc, fhsz, fact count, etc.)
  2. Add one `chain` node per compliance chain
  3. Edge: project → chain  (relation: contains_chain)
  4. Edge: chain → rule's section_node  (relation: fires_rule)
  5. Edge: chain → terminal standards  (relation: requires_standard)

For each existing rule node:
  - Annotate with `fires_in: [project_slugs]`
  - Annotate with `skipped_in: [project_slugs]`
  - Annotate with `chains: [chain_node_ids]`

For each project's skipped rules:
  Generate skip_trace.json showing which trigger predicates failed.

Outputs:
  graphify-out/graph.json        ← augmented in place (backup at .before-plancheck)
  plan-check/.skip-traces/<slug>.json  ← per-project skip trace
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from networkx.readwrite import json_graph


PLAN_DIR = Path(__file__).parent
GRAPH_PATH = PLAN_DIR.parent / 'graphify-out' / 'graph.json'
SKIP_DIR = PLAN_DIR / '.skip-traces'


def slugify(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def normalize_pred(p: str) -> str:
    s = p.lower().strip()
    s = re.sub(r'[\s\-]+', '_', s)
    s = re.sub(r'_+', '_', s)
    return s


def collect_rule_predicates(applies_when):
    """Recursively collect every atomic predicate (with logical context) referenced in applies_when."""
    out = []

    def walk(c):
        if not isinstance(c, dict):
            return
        p = c.get('predicate')
        if p in ('any_of', 'all_of', 'not'):
            for child in (c.get('of') or c.get('clauses') or []):
                walk(child)
        elif p:
            out.append(p)

    for c in applies_when or []:
        walk(c)
    return out


def trace_skip(rule, expanded_facts):
    """Return a structured 'why this rule was skipped' explanation."""
    aw = rule.get('applies_when') or []
    if not aw:
        return {'reason': 'no_applies_when', 'detail': 'rule has no triggers (would always fire — likely engine bug)'}

    asserted = expanded_facts
    referenced = collect_rule_predicates(aw)
    matched = [p for p in referenced if normalize_pred(p) in asserted]
    unmatched = [p for p in referenced if normalize_pred(p) not in asserted]

    return {
        'cite': rule.get('cite'),
        'matched_predicates': matched,
        'unmatched_predicates': unmatched,
        'first_unmatched': unmatched[0] if unmatched else None,
        'reason': 'predicates_unmet' if unmatched else 'composite_logic_failed',
    }


def build_augmentation(projects):
    """Given list of {slug, facts, vios, chains} per project, build node + edge lists.

    Returns:
      new_nodes:   list of dicts ready for graph.json
      new_edges:   list of dicts ready for graph.json links
      rule_annotations: {rule_section_node: {fires_in: [], skipped_in: [], chains: []}}
    """
    new_nodes = []
    new_edges = []
    rule_anno = defaultdict(lambda: {'fires_in': [], 'skipped_in': [], 'chains': []})

    for proj in projects:
        slug = proj['slug']
        facts = proj['facts']
        vios = proj['vios']
        chains = proj['chains']
        rules_by_id = proj['rules_by_id']

        project_addr = facts.get('project', {}).get('address', slug)
        project_node_id = f'plancheck_project_{slug}'

        # Project node
        new_nodes.append({
            'id': project_node_id,
            'label': f'PROJECT: {project_addr}',
            'file_type': 'document',
            'source_file': '',
            'kind': 'plancheck_project',
            'project_slug': slug,
            'sdc': facts.get('project', {}).get('seismic_design_category'),
            'fhsz': facts.get('project', {}).get('fire_hazard_severity_zone'),
            'rules_fired': len(vios.get('fires', [])),
            'chains_count': len(chains.get('chains', [])),
        })

        for c in chains.get('chains', []):
            head = c['head']
            chain_id = f'plancheck_chain_{slug}_{re.sub(r"[^a-z0-9]+","_",head["cite"].lower())}'
            chain_label = f'CHAIN [{slug[:14]}]: {head["cite"]} — {head["title"][:50]}'
            new_nodes.append({
                'id': chain_id,
                'label': chain_label,
                'file_type': 'document',
                'source_file': '',
                'kind': 'plancheck_chain',
                'project_slug': slug,
                'head_cite': head['cite'],
                'head_title': head['title'],
                'rule_count': len(c['rules']),
                'cross_pack': c.get('cross_pack', False),
                'rule_packs_spanned': c.get('rule_packs_spanned', []),
            })

            # project → chain
            new_edges.append({
                'source': project_node_id,
                'target': chain_id,
                'relation': 'contains_chain',
                'confidence': 'EXTRACTED',
                'confidence_score': 1.0,
                'weight': 1.0,
            })

            # chain → each rule's section_node
            for r in c['rules']:
                full_rule = rules_by_id.get(r['rule_id'])
                if not full_rule:
                    continue
                sn = full_rule.get('section_node')
                if sn:
                    new_edges.append({
                        'source': chain_id,
                        'target': sn,
                        'relation': 'fires_rule',
                        'confidence': 'EXTRACTED',
                        'confidence_score': 1.0,
                        'weight': 1.0,
                        'cite': full_rule.get('cite'),
                    })
                    rule_anno[sn]['fires_in'].append(slug)
                    rule_anno[sn]['chains'].append(chain_id)

            # chain → terminal standards
            for std in c.get('terminal_standards', []):
                new_edges.append({
                    'source': chain_id,
                    'target': std,
                    'relation': 'requires_standard',
                    'confidence': 'EXTRACTED',
                    'confidence_score': 1.0,
                    'weight': 1.0,
                })

        # Tag rules that did NOT fire (for completeness)
        fired_ids = {v['rule_id'] for v in vios.get('fires', [])}
        for rid, full_rule in rules_by_id.items():
            if rid in fired_ids:
                continue
            sn = full_rule.get('section_node')
            if sn and slug not in rule_anno[sn]['skipped_in']:
                rule_anno[sn]['skipped_in'].append(slug)

    return new_nodes, new_edges, dict(rule_anno)


def main():
    # Load existing graph
    data = json.loads(GRAPH_PATH.read_text())
    G = json_graph.node_link_graph(data, edges='links')
    existing_ids = set(G.nodes())

    # Load all rules
    rules_doc = json.loads((PLAN_DIR / 'all_rules.json').read_text())
    rules_by_id = {r['id']: r for r in rules_doc['rules']}

    # Locate projects from sample-facts/
    sample_dir = PLAN_DIR / 'sample-facts'
    projects = []
    for facts_path in sorted(sample_dir.glob('*.expanded.json')):
        slug = slugify(facts_path.stem.replace('.expanded', ''))[:30]
        # Find matching violations + chains files
        vios_candidates = list(sample_dir.glob('*violations.json'))
        # Heuristic: match by slug fragment
        vios_path = None
        chains_path = None
        if 'sfr-truckee' in facts_path.stem:
            vios_path = sample_dir / 'full-violations.json'
            chains_path = sample_dir / 'full-chains.json'
            slug = '12345-ridge-road-truckee-ca'
        elif 'adu-la' in facts_path.stem:
            vios_path = sample_dir / 'adu-violations.json'
            chains_path = sample_dir / 'adu-chains.json'
            slug = '1234-hyperion-ave-los-angeles'
        if not vios_path or not vios_path.exists():
            continue
        projects.append({
            'slug': slug,
            'facts': json.loads(facts_path.read_text()),
            'vios': json.loads(vios_path.read_text()),
            'chains': json.loads(chains_path.read_text()),
            'rules_by_id': rules_by_id,
        })

    print(f'Found {len(projects)} project fact sets:')
    for p in projects:
        print(f'  {p["slug"]}: {len(p["vios"].get("fires", []))} fires, {len(p["chains"].get("chains", []))} chains')

    # Build augmentation
    new_nodes, new_edges, rule_anno = build_augmentation(projects)
    print(f'\nAugmentation: +{len(new_nodes)} nodes, +{len(new_edges)} edges, '
          f'annotated {len(rule_anno)} existing rule nodes')

    # Backup
    Path(str(GRAPH_PATH) + '.before-plancheck').write_text(GRAPH_PATH.read_text())

    # Add to graph
    skipped_dupe_nodes = 0
    for n in new_nodes:
        if n['id'] in existing_ids:
            skipped_dupe_nodes += 1
            continue
        attrs = {k: v for k, v in n.items() if k != 'id'}
        G.add_node(n['id'], **attrs)
        existing_ids.add(n['id'])

    skipped_dupe_edges = 0
    for e in new_edges:
        s, t = e['source'], e['target']
        if s not in G or t not in G:
            skipped_dupe_edges += 1
            continue
        if G.has_edge(s, t):
            skipped_dupe_edges += 1
            continue
        attrs = {k: v for k, v in e.items() if k not in ('source', 'target')}
        G.add_edge(s, t, **attrs)

    # Annotate existing rule nodes
    for sn, anno in rule_anno.items():
        if sn in G:
            for k, v in anno.items():
                G.nodes[sn][f'plancheck_{k}'] = sorted(set(v))

    # Save augmented graph
    out = {
        'directed': data.get('directed', False),
        'multigraph': data.get('multigraph', False),
        'graph': data.get('graph', {}),
        'nodes': [{'id': n, **d} for n, d in G.nodes(data=True)],
        'links': [{'source': u, 'target': v, **d} for u, v, d in G.edges(data=True)],
    }
    GRAPH_PATH.write_text(json.dumps(out, indent=2))
    print(f'Augmented graph saved. Now: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges')

    # Generate skip traces
    SKIP_DIR.mkdir(exist_ok=True)
    for p in projects:
        slug = p['slug']
        expanded_facts = set(normalize_pred(f) for f in p['facts'].get('predicates', []))
        fired_ids = {v['rule_id'] for v in p['vios'].get('fires', [])}
        skipped_traces = []
        for rid, rule in rules_by_id.items():
            if rid in fired_ids:
                continue
            t = trace_skip(rule, expanded_facts)
            t['rule_id'] = rid
            skipped_traces.append(t)
        # Aggregate: which predicates were the most common cause of skips?
        unmet_counter = defaultdict(int)
        for t in skipped_traces:
            for u in (t.get('unmatched_predicates') or [])[:1]:  # only first unmet
                unmet_counter[u] += 1
        top_unmet = sorted(unmet_counter.items(), key=lambda x: -x[1])[:20]

        out_doc = {
            'project_slug': slug,
            'skipped_count': len(skipped_traces),
            'top_unmet_predicates': [{'predicate': k, 'blocks_n_rules': v} for k, v in top_unmet],
            'traces': skipped_traces,
        }
        (SKIP_DIR / f'{slug}.json').write_text(json.dumps(out_doc, indent=2))
        print(f'\n  Skip trace [{slug}]: {len(skipped_traces)} skipped rules')
        print(f'    Top blocking predicates:')
        for pred, n in top_unmet[:8]:
            print(f'      {n:>3}x  {pred}')


if __name__ == '__main__':
    main()
