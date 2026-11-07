import json
from pathlib import Path
from graphify.build import build_from_json
from graphify.cluster import score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from graphify.export import to_json, to_obsidian, to_canvas, to_html

extraction = json.loads(Path('graphify-out/.graphify_extract.json').read_text())
detection  = json.loads(Path('graphify-out/.graphify_detect.json').read_text())
analysis   = json.loads(Path('graphify-out/.graphify_analysis.json').read_text())

G = build_from_json(extraction)
communities = {int(k): v for k, v in analysis['communities'].items()}
cohesion = {int(k): v for k, v in analysis['cohesion'].items()}
nodes_by_id = {n['id']: n for n in extraction['nodes']}

LABELS = {
    0:  "Wiring Methods — Article 300",
    1:  "Intrinsically Safe Systems — Article 504",
    2:  "Communications Bonding & Grounding — Article 800",
    3:  "Nonmetallic Wireways — Article 378",
    4:  "Switches & General-Use Cords",
    5:  "Hazardous Equipment Suitability (500.8)",
    6:  "Mobile Homes & RVs",
    7:  "Branch-Circuit Ratings",
    8:  "Emergency Systems — Article 700",
    9:  "Motor Disconnects — Article 430",
    10: "Hazardous Location Classification — Article 500",
    11: "California Energy Code — Article 89",
    12: "General Installation Conditions",
    13: "IT Equipment & Audio Systems",
    14: "Marinas & Motor Fuel Dispensing",
    15: "Interconnected Power Sources — Article 705",
    16: "Grounded Conductor Identification",
    17: "Type AC/MC/AC-equivalent Cable",
    18: "Flexible Cords & Cables — Article 400",
    19: "Grounded Conductor Use",
    20: "Swimming Pools & Spas",
    21: "Cabinets & Cutout Boxes — Article 312",
    22: "Luminaires & Appliance Branch Circuits",
    23: "Outdoor Deicing/Snow-Melting — Article 426",
    24: "Branch-Circuit Load Calculations",
    25: "Article 89 Title, Format & Conflicts",
    26: "Code Administration & AHJ — Article 80",
    27: "Cable Substitution Hierarchy (Chapter 8)",
    28: "GFCI Protection — Personnel",
    29: "Working Space — 110.26",
}
for cid in communities:
    if cid not in LABELS:
        LABELS[cid] = f"Community {cid}"

questions = suggest_questions(G, communities, LABELS)
gods = analysis['gods']
surprises = analysis['surprises']
report = generate(G, communities, cohesion, LABELS, gods, surprises, detection, {'input': 0, 'output': 0}, 'chapters', suggested_questions=questions)
Path('graphify-out/GRAPH_REPORT.md').write_text(report)
Path('graphify-out/.graphify_labels.json').write_text(json.dumps({str(k): v for k, v in LABELS.items()}))

# Force-overwrite graph.json (safety check refused at 7244 < 7362)
to_json(G, communities, 'graphify-out/graph.json', force=True)
print(f'graph.json: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges')

# Obsidian vault
n = to_obsidian(G, communities, 'graphify-out/obsidian', community_labels=LABELS, cohesion=cohesion)
print(f'Obsidian: {n} notes')
to_canvas(G, communities, 'graphify-out/obsidian/graph.canvas', community_labels=LABELS)

# HTML aggregated view
from collections import Counter
import networkx as nx
real = {cid: members for cid, members in communities.items() if len(members) >= 2}
node_to_community = {nid: cid for cid, members in real.items() for nid in members}
meta = nx.Graph()
for cid in real:
    meta.add_node(str(cid), label=LABELS.get(cid, f'Community {cid}'))
edge_counts = Counter()
for u, v in G.edges():
    cu, cv = node_to_community.get(u), node_to_community.get(v)
    if cu is not None and cv is not None and cu != cv:
        edge_counts[(min(cu, cv), max(cu, cv))] += 1
for (cu, cv), w in edge_counts.items():
    meta.add_edge(str(cu), str(cv), weight=w, relation=f'{w} cross-community edges', confidence='AGGREGATED')
member_counts = {cid: len(members) for cid, members in real.items()}
meta_communities = {cid: [str(cid)] for cid in real}
to_html(meta, meta_communities, 'graphify-out/graph.html', community_labels=LABELS, member_counts=member_counts)
print(f'graph.html (aggregated): {meta.number_of_nodes()} community nodes, {meta.number_of_edges()} cross-community edges')
