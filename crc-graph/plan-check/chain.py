"""
Cross-pack rule chain traversal.

Reads:
  all_rules.json    - merged rule corpus
  violations.json   - engine output (fired rules with cite chain)
  graph.json        - knowledge graph (for resolving section_node → rule lookups)

Writes:
  chained_violations.json - rules grouped into compliance chains, deduplicated evidence

Method:
  1. Build rule_by_section: {section_node → rule_id} for fast lookup
  2. Build dependency DiGraph: each rule node, edge rule_a → rule_b if rule_a's
     depends_on contains rule_b's section_node
  3. Restrict to subgraph induced by FIRED rules
  4. Find weakly-connected components — each is one chain
  5. For each chain:
       a. Pick head rule (most specific applies_when, breaking ties by cite depth)
       b. BFS from head along dependency edges, recording depth + path
       c. Collect terminal standards (depends_on entries that aren't rules — std_*)
       d. Deduplicate evidence_required across the chain
       e. Union the matched_conditions across the chain
"""

import json
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import networkx as nx
from networkx.readwrite import json_graph


PLAN_DIR = Path(__file__).parent
GRAPH_PATH = PLAN_DIR.parent / 'graphify-out' / 'graph.json'


# ===== fuzzy depends_on resolution =====

def _section_core(s: str) -> str:
    """Strip prefixes/suffixes for fuzzy comparison.

    section_r301_1_3_engineered_design → r301_1_3
    """
    if not s:
        return ''
    s = s.lower()
    # Strip leading section_/std_/table_/figure_
    for p in ('section_', 'std_', 'table_', 'figure_'):
        if s.startswith(p):
            s = s[len(p):]
            break
    # Drop trailing semantic qualifier (the part after the last code-numeric token)
    # Match a code-style prefix: r302_7 or au_106_11
    m = re.match(r'^([a-z]+_?\d+(?:_\d+)*)', s)
    if m:
        return m.group(1)
    return s


def _is_parent_of(child_core: str, parent_core: str) -> bool:
    """child_core starts with parent_core followed by '_' or =="""
    if child_core == parent_core:
        return True
    return child_core.startswith(parent_core + '_')


def fuzzy_resolve_dep(dep: str, by_section: dict, by_cite: dict) -> list[str]:
    """Return rule_ids that this depends_on entry might reasonably refer to.

    Layered resolution:
      1) exact match in by_section or by_cite
      2) section_core(dep) matches section_core of another rule's section_node
      3) parent-of relationship: dep is a parent of some rule's section_node
      4) child-of relationship: dep is a child of some rule's section_node
    """
    # Layer 1
    if dep in by_section:
        return list(by_section[dep])
    if dep in by_cite:
        return list(by_cite[dep])

    dep_core = _section_core(dep)
    if not dep_core:
        return []

    # Layer 2: equal cores
    matches = []
    for sn, rids in by_section.items():
        sn_core = _section_core(sn)
        if sn_core == dep_core:
            matches.extend(rids)
    if matches:
        return matches

    # Layer 3+4: parent/child relations — but constrain so a parent dep doesn't
    # explode into every descendant. Prefer shorter (parent) matches.
    parents = []
    children = []
    for sn, rids in by_section.items():
        sn_core = _section_core(sn)
        if not sn_core:
            continue
        if _is_parent_of(sn_core, dep_core):
            children.append((sn_core, sn, rids))  # dep is parent, sn is child
        elif _is_parent_of(dep_core, sn_core):
            parents.append((sn_core, sn, rids))   # dep is child, sn is parent

    # Prefer parent (the more general rule the dep is part of)
    if parents:
        parents.sort(key=lambda x: len(x[0]), reverse=True)  # closest parent
        closest_core = parents[0][0]
        return [rid for core, _, rids in parents if core == closest_core for rid in rids]

    # Otherwise return immediate children only (one level deeper)
    if children:
        children.sort(key=lambda x: len(x[0]))  # closest children first
        # Only take same-distance children
        closest_core_len = len(children[0][0])
        return [rid for core, _, rids in children if len(core) == closest_core_len for rid in rids]

    return []


# ===== graph-edge augmentation =====

