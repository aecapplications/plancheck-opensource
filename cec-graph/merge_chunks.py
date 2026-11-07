"""Merge all chunk_*.json files (deterministic + subagent) into a single extraction.

Normalizes schema variations between deterministic and subagent outputs.
"""

import json
from pathlib import Path

OUT = Path("graphify-out")
files = sorted(OUT.glob("chunk_*.json"))


def norm_node(n):
    if "id" not in n or "label" not in n:
        return None
    return {
        "id": n["id"],
        "label": n["label"],
        "file_type": n.get("file_type", "document"),
        "source_file": n.get("source_file", ""),
        "source_location": n.get("source_location"),
        "source_url": n.get("source_url"),
        "captured_at": n.get("captured_at"),
        "author": n.get("author"),
        "contributor": n.get("contributor"),
    }


def norm_edge(e):
    src = e.get("source") or e.get("src") or e.get("from")
    tgt = e.get("target") or e.get("tgt") or e.get("to")
    if not src or not tgt or src == tgt:
        return None
    rel = e.get("relation") or e.get("type") or e.get("rel") or "related_to"
    conf = e.get("confidence") or "INFERRED"
    score = e.get("confidence_score")
    if score is None:
        score = 1.0 if conf == "EXTRACTED" else 0.7
    return {
        "source": src,
        "target": tgt,
        "relation": rel,
        "confidence": conf,
        "confidence_score": float(score),
        "source_file": e.get("source_file", ""),
        "source_location": e.get("source_location"),
        "weight": float(e.get("weight", 1.0)),
    }


def norm_hyper(h):
    if "nodes" not in h or len(h.get("nodes", [])) < 3:
        return None
    return {
        "id": h.get("id") or f"hyper_{hash(tuple(h['nodes']))}",
        "label": h.get("label", "Group"),
        "nodes": list(h["nodes"]),
        "relation": h.get("relation") or h.get("type") or "participate_in",
        "confidence": h.get("confidence", "EXTRACTED"),
        "confidence_score": float(h.get("confidence_score", 1.0)),
        "source_file": h.get("source_file", ""),
    }


all_nodes = []
all_edges = []
all_hyperedges = []
seen_ids = set()
per_file = []

for f in files:
    try:
        data = json.loads(f.read_text())
    except Exception as ex:
        print(f"  skip {f.name}: parse error {ex}")
        continue
    n_added = e_added = h_added = 0
    for n in data.get("nodes", []):
        nn = norm_node(n)
        if nn and nn["id"] not in seen_ids:
            seen_ids.add(nn["id"])
            all_nodes.append(nn)
            n_added += 1
    for e in data.get("edges", []):
        ne = norm_edge(e)
        if ne:
            all_edges.append(ne)
            e_added += 1
    for h in data.get("hyperedges", []):
        nh = norm_hyper(h)
        if nh:
            all_hyperedges.append(nh)
            h_added += 1
    per_file.append((f.name, n_added, e_added, h_added))

# Cross-chunk reference resolution: cec_<num> stub nodes -> canonical section by label
canonical = {}
for n in all_nodes:
    if not n["id"].startswith("cec_"):
        lbl = n.get("label") or ""
        if lbl and lbl[:1].isdigit() and "." in lbl and lbl not in canonical:
            canonical[lbl] = n["id"]

remap = {}
for n in all_nodes:
    if n["id"].startswith("cec_"):
        lbl = n.get("label") or ""
        if lbl in canonical:
            remap[n["id"]] = canonical[lbl]

remapped = 0
for e in all_edges:
    if e["source"] in remap:
        e["source"] = remap[e["source"]]
        remapped += 1
    if e["target"] in remap:
        e["target"] = remap[e["target"]]
        remapped += 1

all_nodes = [n for n in all_nodes if n["id"] not in remap]
seen_ids = {n["id"] for n in all_nodes}

clean_edges = [e for e in all_edges if e["source"] in seen_ids and e["target"] in seen_ids]
edge_keys = set()
deduped = []
for e in clean_edges:
    k = (e["source"], e["target"], e["relation"])
    if k in edge_keys:
        continue
    edge_keys.add(k)
    deduped.append(e)

clean_hyper = []
for h in all_hyperedges:
    nodes = [remap.get(n, n) for n in h["nodes"]]
    nodes = [n for n in nodes if n in seen_ids]
    if len(nodes) >= 3:
        h["nodes"] = nodes
        clean_hyper.append(h)

merged = {
    "nodes": all_nodes,
    "edges": deduped,
    "hyperedges": clean_hyper,
    "input_tokens": 0,
    "output_tokens": 0,
}
Path("graphify-out/.graphify_extract.json").write_text(json.dumps(merged))

print(f"merged {len(files)} chunk files")
for name, n, e, h in per_file:
    print(f"  {name}: +{n} nodes, +{e} edges, +{h} hyperedges")
print(f"\nfinal: {len(all_nodes):,} nodes, {len(deduped):,} edges, {len(clean_hyper)} hyperedges")
print(f"cross-chunk stubs: {len(remap)} nodes redirected, {remapped} edge endpoints remapped")
