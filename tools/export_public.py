#!/usr/bin/env python3
"""Build the public, open-source tree of PlanCheck from this private repo.

    python tools/export_public.py DEST [--python .venv/bin/python]

Starting from the committed HEAD (uncommitted changes are NOT exported
unless --worktree is given):

1. extract HEAD into DEST (which must not exist or be empty);
2. delete ``*-graph/chapters/`` and ignore it in DEST/.gitignore;
3. delete every ``verbatim`` key from JSON files, and the matching
   ``> quote`` blocks from rendered Markdown reports;
4. drop README blocks fenced by ``<!-- private-only -->`` markers;
5. regenerate the parity baseline by running the gate on DEST
   (tools/parity_gate.py --update) and then re-verify it;
6. audit DEST against this repo's chapters (tools/audit_verbatim.py) and
   fail on any publisher license footer, any surviving ``verbatim`` key, or
   any verbatim run longer than --max-run words.

DEST is left as a plain directory (no .git) for review. Nothing is pushed.
"""
from __future__ import annotations

import argparse
import io
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from strip_verbatim import find_verbatim, strip_tree  # noqa: E402
PRIVATE_BLOCK = re.compile(
    r"\n?<!-- private-only -->.*?<!-- /private-only -->\n?", re.S)
IGNORE_BLOCK = """
# Licensed code-book text is never distributed (see README "Code-book text")
*-graph/chapters/
"""


def worktree_tree() -> str:
    """Tree id of the working tree (tracked + untracked, honouring
    .gitignore), built in a throwaway index so the real index is untouched."""
    import os
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        subprocess.run(["git", "add", "-A"], cwd=ROOT, env=env, check=True)
        return subprocess.run(["git", "write-tree"], cwd=ROOT, env=env,
                              capture_output=True, text=True,
                              check=True).stdout.strip()


def extract(dest: Path, treeish: str) -> None:
    archive = subprocess.run(["git", "archive", "--format=tar", treeish],
                             cwd=ROOT, capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(dest, filter="data")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dest", type=Path)
    ap.add_argument("--python", default=sys.executable,
                    help="interpreter with webapp requirements (parity gate)")
    ap.add_argument("--worktree", action="store_true",
                    help="export the working tree instead of HEAD (testing)")
    ap.add_argument("--max-run", type=int, default=30,
                    help="longest verbatim run (words) allowed in any file")
    args = ap.parse_args()
    dest = args.dest.resolve()

    if dest.exists() and any(dest.iterdir()):
        raise SystemExit(f"{dest} exists and is not empty")
    if ROOT in dest.parents or dest == ROOT:
        raise SystemExit("DEST must be outside the private repo")
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                           capture_output=True, text=True).stdout
    if dirty.strip() and not args.worktree:
        print("warning: uncommitted changes are not exported", file=sys.stderr)
    dest.mkdir(parents=True, exist_ok=True)

    treeish = worktree_tree() if args.worktree else "HEAD"
    print(f"1. extracting {'working tree' if args.worktree else 'HEAD'}")
    extract(dest, treeish)

    print("2. removing chapters/")
    for d in dest.glob("*-graph/chapters"):
        shutil.rmtree(d)
    gi = dest / ".gitignore"
    gi.write_text(gi.read_text() + IGNORE_BLOCK)

    print("3. stripping verbatim quotes")
    strip_tree(dest)

    print("4. dropping private-only README blocks")
    for p in dest.rglob("*.md"):
        text = p.read_text()
        if "<!-- private-only -->" in text:
            p.write_text(PRIVATE_BLOCK.sub("\n", text))

    gate = [args.python, str(dest / "tools" / "parity_gate.py"),
            "--root", str(dest), "--python", args.python]
    print("5. regenerating parity baseline on the stripped tree")
    subprocess.run(gate + ["--update"], check=True)
    subprocess.run(gate, check=True)
    for junk in list(dest.rglob("__pycache__")) + [dest / "webapp" / "jobs"]:
        shutil.rmtree(junk, ignore_errors=True)

    print("6. auditing")
    leftover = find_verbatim(dest)
    if leftover:
        print("FAIL: non-null `verbatim` values remain in:", *leftover, sep="\n  ")
        return 1
    audit = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "audit_verbatim.py"),
         "--root", str(dest), "--chapters-root", str(ROOT),
         "--max-run", str(args.max_run), "--top", "15"])
    if audit.returncode:
        print("FAIL: audit found publishable code text (see above)")
        return 1
    print(f"\nexport OK: {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
