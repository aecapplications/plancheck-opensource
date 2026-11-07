#!/usr/bin/env python3
"""Flag repo files that reproduce long verbatim runs of code-book text.

The extracted chapter text (``*-graph/chapters/``) is copyrighted and kept out
of the public repo. Derived artifacts (rule packs, prompts, graphs, reports)
may cite sections, paraphrase requirements, and quote short phrases, but must
not carry long verbatim passages. This tool measures that.

It builds a set of word n-gram shingles from every chapter file present
locally, then scans the given files (default: all git-tracked files outside
``chapters/``) and reports, per file, the longest verbatim run (in words) and
the share of the file's shingles found in the code text. Watermark/license
footers are flagged separately.

Usage:
    python tools/audit_verbatim.py                    # audit tracked files
    python tools/audit_verbatim.py --max-run 40       # exit 1 if any run > 40
    python tools/audit_verbatim.py path/a.json ...    # audit specific files
    python tools/audit_verbatim.py --root ../export --chapters-root .
                                                      # audit an export tree

Requires the chapters to exist locally (regenerate them from your licensed
PDFs); with no chapters present it can only check for watermarks.
"""
from __future__ import annotations

import argparse
import glob
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
N = 8  # shingle size in words
WORD = re.compile(r"[a-z0-9]+(?:[.'-][a-z0-9]+)*")
WATERMARK = re.compile(
    r"Accessed\sby\s.{0,80}Order\sNumber|pursuant\sto\sLicense\sAgreement\swith|"
    r"ALL\sRIGHTS\sRESERVED", re.I)


def words(text: str) -> list[str]:
    return WORD.findall(text.lower())


def load_shingles(chapters_root: Path) -> set[int]:
    sh: set[int] = set()
    for p in glob.glob(str(chapters_root / "*-graph" / "chapters" / "*.md")):
        w = words(Path(p).read_text(errors="ignore"))
        sh.update(hash(tuple(w[i:i + N])) for i in range(len(w) - N + 1))
    return sh


def tracked_files(root: Path) -> list[Path]:
    if (root / ".git").exists():
        names = subprocess.run(["git", "ls-files"], cwd=root,
                               capture_output=True, text=True,
                               check=True).stdout.split("\n")
    else:  # an export tree: every file
        names = [str(p.relative_to(root)) for p in root.rglob("*")
                 if p.is_file()]
    return [root / f for f in names
            if f and "/chapters/" not in f and not f.endswith(".pdf")]


def audit(path: Path, sh: set[int]) -> tuple[int, float, int]:
    text = path.read_text(errors="ignore")
    wm = len(WATERMARK.findall(text))
    w = words(text)
    hits = [hash(tuple(w[i:i + N])) in sh for i in range(len(w) - N + 1)]
    if not hits:
        return 0, 0.0, wm
    longest = run = 0
    for h in hits:
        run = run + 1 if h else 0
        longest = max(longest, run)
    # a run of k consecutive shingle hits spans k + N - 1 words
    return (longest + N - 1 if longest else 0), sum(hits) / len(hits), wm


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--max-run", type=int, default=None,
                    help="fail if any file has a verbatim run longer than this")
    ap.add_argument("--top", type=int, default=40, help="rows to print")
    ap.add_argument("--root", type=Path, default=ROOT,
                    help="tree to audit (default: this repo)")
    ap.add_argument("--chapters-root", type=Path, default=None,
                    help="tree holding *-graph/chapters/ (default: --root)")
    args = ap.parse_args()
    root = args.root.resolve()

    sh = load_shingles((args.chapters_root or root).resolve())
    if not sh:
        print("warning: no chapter text found; checking watermarks only",
              file=sys.stderr)
    rows = []
    for f in args.files or tracked_files(root):
        try:
            rows.append((f, *audit(f, sh)))
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue
    rows.sort(key=lambda r: (r[3], r[1], r[2]), reverse=True)

    print(f"{'longest':>7} {'overlap':>7} {'wmark':>5}  file")
    for f, longest, frac, wm in rows[:args.top]:
        print(f"{longest:>7} {frac:>6.1%} {wm:>5}  {f.resolve().relative_to(root)}")

    bad = [r for r in rows if r[3] or
           (args.max_run is not None and r[1] > args.max_run)]
    if args.max_run is not None or any(r[3] for r in rows):
        print(f"\n{len(bad)} file(s) over limit (watermark or run > "
              f"{args.max_run})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