def load_graph_section_edges(min_confidence: float = 0.0) -> nx.DiGraph:
    """Load graphify graph's edges between sections (for chain augmentation).

    min_confidence — drop edges with confidence_score below this threshold.
    Default 0.0 keeps every edge; 1.0 keeps only EXTRACTED (verbatim text match).
    """
    if not GRAPH_PATH.exists():
        return nx.DiGraph()
    data = json.loads(GRAPH_PATH.read_text())
    G = json_graph.node_link_graph(data, edges='links')
    keep_relations = {'requires', 'references', 'amends', 'applies_to', 'cites',
                      'alternative_to', 'alternatives_to', 'exempts', 'rationale_for',
                      'part_of', 'defines'}
    out = nx.DiGraph()
    for u, v, d in G.edges(data=True):
        rel = d.get('relation', '')
        if rel not in keep_relations:
            continue
        cs = d.get('confidence_score')
        # Treat missing/null confidence as 1.0 (extracted with no explicit score)
        cs = 1.0 if cs is None else cs
        if cs < min_confidence:
            continue
        out.add_edge(u, v, **d)
    return out


def cite_depth(cite: str) -> int:
    """How specific is this cite? R324.4.2 > R324.4 > R324."""
    if not cite:
        return 0
    return cite.count('.') + 1


def predicate_count(applies_when) -> int:
    """Specificity proxy: how many distinct predicate clauses?"""
    n = 0
    for c in (applies_when or []):
        if not isinstance(c, dict):
            continue
        p = c.get('predicate')
        if p in ('any_of', 'all_of', 'not'):
            n += len(c.get('of') or c.get('clauses') or [])
        elif p:
            n += 1
    return n


def is_terminal(node_id: str) -> bool:
    """True if this is a leaf citation (standard, table, figure)."""
    s = (node_id or '').lower()
    return s.startswith('std_') or s.startswith('table_') or s.startswith('figure_') or s.startswith('chapter_')


def build_chain_graph(rules: list[dict], use_fuzzy: bool = True, use_graph_edges: bool = True,
                       min_graph_confidence: float = 0.0) -> tuple[nx.DiGraph, dict]:
    """Construct rule-to-rule dependency graph with optional fuzzy + graph-edge augmentation.

    min_graph_confidence filters which graphify-graph edges are added as chain edges.
    """
    by_section = defaultdict(list)
    by_cite = defaultdict(list)
    for r in rules:
        if r.get('section_node'):
            by_section[r['section_node']].append(r['id'])
        if r.get('cite'):
            by_cite[r['cite']].append(r['id'])

    G = nx.DiGraph()
    edge_stats = Counter()  # noqa: F821 - using local Counter via collections
    for r in rules:
        G.add_node(r['id'], **{k: r.get(k) for k in
                               ('cite', 'title', 'severity', 'jurisdiction',
                                'verbatim', 'requires', 'evidence_required',
                                'depends_on', 'section_node', '_rule_pack', '_community_id',
                                'applies_when')})
        for dep in r.get('depends_on') or []:
            targets = by_section.get(dep, []) + by_cite.get(dep, [])
            kind = 'exact'
            if not targets and use_fuzzy:
                targets = fuzzy_resolve_dep(dep, by_section, by_cite)
                if targets:
                    kind = 'fuzzy'
            for tgt in sorted(set(targets)):
                if tgt != r['id'] and not G.has_edge(r['id'], tgt):
                    G.add_edge(r['id'], tgt, via=dep, kind=f'rule_dep_{kind}')
                    edge_stats[kind] += 1

    # Augment with graphify graph's section→section edges
    if use_graph_edges:
        section_graph = load_graph_section_edges(min_confidence=min_graph_confidence)
        for u, v, d in section_graph.edges(data=True):
            u_rules = by_section.get(u, [])
            v_rules = by_section.get(v, [])
            for ru in u_rules:
                for rv in v_rules:
                    if ru != rv and not G.has_edge(ru, rv):
                        G.add_edge(ru, rv, via=f'graph:{d.get("relation","")}',
                                   kind='graph_edge', confidence=d.get('confidence'))
                        edge_stats['graph'] += 1

    # Mark rules with identical cite or section_node as duplicates
    for sn, rids in by_section.items():
        if len(rids) > 1:
            anchor = rids[0]
            for other in rids[1:]:
                if not G.has_edge(anchor, other):
                    G.add_edge(anchor, other, via=f'shared_section_node:{sn}', kind='duplicate')
                    edge_stats['duplicate'] += 1
                if not G.has_edge(other, anchor):
                    G.add_edge(other, anchor, via=f'shared_section_node:{sn}', kind='duplicate')
                    edge_stats['duplicate'] += 1
    for cite, rids in by_cite.items():
        if len(rids) > 1:
            anchor = rids[0]
            for other in rids[1:]:
                if not G.has_edge(anchor, other):
                    G.add_edge(anchor, other, via=f'shared_cite:{cite}', kind='duplicate')
                    edge_stats['duplicate'] += 1
                if not G.has_edge(other, anchor):
                    G.add_edge(other, anchor, via=f'shared_cite:{cite}', kind='duplicate')

    G.graph['edge_stats'] = dict(edge_stats)
    return G, dict(by_section)


