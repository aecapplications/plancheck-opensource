#!/usr/bin/env python3
"""Report where each code book stands in the add-code-book workflow.

    python .claude/skills/add-code-book/scripts/book_status.py          # all books
    python .claude/skills/add-code-book/scripts/book_status.py cec      # one book
    python .claude/skills/add-code-book/scripts/book_status.py cec --remaining

For each <book>-graph/ directory it checks every workflow artifact on disk and
prints the next step. Read-only; uses only the standard library.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SHARED = ("engine.py", "integrate.py", "normalize_clauses.py",
          "render_report.py")
ADAPTED = ("decompose.py", "chain.py", "fixup_ids.py", "canonicalize.py")


def registry() -> dict[str, dict]:
    """Book entries parsed from webapp/books.py (no import side effects)."""
    src = (ROOT / "webapp" / "books.py").read_text()
    out = {}
    for m in re.finditer(r"Book\((.*?)\)", src, re.S):
        fields = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        if "id" in fields:
            fields["sample_facts_none"] = "sample_facts=None" in m.group(1)
            out[fields["id"]] = fields
    return out


def chapter_refs(gdir: Path) -> set[str]:
    refs = set()
    for p in (gdir / "plan-check" / ".prompts").glob("*.txt"):
        refs.update(re.findall(r"chapters/([^\s`'\"]+)", p.read_text(errors="ignore")))
    return refs


def status(book: str, reg: dict, show_remaining: bool) -> None:
    g = ROOT / f"{book}-graph"
    pc = g / "plan-check"
    lines, next_step = [], None

    def row(ok, label, detail=""):
        lines.append(f"  [{'x' if ok else ' '}] {label}" + (f" — {detail}" if detail else ""))
        return ok

    manifest = g / "chapters.manifest.json"
    have_manifest = row(manifest.is_file(), "1 chapter manifest")
    chapters = sorted(p.name for p in (g / "chapters").glob("[!.]*")) if (g / "chapters").is_dir() else []
    refs = chapter_refs(g)
    missing = sorted(refs - set(chapters))
    row(bool(chapters) and not missing, "1 chapters/ present locally",
        f"{len(chapters)} files" + (f", {len(missing)} referenced files missing" if missing else "")
        if chapters else "absent — rebuild with tools/split_chapters.py build")
    if not have_manifest:
        next_step = next_step or "step 1 (manifest + chapters)"

    graph = g / "graphify-out" / "graph.json"
    nodes = len(json.loads(graph.read_text()).get("nodes", [])) if graph.is_file() else 0
    if not row(graph.is_file(), "2 graph", f"{nodes} nodes" if nodes else ""):
        next_step = next_step or "step 2 (graphify)"

    shared_ok = all((pc / f).is_file() for f in SHARED + ADAPTED)
    drift = []
    donor = ROOT / "cec-graph" / "plan-check"
    for f in SHARED:
        if (pc / f).is_file() and (donor / f).is_file() and (pc / f).read_bytes() != (donor / f).read_bytes():
            drift.append(f)
    if not row(shared_ok and not drift, "3 plan-check scaffold",
               f"shared files differ from cec: {', '.join(drift)}" if drift else
               ("" if shared_ok else "missing " + ", ".join(f for f in SHARED + ADAPTED if not (pc / f).is_file()))):
        next_step = next_step or "step 3 (scaffold plan-check/)"

    prompts = sorted((pc / ".prompts").glob("c*.txt"))
    if not row(bool(prompts), "4 dispatch prompts", f"{len(prompts)} prompts"):
        next_step = next_step or "step 4 (dispatch)"

    packs = {re.match(r"(c\d+)_", p.name).group(1) for p in pc.glob("c[0-9]*_rules.json")}
    remaining = [p.stem for p in prompts if p.stem not in packs]
    row(prompts and not remaining, "5 rule packs extracted",
        f"{len(packs)} of {len(prompts)}" if prompts else "")
    if prompts and remaining:
        next_step = next_step or f"step 5 (extract {len(remaining)} remaining packs)"

    all_rules = pc / "all_rules.json"
    n_rules = len(json.loads(all_rules.read_text()).get("rules", [])) if all_rules.is_file() else 0
    stale = False
    if all_rules.is_file():  # stale if any pack rule is absent from the corpus
        merged = {r.get("id") for r in json.loads(all_rules.read_text()).get("rules", [])}
        stale = any(r.get("id") not in merged
                    for p in pc.glob("c[0-9]*_rules.json")
                    for r in json.loads(p.read_text()).get("rules", []))
    if not row(all_rules.is_file() and (pc / "canonical" / "vocabulary.json").is_file() and not stale,
               "6 integrated corpus",
               (f"{n_rules} rules" + (" — some pack rules missing from all_rules.json; re-run step 6" if stale else ""))
               if all_rules.is_file() else ""):
        if packs:
            next_step = next_step or "step 6 (integrate)"

    decomp = (pc / "predicate_decomposition.json").is_file()
    facts = []  # fact fixtures only: a top-level "predicates" list, not *.expanded.json
    for f in sorted((pc / "sample-facts").glob("*.json")) if (pc / "sample-facts").is_dir() else []:
        try:
            d = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        if not f.name.endswith(".expanded.json") and isinstance(d, dict) and isinstance(d.get("predicates"), list):
            facts.append(f.name)
    if not row(decomp and bool(facts), "7 decomposition + sample facts",
               ("" if decomp else "no predicate_decomposition.json; ") +
               (f"sample facts: {', '.join(facts)}" if facts else "no sample-facts fixture")):
        next_step = next_step or "step 7 (decomposition + sample facts)"

    entry = reg.get(book)
    prompts_mod = ROOT / "webapp" / "extractor" / "prompts" / f"{book}.py"
    ok8 = bool(entry) and prompts_mod.is_file() and entry and not entry["sample_facts_none"]
    if not row(ok8, "8 webapp registration",
               "no Book entry in webapp/books.py" if not entry else
               ("no webapp/extractor/prompts/%s.py" % book if not prompts_mod.is_file() else
                ("sample_facts=None in Book entry" if entry["sample_facts_none"] else ""))):
        next_step = next_step or "step 8 (webapp pickup)"

    available = all_rules.is_file() and (pc / "canonical" / "vocabulary.json").is_file() and decomp
    lines.append(f"  webapp availability: {'AVAILABLE' if available else 'not available'}")
    print(f"{book}  ({g.name}/)")
    print(*lines, sep="\n")
    print(f"  next: {next_step or 'step 9 (verify) / maintenance'}")
    if show_remaining and remaining:
        print("  remaining prompts: " + " ".join(remaining))
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("book", nargs="?")
    ap.add_argument("--remaining", action="store_true",
                    help="list prompts that have no extracted pack yet")
    args = ap.parse_args()
    books = [args.book] if args.book else sorted(
        p.name[:-len("-graph")] for p in ROOT.glob("*-graph") if p.is_dir())
    if args.book and not (ROOT / f"{args.book}-graph").is_dir():
        print(f"no {args.book}-graph/ yet — start at step 1")
        return 0
    reg = registry()
    for b in books:
        status(b, reg, args.remaining)
    return 0


if __name__ == "__main__":
    sys.exit(main())
