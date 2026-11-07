import json
from graphify.build import build_from_json
from graphify.cluster import score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from pathlib import Path

extraction = json.loads(Path('graphify-out/.graphify_extract.json').read_text())
detection  = json.loads(Path('graphify-out/.graphify_detect.json').read_text())
analysis   = json.loads(Path('graphify-out/.graphify_analysis.json').read_text())

G = build_from_json(extraction)
communities = {int(k): v for k, v in analysis['communities'].items()}
cohesion = {int(k): v for k, v in analysis['cohesion'].items()}
tokens = {'input': 0, 'output': 0}

LABELS = {
    0: "Grounding & Cable Bonding",
    1: "Services & Feeders",
    2: "Equipment Installations & Motors",
    3: "General Installation Requirements",
    4: "Branch-Circuit Ratings",
    5: "Overcurrent & Appliances",
    6: "Conductor Sizing",
    7: "Dwelling Unit Receptacles",
    8: "Grounded Conductor Identification",
    9: "Hazardous Locations & Flex Cords",
    10: "Swimming Pools & Spas",
    11: "Branch-Circuit Load Calculations",
    12: "Overcurrent Protection",
    13: "Conductor Color Coding",
    14: "Services — General",
    15: "Audio & IT Equipment",
    16: "Wiring Method Installation",
    17: "DER & Energy Storage",
    18: "Working Space & Access",
    19: "Non-Metallic Wiring Methods",
    20: "Wiring Methods — General",
    21: "High-Voltage Installations",
    22: "Code Administration & AHJ",
    23: "Intersystem Bonding",
    24: "Outdoor Disconnects",
    25: "Grounding Electrode & EGC",
    26: "EV & Truck Parking",
    27: "RV & Receptacles",
    28: "Boxes & Raceways",
    29: "Underground Wiring",
}
for cid in communities:
    if cid not in LABELS:
        LABELS[cid] = f"Community {cid}"

questions = suggest_questions(G, communities, LABELS)

report = generate(G, communities, cohesion, LABELS, analysis['gods'], analysis['surprises'], detection, tokens, 'chapters', suggested_questions=questions)
Path('graphify-out/GRAPH_REPORT.md').write_text(report)
Path('graphify-out/.graphify_labels.json').write_text(json.dumps({str(k): v for k, v in LABELS.items()}))
named = sum(1 for v in LABELS.values() if not v.startswith('Community '))
print('report regenerated with community labels')
print(f'labeled {named} of {len(LABELS)} communities by name')
