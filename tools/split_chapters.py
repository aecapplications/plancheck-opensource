#!/usr/bin/env python3
"""Regenerate a book's chapters/ text from your own copy of the code PDF.

Code-book text is never distributed with PlanCheck. Each book instead ships
``<book>-graph/chapters.manifest.json`` — chapter filenames, titles, and
1-based inclusive PDF page ranges (no code text). This tool rebuilds
``<book>-graph/chapters/`` from it, with the exact filenames the committed
graph and extraction prompts reference.

    # rebuild an existing book's chapters from your PDF
    python tools/split_chapters.py build --book cec --pdf ~/codes/2022_CEC.pdf

    # draft a manifest for a new book from the PDF's bookmarks, then edit it
    python tools/split_chapters.py init --book calgreen --pdf CALGreen.pdf --level 1

    # preflight: does every chapter file the prompts/graph reference exist?
    python tools/split_chapters.py check --book cec

Text is extracted with PyMuPDF (already a webapp requirement). It will not be
byte-identical to the text the graph was originally built from — those
extracts used several converters — but the filenames, page coverage, and
content match, which is what graph building and rule extraction need.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def manifest_path(book: str) -> Path:
    return ROOT / f"{book}-graph" / "chapters.manifest.json"


def load_manifest(book: str) -> dict:
    p = manifest_path(book)
    if not p.is_file():
        raise SystemExit(f"no manifest at {p.relative_to(ROOT)} — create one "
                         f"with `init` (new book) first")
    return json.loads(p.read_text())


def slug(text: str, limit: int = 60) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:limit]


# --------------------------------------------------------------------------- #
def cmd_build(args) -> int:
    import pymupdf

    m = load_manifest(args.book)
    doc = pymupdf.open(args.pdf)
    expected = m["source"].get("page_count")
    if expected and doc.page_count != expected:
        print(f"warning: PDF has {doc.page_count} pages, manifest expects "
              f"{expected} ({m['source']['title']}). A different printing "
              f"will misalign page ranges.", file=sys.stderr)
        if not args.force:
            print("refusing to continue without --force", file=sys.stderr)
            return 1
    out = Path(args.out) if args.out else ROOT / f"{args.book}-graph" / "chapters"
    out.mkdir(parents=True, exist_ok=True)
    written = skipped = 0
    for ch in m["chapters"]:
        dest = out / ch["file"]
        if dest.exists() and not args.overwrite:
            skipped += 1
            continue
        a, z = ch["pages"]
        if not (1 <= a <= z <= doc.page_count):
            raise SystemExit(f"{ch['file']}: pages {a}-{z} outside PDF "
                             f"(1-{doc.page_count})")
        body = "\n".join(doc[i].get_text() for i in range(a - 1, z))
        header = (f"# {ch['title']}\n\n_Source: {m['source']['filename']} "
                  f"pages {a}-{z}_\n\n")
        dest.write_text(header + body)
        written += 1
    print(f"{args.book}: wrote {written} chapter files to {out}"
          + (f" ({skipped} existing kept; --overwrite to replace)"
             if skipped else ""))
    return 0


# --------------------------------------------------------------------------- #
def cmd_init(args) -> int:
    import pymupdf

    p = manifest_path(args.book)
    if p.exists() and not args.force:
        raise SystemExit(f"{p.relative_to(ROOT)} exists (use --force)")
    doc = pymupdf.open(args.pdf)
    toc = [(t, pg) for lvl, t, pg in doc.get_toc() if lvl == args.level]
    if not toc:
        levels = sorted({lvl for lvl, _, _ in doc.get_toc()})
        raise SystemExit(f"no bookmarks at level {args.level} "
                         f"(levels present: {levels or 'none'})")
    chapters = []
    for i, (title, start) in enumerate(toc):
        end = (toc[i + 1][1] - 1) if i + 1 < len(toc) else doc.page_count
        chapters.append({"file": f"{i + 1:02d}_{slug(title)}.md",
                         "title": title, "pages": [start, max(start, end)]})
    m = {"_comment": "Draft from PDF bookmarks — edit before use: drop front "
                     "matter/index entries, split very large chapters (keep "
                     "an NN_ or chNN_ filename prefix; graphify and "
                     "make_dispatch key off it). Pages are 1-based, inclusive.",
         "source": {"title": args.title or Path(args.pdf).stem,
                    "filename": Path(args.pdf).name,
                    "page_count": doc.page_count},
         "chapters": chapters}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {p.relative_to(ROOT)} with {len(chapters)} entries — "
          f"review it, then run `build`")
    return 0


# --------------------------------------------------------------------------- #
def referenced_files(book: str) -> dict[str, set[str]]:
    """chapters/<file> names referenced by the committed prompts and graph."""
    gdir = ROOT / f"{book}-graph"
    refs: dict[str, set[str]] = {}
    pat = re.compile(rf"(?:{re.escape(book)}-graph/)?chapters/([^\s`'\"]+)")
    for p in sorted((gdir / "plan-check" / ".prompts").glob("*.txt")):
        for name in pat.findall(p.read_text(errors="ignore")):
            refs.setdefault(name, set()).add(f"prompt {p.name}")
    graph = gdir / "graphify-out" / "graph.json"
    if graph.is_file():
        for n in json.loads(graph.read_text()).get("nodes", []):
            sf = n.get("source_file") or ""
            if sf.startswith("chapters/"):
                refs.setdefault(sf[len("chapters/"):], set()).add("graph.json")
    return refs


def check_book(book: str, chapters_dir: Path | None = None,
               files: list[str] | None = None) -> list[str]:
    """Return problems (empty if every referenced chapter file exists)."""
    cdir = chapters_dir or ROOT / f"{book}-graph" / "chapters"
    refs = referenced_files(book)
    if files is not None:  # restrict to these referencing sources
        refs = {k: v for k, v in refs.items()
                if any(f"prompt {f}" in v for f in files)}
    missing = sorted(k for k in refs if not (cdir / k).is_file())
    problems = [f"missing {cdir.relative_to(ROOT) if cdir.is_relative_to(ROOT) else cdir}/{k}"
                f" (referenced by {', '.join(sorted(refs[k])[:3])})"
                for k in missing]
    mpath = manifest_path(book)
    if mpath.is_file():
        listed = {c["file"] for c in json.loads(mpath.read_text())["chapters"]}
        problems += [f"{k} is referenced but not in chapters.manifest.json"
                     for k in sorted(set(refs) - listed)]
    return problems


def cmd_check(args) -> int:
    cdir = Path(args.dir).resolve() if args.dir else None
    problems = check_book(args.book, cdir, args.prompt or None)
    refs = referenced_files(args.book)
    if args.prompt:
        refs = {k: v for k, v in refs.items()
                if any(f"prompt {f}" in v for f in args.prompt)}
    n = len(refs)
    if problems:
        print(*problems, sep="\n")
        print(f"\n{args.book}: {len(problems)} problem(s). Regenerate the "
              f"chapters: python tools/split_chapters.py build --book "
              f"{args.book} --pdf <your copy of the code PDF>")
        return 1
    print(f"{args.book}: all {n} referenced chapter files present")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="write chapters/ from the manifest")
    b.add_argument("--book", required=True)
    b.add_argument("--pdf", required=True)
    b.add_argument("--out", help="output dir (default <book>-graph/chapters)")
    b.add_argument("--overwrite", action="store_true")
    b.add_argument("--force", action="store_true",
                   help="proceed even if the PDF page count differs")
    b.set_defaults(func=cmd_build)

    i = sub.add_parser("init", help="draft a manifest from PDF bookmarks")
    i.add_argument("--book", required=True)
    i.add_argument("--pdf", required=True)
    i.add_argument("--level", type=int, default=1,
                   help="bookmark depth that corresponds to chapters")
    i.add_argument("--title", help="human-readable source title")
    i.add_argument("--force", action="store_true")
    i.set_defaults(func=cmd_init)

    c = sub.add_parser("check", help="verify referenced chapter files exist")
    c.add_argument("--book", required=True)
    c.add_argument("--dir", help="chapters dir to check (default the book's)")
    c.add_argument("--prompt", action="append",
                   help="only files referenced by this prompt (e.g. c07.txt)")
    c.set_defaults(func=cmd_check)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
