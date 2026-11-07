"""Shim — the dispatch generator moved to tools/make_dispatch.py.

Equivalent invocation (from the repo root):
    python tools/make_dispatch.py --graph-dir cec-graph [--min-nodes N]

Kept so existing docs/muscle memory pointing here still work. Regenerating
through the shared tool is byte-identical to this script's original output.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from make_dispatch import main  # noqa: E402

if __name__ == "__main__":
    main(["--graph-dir", "cec-graph", *sys.argv[1:]])
