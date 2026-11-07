"""Deterministic per-chunk extraction for the 2022 California Electrical Code.

For each chunk file in chapters/, produce graphify-out/chunk_NN.json with:
- Section nodes (e.g., 210.8(A)(1))
- Article header nodes (e.g., "Article 210")
- Table reference nodes
- Defined-term nodes (Article 100 only)
- "references" edges between sections via "see X.Y" / "in accordance with X.Y" patterns
- "contains" edges from article -> section
- Optional similarity hints based on section number proximity
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict

CHAPTERS_DIR = Path("chapters")
OUT_DIR = Path("graphify-out")

# Match section numbers: e.g., 210.8, 250.66, 517.30(C)(1), 110.26(A)
# No trailing \b — closing ")" + space has no word boundary; that breaks matches.
SECTION_RE = re.compile(r"(?<![\d.])(?P<num>\d{2,3}\.\d+(?:\([A-Z0-9]+\))*(?:\(\d+\))*)(?![A-Za-z0-9_.])")

# Article header line: "Article 210 Branch Circuits" or "Article 100 Definitions"
ARTICLE_HDR_RE = re.compile(r"^Article\s+(\d{2,3})\s+([A-Za-z][A-Za-z0-9 ,/&\-:]+?)\s*$", re.MULTILINE)

# Cross-reference markers — broad set of CEC reference phrases
XREF_RE = re.compile(
    r"(?:in accordance with|in compliance with|see|complying with|comply with|conform(?:s|ing)? to|as required (?:in|by)|as specified (?:in|by)|as permitted (?:in|by)|as covered (?:in|by)|as defined in|as described in|as outlined in|as listed in|under|per|pursuant to|installed in accordance with|of Section|of Article)\s+(?:Article\s+|Section\s+|Part\s+[IVX]+\s+of\s+Article\s+)?(?P<num>\d{2,3}(?:\.\d+(?:\([A-Z0-9]+\))*(?:\(\d+\))*)?)\b",
    re.IGNORECASE,
)
# Parenthetical xrefs like "(see 250.122)" or "[see 240.4(D)]"
PAREN_XREF_RE = re.compile(r"[\(\[]see\s+(?P<num>\d{2,3}\.\d+(?:\([A-Z0-9]+\))*(?:\(\d+\))*)\b", re.IGNORECASE)

# Table references: "Table 250.66", "Table 310.15(B)(16)", "Table C.1(A)"
TABLE_RE = re.compile(r"\bTable\s+(?P<id>\d{2,3}\.\d+(?:\([A-Z0-9]+\))*(?:\(\d+\))*|[A-Z]\.\d+(?:\([A-Z0-9]+\))*|\d+(?:\.\d+)?)\b")

# Article 100 defined-term entries are usually "Term." or "Term (qualifier)." at line start
# We'll only mine these from chunk_03 specifically.

# Hyperedge candidates: group sections within the same parent (e.g., all 210.8 children)
def parent_section(num: str) -> str:
    """Return the top-level XX.Y prefix of a section number (drop sub-letters/digits)."""
    m = re.match(r"(\d{2,3}\.\d+)", num)
    return m.group(1) if m else num


def normalize_id(stem: str, entity: str) -> str:
    e = re.sub(r"[^a-zA-Z0-9]+", "_", entity).strip("_").lower()
    return f"{stem}_{e}"


def slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()


def extract_chunk(file_path: Path, chunk_num: int):
    text = file_path.read_text(encoding="utf-8")
    # Strip metadata header (lines starting with "#" before the first blank line)
    lines = text.splitlines()
    body_start = 0
    for i, line in enumerate(lines):
        if not line.startswith("#") and line.strip():
            body_start = i
            break
    body = "\n".join(lines[body_start:])

    stem = file_path.stem  # e.g., "01_article_89_general_code_provisions"
    source_file = f"chapters/{file_path.name}"

    nodes_by_id = {}
    edges = []
    seen_edges = set()

    def add_node(nid, label, source_location=None, kind="section"):
        if nid in nodes_by_id:
            return
        nodes_by_id[nid] = {
            "id": nid,
            "label": label,
            "file_type": "document",
            "source_file": source_file,
            "source_location": source_location,
            "source_url": None,
            "captured_at": None,
            "author": None,
            "contributor": None,
            "kind": kind,  # extra metadata for our use
        }

    def add_edge(src, tgt, relation, confidence, score, source_location=None):
        key = (src, tgt, relation)
        if key in seen_edges or src == tgt:
            return
        seen_edges.add(key)
        edges.append({
            "source": src,
            "target": tgt,
            "relation": relation,
            "confidence": confidence,
            "confidence_score": score,
            "source_file": source_file,
            "source_location": source_location,
            "weight": 1.0,
        })

    # 1. Article header nodes
    article_ids = {}
    for m in ARTICLE_HDR_RE.finditer(body):
        art_num = m.group(1)
        art_title = m.group(2).strip()
        nid = normalize_id(stem, f"article_{art_num}")
        article_ids[art_num] = nid
        add_node(nid, f"Article {art_num} {art_title}", source_location=f"Article {art_num}", kind="article")

    # 2. Section nodes
    section_nodes = {}  # number -> node id
    for m in SECTION_RE.finditer(body):
        num = m.group("num")
        if num.startswith("0"):
            continue
        # Skip section numbers that look like dates or table cells (heuristic: too many parens)
        if num.count("(") > 4:
            continue
        nid = normalize_id(stem, num)
        if num not in section_nodes:
            section_nodes[num] = nid
            add_node(nid, num, source_location=num, kind="section")
            # contains edge from article (matches first 3 digits before dot) to section
            top = num.split(".")[0]
            if top in article_ids:
                add_edge(article_ids[top], nid, "contains", "EXTRACTED", 1.0)

    # 3. Table nodes
    table_nodes = {}
    for m in TABLE_RE.finditer(body):
        tid = m.group("id")
        nid = normalize_id(stem, f"table_{tid}")
        if tid not in table_nodes:
            table_nodes[tid] = nid
            add_node(nid, f"Table {tid}", source_location=f"Table {tid}", kind="table")

    # 4. Cross-reference edges
    # Walk the body keeping track of which section is "current" (to use as edge source)
    section_pattern = re.compile(r"^(\d{2,3}\.\d+(?:\([A-Z0-9]+\))*(?:\(\d+\))*)\b")
    current_section = None
    for line in body.splitlines():
        # Detect a section header at the start of a line
        m = section_pattern.match(line.strip())
        if m and m.group(1) in section_nodes:
            current_section = m.group(1)
        if not current_section:
            continue
        # Combined xref iteration: regular phrase-based AND parenthetical
        for regex in (XREF_RE, PAREN_XREF_RE):
            for xm in regex.finditer(line):
                target_num = xm.group("num")
                if "." not in target_num:
                    if target_num in article_ids:
                        add_edge(section_nodes[current_section], article_ids[target_num], "references", "EXTRACTED", 1.0)
                    continue
                if target_num in section_nodes:
                    add_edge(section_nodes[current_section], section_nodes[target_num], "references", "EXTRACTED", 1.0)
                else:
                    ext_id = f"cec_{slug(target_num)}"
                    add_node(ext_id, target_num, source_location=target_num, kind="external_section")
                    add_edge(section_nodes[current_section], ext_id, "references", "EXTRACTED", 1.0)

    # 5. Article-100 defined terms (only chunk 03)
    if stem.startswith("03_"):
        # Defined terms in Article 100 are headed like "Term Name."
        # Heuristic: lines that match "[Capitalized Phrase]." with no leading section number,
        # followed by a definition paragraph.
        term_re = re.compile(r"^([A-Z][A-Za-z][A-Za-z, \-/\(\)]*?)\.\s+([A-Z])")
        for line in body.splitlines():
            mm = term_re.match(line.strip())
            if not mm:
                continue
            term = mm.group(1).strip()
            # Filter out long lines or junk
            if len(term) < 3 or len(term) > 80:
                continue
            # Reject if it starts with "Article" / "Chapter" / "Part"
            if term.lower().startswith(("article", "chapter", "part", "section", "informational note")):
                continue
            nid = normalize_id(stem, term)
            add_node(nid, term, source_location="Article 100", kind="defined_term")

    # 6. Hyperedges: group sub-sections under their parent (e.g., all 210.8(*) children)
    # Auto-create parent stub if it has 3+ children but isn't itself a recognized section yet.
    parent_groups = defaultdict(list)
    for num, nid in section_nodes.items():
        p = parent_section(num)
        if p != num:
            parent_groups[p].append(nid)
    hyperedges = []
    for p, members in parent_groups.items():
        if len(members) < 3:
            continue
        if p not in section_nodes:
            pid = normalize_id(stem, p)
            section_nodes[p] = pid
            add_node(pid, p, source_location=p, kind="section")
            top = p.split(".")[0]
            if top in article_ids:
                add_edge(article_ids[top], pid, "contains", "EXTRACTED", 1.0)
        # Containment edges parent -> children
        for child in members:
            add_edge(section_nodes[p], child, "contains", "EXTRACTED", 1.0)
        hyperedges.append({
            "id": normalize_id(stem, f"group_{p}"),
            "label": f"All sub-sections under {p}",
            "nodes": [section_nodes[p]] + members,
            "relation": "participate_in",
            "confidence": "EXTRACTED",
            "confidence_score": 1.0,
            "source_file": source_file,
        })
    # Cap hyperedges at 5 per chunk to keep them meaningful
    hyperedges.sort(key=lambda h: -len(h["nodes"]))
    hyperedges = hyperedges[:5]

    # Strip the internal "kind" field from nodes before output (not in graphify schema)
    for n in nodes_by_id.values():
        n.pop("kind", None)

    payload = {
        "nodes": list(nodes_by_id.values()),
        "edges": edges,
        "hyperedges": hyperedges,
        "input_tokens": 0,
        "output_tokens": 0,
    }

    out_path = OUT_DIR / f"chunk_{chunk_num:02d}.json"
    out_path.write_text(json.dumps(payload, indent=2))
    return len(payload["nodes"]), len(payload["edges"]), len(payload["hyperedges"])


def main():
    files = sorted(CHAPTERS_DIR.glob("*.txt"))
    print(f"processing {len(files)} chunks")
    total_n = total_e = total_h = 0
    for f in files:
        chunk_num = int(f.name.split("_")[0])
        n, e, h = extract_chunk(f, chunk_num)
        total_n += n
        total_e += e
        total_h += h
        print(f"  chunk_{chunk_num:02d}: {n:>4} nodes, {e:>5} edges, {h} hyperedges  ({f.name})")
    print(f"\ntotal: {total_n:,} nodes, {total_e:,} edges, {total_h} hyperedges")


if __name__ == "__main__":
    main()
