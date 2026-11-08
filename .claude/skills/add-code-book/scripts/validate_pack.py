#!/usr/bin/env python3
"""Validate freshly extracted rule packs before integrating them.

    python .claude/skills/add-code-book/scripts/validate_pack.py <book>-graph/plan-check/c07_*_rules.json [...]

For each pack it checks that:
  - the file parses as JSON with a non-empty `rules` list;
  - every rule has id, cite, title, section_node, applies_when, jurisdiction,
    and severity;
  - every section_node, depends_on, and tested_per entry (anywhere in the
    rule) is a node id in the book's graphify-out/graph.json;
  - rule ids are unique within the pack.

`verbatim` is optional (public-repo packs are stripped). Exits 1 if any pack
has errors, so it can drive a fix-and-revalidate loop. Read-only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED = ("id", "cite", "title", "section_node", "applies_when",
            "jurisdiction", "severity")


def graph_ids(pack: Path) -> set[str]:
    graph = pack.resolve().parent.parent / "graphify-out" / "graph.json"
    if not graph.is_file():
        raise SystemExit(f"no graph at {graph}")
    return {n["id"] for n in json.loads(graph.read_text())["nodes"]}


def tested_per(obj) -> list[str]:
    """Every string inside any `tested_per` list, at any depth."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "tested_per" and isinstance(v, list):
                out += [x for x in v if isinstance(x, str)]
            else:
                out += tested_per(v)
    elif isinstance(obj, list):
        for v in obj:
            out += tested_per(v)
    return out


def validate(pack: Path, ids: set[str]) -> list[str]:
    try:
        doc = json.loads(pack.read_text())
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"]
    rules = doc.get("rules") if isinstance(doc, dict) else None
    if not rules:
        return ["no `rules` list"]
    errors, seen = [], set()
    for r in rules:
        rid = r.get("id", "?")
        if rid in seen:
            errors.append(f"{rid}: duplicate rule id")
        seen.add(rid)
        errors += [f"{rid}: missing {f}" for f in REQUIRED if not r.get(f)]
        refs = ([("section_node", r["section_node"])] if r.get("section_node") else [])
        refs += [("depends_on", d) for d in r.get("depends_on") or []]
        refs += [("tested_per", t) for t in tested_per(r)]
        errors += [f'{rid}: {kind} "{v}" is not a graph node id'
                   for kind, v in refs if v not in ids]
    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.strip().split("\n\n")[1])
        return 2
    failed = 0
    cache: dict[Path, set[str]] = {}
    for arg in sys.argv[1:]:
        pack = Path(arg)
        gdir = pack.resolve().parent.parent
        ids = cache.setdefault(gdir, graph_ids(pack))
        errors = validate(pack, ids)
        n = len(json.loads(pack.read_text()).get("rules", [])) if not errors or "JSON" not in errors[0] else 0
        print(f"{'OK  ' if not errors else 'FAIL'} {pack.name}: {n} rules, {len(errors)} errors")
        for e in errors[:15]:
            print(f"     {e}")
        if len(errors) > 15:
            print(f"     ... +{len(errors) - 15} more")
        failed += bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
