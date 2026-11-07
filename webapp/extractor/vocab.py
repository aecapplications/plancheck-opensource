"""The predicate universe the pipeline can act on, per code book.

This is the book's vocabulary.json (predicates that rules' applies_when
reference) UNION the declared/composite predicates in its
predicate_decomposition.json (which decompose into rule predicates).
Constraining extraction to this set guarantees every emitted predicate either
fires a rule directly or expands into one — anything else would be inert noise.

Both the LLM system block (the names the model may emit) and the reconciliation
validator (the hard allowlist) are built from here so they never drift.

All functions are keyed by book id and cached per book; the default is CRC
until multi-book extraction lands (Phase 3+).
"""
from __future__ import annotations

import json
from functools import lru_cache

from .. import books


def norm(p: str, book_id: str = "crc") -> str:
    return books.load_modules(book_id).decompose.normalize(p)


def _decomp_leaves(spec) -> list[str]:
    out: list[str] = []
    if isinstance(spec, str):
        return [spec]
    if isinstance(spec, dict):
        for k in ("all_of", "any_of"):
            for c in spec.get(k, []) or []:
                out += _decomp_leaves(c)
        if "not" in spec:
            out += _decomp_leaves(spec["not"])
        if "predicate" in spec:
            out.append(spec["predicate"])
    return out


@lru_cache(maxsize=None)
def maps(book_id: str = "crc") -> tuple[set[str], dict[str, str]]:
    """Return (canonical_set, alias_to_canonical) for a book, keys normalized."""
    book = books.get(book_id)
    decompose = books.load_modules(book_id).decompose
    _n = decompose.normalize

    vocab = json.loads(book.vocab_path.read_text())
    canonical: set[str] = set()
    alias_map: dict[str, str] = {}
    for p in vocab["predicates"]:
        c = _n(p["canonical"])
        canonical.add(c)
        for a in p.get("aliases", []) or []:
            alias_map[_n(a)] = c

    # Declared/composite predicates from the decomposition table.
    table = json.loads(decompose.DECOMP_PATH.read_text())
    for grp in table.get("aliases", {}).get("groups", []):
        for g in grp:
            canonical.add(_n(g))
    for key, spec in table.get("compounds", {}).items():
        if key.startswith("_"):
            continue
        canonical.add(_n(key))
        for leaf in _decomp_leaves(spec):
            canonical.add(_n(leaf))
    return canonical, alias_map


def canonicalize(pred: str, book_id: str = "crc") -> str | None:
    """Map a model-emitted predicate to an allowed canonical name, else None."""
    canonical, alias_map = maps(book_id)
    n = norm(pred, book_id)
    if n in canonical:
        return n
    return alias_map.get(n)


@lru_cache(maxsize=None)
def rendered_text(book_id: str = "crc") -> str:
    """The predicate list shown to the model, grouped by category, with the
    declared/composite forms appended so the model can emit either level."""
    book = books.get(book_id)
    _n = books.load_modules(book_id).decompose.normalize

    vocab = json.loads(book.vocab_path.read_text())
    by_cat: dict[str, list[str]] = {}
    rule_level: set[str] = set()
    for p in vocab["predicates"]:
        by_cat.setdefault(p.get("category", "OTHER"), []).append(p["canonical"])
        rule_level.add(_n(p["canonical"]))

    lines: list[str] = []
    for cat in sorted(by_cat):
        lines.append(f"## {cat}")
        lines.extend(sorted(by_cat[cat]))
        lines.append("")

    canonical, _ = maps(book_id)
    declared_only = sorted(canonical - rule_level)
    if declared_only:
        lines.append("## DECLARED / COMPOSITE (expand into the predicates above)")
        lines.extend(declared_only)
        lines.append("")
    return "\n".join(lines)
