import json
from graphify.build import build_from_json
from graphify.export import to_obsidian, to_canvas, to_html
from pathlib import Path

extraction = json.loads(Path('graphify-out/.graphify_extract.json').read_text())
analysis   = json.loads(Path('graphify-out/.graphify_analysis.json').read_text())
labels_raw = json.loads(Path('graphify-out/.graphify_labels.json').read_text())

G = build_from_json(extraction)
communities = {int(k): v for k, v in analysis['communities'].items()}
cohesion = {int(k): v for k, v in analysis['cohesion'].items()}
labels = {int(k): v for k, v in labels_raw.items()}

# Obsidian vault
obsidian_dir = 'graphify-out/obsidian'
n = to_obsidian(G, communities, obsidian_dir, community_labels=labels or None, cohesion=cohesion)
print(f'Obsidian vault: {n} notes in {obsidian_dir}/')

to_canvas(G, communities, f'{obsidian_dir}/graph.canvas', community_labels=labels or None)
print(f'Canvas: {obsidian_dir}/graph.canvas')

# HTML graph
NODE_LIMIT = 5000
if G.number_of_nodes() > NODE_LIMIT:
    from collections import Counter
    print(f'Graph has {G.number_of_nodes()} nodes (above {NODE_LIMIT}). Building aggregated community view...')
    # Only include "real" communities (>= 2 members) — singletons are noise from sparse cross-refs.
    MIN_COMMUNITY_SIZE = 2
    real = {cid: members for cid, members in communities.items() if len(members) >= MIN_COMMUNITY_SIZE}
    print(f'  filtering to {len(real)} communities with >= {MIN_COMMUNITY_SIZE} members (dropped {len(communities) - len(real)} singletons)')
    node_to_community = {nid: cid for cid, members in real.items() for nid in members}
    import networkx as nx_meta
    meta = nx_meta.Graph()
    for cid, members in real.items():
        meta.add_node(str(cid), label=labels.get(cid, f'Community {cid}'))
    edge_counts = Counter()
    for u, v in G.edges():
        cu, cv = node_to_community.get(u), node_to_community.get(v)
        if cu is not None and cv is not None and cu != cv:
            edge_counts[(min(cu, cv), max(cu, cv))] += 1
    for (cu, cv), w in edge_counts.items():
        meta.add_edge(str(cu), str(cv), weight=w, relation=f'{w} cross-community edges', confidence='AGGREGATED')
    if meta.number_of_nodes() > 1:
        meta_communities = {cid: [str(cid)] for cid in real}
        member_counts = {cid: len(members) for cid, members in real.items()}
        to_html(meta, meta_communities, 'graphify-out/graph.html', community_labels=labels or None, member_counts=member_counts)
        print(f'graph.html written (aggregated: {meta.number_of_nodes()} community nodes, {meta.number_of_edges()} cross-community edges)')
    else:
        print('Single community — aggregated view not useful. Skipping graph.html.')
else:
    to_html(G, communities, 'graphify-out/graph.html', community_labels=labels or None)
    print('graph.html written')
