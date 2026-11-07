#!/usr/bin/env python3
"""Remove `verbatim` code-text quotes before anything is published.

Rule extraction quotes each section's load-bearing sentence in a `verbatim`
field — it anchors the model to the source and is handy in local reports —
but it is copyrighted code text and must not be committed to the public
repository. This tool strips it.

    python tools/strip_verbatim.py            # strip in place (whole repo)
    python tools/strip_verbatim.py --check    # exit 1 if any quote remains

Stripping removes every `verbatim` key from JSON files (formatting
preserved) and the matching `> quote` blocks from rendered Markdown reports
(strip JSON and Markdown in the same run — the quotes are matched by text).
`"verbatim": null`, which the engine emits for unquoted rules, carries no
text and is left alone.

In the private full-fidelity repository (where `*-graph/chapters/` is
tracked) in-place stripping is refused: use tools/export_public.py, which
strips a copy.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NON_NULL = re.compile(r'"verbatim":(?!\s*null\b)')
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "jobs", "chapters"}


def _files(root: Path, suffix: str):
    for p in sorted(root.rglob(f"*{suffix}")):
        if p.is_file() and not SKIP_DIRS & set(p.relative_to(root).parts):
            yield p


def drop_key(obj, key: str, found: list[str]):
    """Return obj with `key` removed at every depth; collect removed strings."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k == key:
                if isinstance(v, str):
                    found.append(v)
                continue
            out[k] = drop_key(v, key, found)
        return out
    if isinstance(obj, list):
        return [drop_key(v, key, found) for v in obj]
    return obj


def dump_like(original: str, obj) -> str:
    """Serialize obj matching the original file's json.dumps style."""
    parsed = json.loads(original)
    for indent in (2, 1, 4, None):
        for ascii_ in (True, False):
            text = json.dumps(parsed, indent=indent, ensure_ascii=ascii_)
            if text == original.rstrip("\n"):
                tail = original[len(text):]
                return json.dumps(obj, indent=indent,
                                  ensure_ascii=ascii_) + tail
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def strip_json(root: Path) -> list[str]:
    """Strip non-null `verbatim` values from JSON under root; return quotes."""
    quotes: list[str] = []
    changed = 0
    for p in _files(root, ".json"):
        text = p.read_text()
        if not NON_NULL.search(text):
            continue
        found: list[str] = []
        new = drop_key(json.loads(text), "verbatim", found)
        if found:
            p.write_text(dump_like(text, new))
            quotes.extend(found)
            changed += 1
    print(f"  stripped `verbatim` from {changed} JSON files "
          f"({len(quotes)} quotes)")
    return quotes


def strip_markdown(root: Path, quotes: list[str]) -> None:
    # render_report.render_rule_card emits '\n> {verbatim}\n' as one element of
    # a '\n'-joined list, i.e. '\n\n> {q}\n\n' between neighbours; without it
    # the neighbours are joined by a single '\n'.
    uniq = sorted(set(quotes), key=len, reverse=True)
    changed = 0
    for p in _files(root, ".md"):
        text = p.read_text()
        new = text
        for q in uniq:
            if q in new:
                new = new.replace(f"\n\n> {q}\n\n", "\n")
        if new != text:
            p.write_text(new)
            changed += 1
    print(f"  stripped quote blocks from {changed} Markdown files")


def strip_tree(root: Path) -> None:
    strip_markdown(root, strip_json(root))


def find_verbatim(root: Path) -> list[str]:
    """Relative paths of JSON files still carrying a non-null `verbatim`."""
    return [str(p.relative_to(root)) for p in _files(root, ".json")
            if NON_NULL.search(p.read_text(errors="ignore"))]


def is_private_repo(root: Path) -> bool:
    r = subprocess.run(["git", "ls-files", "--", "*-graph/chapters/*"],
                       cwd=root, capture_output=True, text=True)
    return bool(r.stdout.strip())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--check", action="store_true",
                    help="report files with quotes; exit 1 if any (no edits)")
    args = ap.parse_args()
    root = args.root.resolve()

    if args.check:
        left = find_verbatim(root)
        if left:
            print("non-null `verbatim` quotes found — run "
                  "`python tools/strip_verbatim.py` before committing:",
                  *left, sep="\n  ")
            return 1
        print("no `verbatim` quotes")
        return 0
    if is_private_repo(root):
        raise SystemExit("this is the private full-fidelity repo (chapters/ "
                         "is tracked); refusing to strip in place — use "
                         "tools/export_public.py")
    strip_tree(root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
