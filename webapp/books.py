"""Code-book registry and per-book plan-check module loader.

Each code book (CRC, CEC, CBC, ...) ships its own copies of the plan-check
pipeline scripts under <graph_dir>/plan-check/. The scripts define colliding
top-level module names (engine, decompose, chain, render_report) and differ
in genuinely book-specific ways, so they cannot be merged or imported via
sys.path. load_modules() instead loads each book's copies under unique module
names via importlib; the scripts self-resolve their data paths from
Path(__file__).parent, so decompose.DECOMP_PATH / chain.GRAPH_PATH point at
the owning book's files automatically.

A book is "available" once its rule corpus artifacts exist on disk — rule
extraction sessions can land incrementally and the book activates in the
webapp without a code change.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import ModuleType

from . import config

_PIPELINE_STEMS = ("engine", "decompose", "chain", "render_report")


@dataclass(frozen=True)
class Book:
    id: str
    label: str
    short: str
    graph_dir: str            # repo-relative directory, e.g. "crc-graph"
    prompts_module: str       # extractor prompts module name (Phase 3)
    sample_facts: str | None  # FAKE-mode facts file in plan-check/sample-facts/

    @property
    def plan_check_dir(self) -> Path:
        return config.REPO_ROOT / self.graph_dir / "plan-check"

    @property
    def all_rules_path(self) -> Path:
        return self.plan_check_dir / "all_rules.json"

    @property
    def vocab_path(self) -> Path:
        return self.plan_check_dir / "canonical" / "vocabulary.json"

    @property
    def decomp_path(self) -> Path:
        return self.plan_check_dir / "predicate_decomposition.json"

    @property
    def sample_facts_path(self) -> Path | None:
        if self.sample_facts is None:
            return None
        return self.plan_check_dir / "sample-facts" / self.sample_facts


REGISTRY: dict[str, Book] = {
    b.id: b for b in (
        Book(id="crc", label="California Residential Code", short="CRC",
             graph_dir="crc-graph", prompts_module="crc",
             sample_facts="full-sfr-truckee.json"),
        Book(id="cec", label="California Electrical Code", short="CEC",
             graph_dir="cec-graph", prompts_module="cec",
             sample_facts="commercial-fitout-wireways.json"),
        Book(id="cbc", label="California Building Code", short="CBC",
             graph_dir="cbc-graph", prompts_module="cbc",
             sample_facts=None),
    )
}


def get(book_id: str) -> Book:
    return REGISTRY[book_id]


def available(book: Book) -> bool:
    """A book is usable once integrate.py has produced its rule corpus and a
    predicate decomposition table has been authored."""
    return (book.all_rules_path.is_file()
            and book.vocab_path.is_file()
            and book.decomp_path.is_file())


def rule_count(book: Book) -> int:
    if not book.all_rules_path.is_file():
        return 0
    try:
        doc = json.loads(book.all_rules_path.read_text())
    except (OSError, json.JSONDecodeError):
        return 0
    return len(doc.get("rules", []))


def book_info(book: Book) -> dict:
    return {
        "id": book.id,
        "label": book.label,
        "short": book.short,
        "available": available(book),
        "rule_count": rule_count(book),
    }


@dataclass(frozen=True)
class BookModules:
    engine: ModuleType
    decompose: ModuleType
    chain: ModuleType
    render_report: ModuleType


def _load_module(book: Book, stem: str) -> ModuleType:
    path = book.plan_check_dir / f"{stem}.py"
    name = f"plancheck_{book.id}_{stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=None)
def load_modules(book_id: str) -> BookModules:
    """Load a book's own pipeline scripts under unique module names."""
    book = get(book_id)
    return BookModules(**{stem: _load_module(book, stem)
                          for stem in _PIPELINE_STEMS})