def decompose_subclusters(G: nx.DiGraph, component: set[str]) -> list[dict]:
    """Run Louvain on the chain's internal edges to find natural sub-clusters.

    Returns a list of {head_rule_id, head_cite, rule_ids, packs} per sub-cluster.
    Used when a chain is larger than the decompose threshold — gives a 2-level view.
    """
    if len(component) < 4:
        return []
    sub = G.subgraph(component).to_undirected()
    if sub.number_of_edges() == 0:
        return []
    try:
        from networkx.algorithms.community import louvain_communities
        communities = louvain_communities(sub, seed=42)
    except ImportError:
        from networkx.algorithms.community import greedy_modularity_communities
        communities = list(greedy_modularity_communities(sub))
    if len(communities) < 2:
        return []
    out = []
    for comm in sorted(communities, key=lambda c: (-len(c), min(c))):
        # Pick sub-cluster head: most predicates, then highest cite depth
        def spec(rid):
            d = G.nodes[rid]
            return (predicate_count(d.get('applies_when')), cite_depth(d.get('cite', '')))
        head = max(sorted(comm), key=spec)
        head_data = G.nodes[head]
        # Plain-language label from a few member cites
        sample_cites = sorted({G.nodes[n].get('cite', n) for n in comm})[:5]
        packs = sorted({G.nodes[n].get('_rule_pack') for n in comm if G.nodes[n].get('_rule_pack')})
        out.append({
            'head_rule_id': head,
            'head_cite': head_data.get('cite'),
            'head_title': head_data.get('title'),
            'rule_count': len(comm),
            'rule_ids': sorted(comm),
            'cites': sample_cites,
            'packs': packs,
        })
    return out


def chain_from_component(G: nx.DiGraph, component: set[str], decompose_threshold: int = 15) -> dict:
    """Build a chain summary for one connected component of fired rules."""
    # Pick head: rule with most applies_when predicates, then highest cite depth
    def specificity(rid):
        d = G.nodes[rid]
        return (predicate_count(d.get('applies_when')), cite_depth(d.get('cite', '')))
    # max() keeps the first maximal element, so sorting first makes specificity
    # ties resolve to the lowest rule id instead of process-dependent set order.
    head = max(sorted(component), key=specificity)

    # BFS from head along directed edges (head → deps)
    visited = {head: 0}
    queue = deque([head])
    edges_in_chain = []
    while queue:
        u = queue.popleft()
        for v in sorted(G.successors(u)):
            if v in component and v not in visited:
                visited[v] = visited[u] + 1
                edges_in_chain.append((u, v, G.edges[u, v].get('via')))
                queue.append(v)
    # Pick up rules reachable backwards too (rules that depend on head)
    for u in component:
        if u not in visited:
            visited[u] = -1  # ancestor of head, depth -1 means "depends on head"

    # Build linear path: depth from head, ties by rule id
    path = sorted(component, key=lambda r: (visited.get(r, 99), r))

    # Collect terminal standards across the chain
    terminals = set()
    for rid in path:
        for dep in G.nodes[rid].get('depends_on') or []:
            if is_terminal(dep):
                terminals.add(dep)

    # Deduplicate evidence in chain order, so first_required_by is stable
    evidence_seen = set()
    evidence = []
    for rid in path:
        for ev in G.nodes[rid].get('evidence_required') or []:
            key = re.sub(r'\W+', ' ', ev.lower()).strip()
            if key not in evidence_seen:
                evidence_seen.add(key)
                evidence.append({'item': ev, 'first_required_by': G.nodes[rid].get('cite')})
    chain = []
    for rid in path:
        d = G.nodes[rid]
        chain.append({
            'rule_id': rid,
            'cite': d.get('cite'),
            'title': d.get('title'),
            'rule_pack': d.get('_rule_pack'),
            'community_id': d.get('_community_id'),
            'severity': d.get('severity'),
            'jurisdiction': d.get('jurisdiction'),
            'depth_from_head': visited.get(rid, 0),
            'verbatim': d.get('verbatim'),
            'predicate_count': predicate_count(d.get('applies_when')),
        })

    head_data = G.nodes[head]
    chain_dict = {
        'chain_id': 'chain_' + head.replace('rule_', ''),
        'head': {
            'rule_id': head,
            'cite': head_data.get('cite'),
            'title': head_data.get('title'),
            'rule_pack': head_data.get('_rule_pack'),
            'predicate_count': predicate_count(head_data.get('applies_when')),
        },
        'rules': chain,
        'terminal_standards': sorted(terminals),
        'evidence_required': evidence,
        'edges': [{'from': u, 'to': v, 'via': via} for u, v, via in edges_in_chain],
        'rule_packs_spanned': sorted(set(r['rule_pack'] for r in chain if r['rule_pack'])),
        'cross_pack': len(set(r['rule_pack'] for r in chain if r['rule_pack'])) > 1,
    }
    # If the chain is large, decompose into sub-clusters for actionable review
    if len(chain) >= decompose_threshold:
        chain_dict['subclusters'] = decompose_subclusters(G, component)
    return chain_dict


def chain_violations(rules_doc: dict, violations_doc: dict, min_graph_confidence: float = 0.0) -> dict:
    rules = rules_doc.get('rules', [])
    rule_by_id = {r['id']: r for r in rules}
    fired_ids = {v['rule_id'] for v in violations_doc.get('fires', [])}

    G, rule_by_section = build_chain_graph(rules, min_graph_confidence=min_graph_confidence)

    # Subgraph induced by fired rules
    fired_subgraph = G.subgraph(fired_ids).copy()

    # Connected components (treating directed edges as undirected for grouping)
    components = list(nx.weakly_connected_components(fired_subgraph))
    # Singletons (fired rules with no dependency to other fired rules) are components of size 1

    chains = [chain_from_component(G, comp) for comp in components]
    # Sort by chain size desc, then by head specificity, then by id for stability
    chains.sort(key=lambda c: (-len(c['rules']), -c['head'].get('predicate_count', 0),
                               c['chain_id']))

    cross_pack = sum(1 for c in chains if c['cross_pack'])

    return {
        'project': violations_doc.get('project', {}),
        'rule_pack': violations_doc.get('rule_pack'),
        'summary': {
            'rules_fired': len(fired_ids),
            'chains': len(chains),
            'compression_ratio': round(len(fired_ids) / max(len(chains), 1), 2),
            'cross_pack_chains': cross_pack,
            'multi_rule_chains': sum(1 for c in chains if len(c['rules']) > 1),
            'singleton_chains': sum(1 for c in chains if len(c['rules']) == 1),
            'edge_stats': G.graph.get('edge_stats', {}),
        },
        'chains': chains,
    }


def main(argv):
    if len(argv) < 4:
        print('usage: chain.py <all_rules.json> <violations.json> <output.json>', file=sys.stderr)
        sys.exit(1)
    rules = json.loads(Path(argv[1]).read_text())
    vios = json.loads(Path(argv[2]).read_text())
    out = chain_violations(rules, vios)
    Path(argv[3]).write_text(json.dumps(out, indent=2))

    s = out['summary']
    print(f'Rules fired:            {s["rules_fired"]}')
    print(f'Chains:                 {s["chains"]}')
    print(f'Multi-rule chains:      {s["multi_rule_chains"]}')
    print(f'Singleton chains:       {s["singleton_chains"]}')
    print(f'Cross-pack chains:      {s["cross_pack_chains"]}')
    print(f'Compression ratio:      {s["compression_ratio"]:.2f}x')
    print()

    print('Top 10 chains by size:')
    for i, c in enumerate(out['chains'][:10], 1):
        head = c['head']
        spans = ', '.join(c['rule_packs_spanned'][:3])
        if len(c['rule_packs_spanned']) > 3:
            spans += f' +{len(c["rule_packs_spanned"])-3}'
        marker = '🔗' if c['cross_pack'] else '  '
        print(f'  {i:>2}. {marker} {len(c["rules"]):>2} rules / {len(c["terminal_standards"]):>2} stds  '
              f'head={head["cite"]:>10}  spans=[{spans}]')


if __name__ == '__main__':
    main(sys.argv)
