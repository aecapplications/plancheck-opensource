"""Per-book extraction context threaded through the extraction passes.

Classification is shared across books (one sheet index per job, written at
the job top level); everything downstream — text pass, vision pass,
reconciliation — is book-specific and gets its inputs (prompts, vocabulary
via book id) and output locations from this context. Until the multi-book
job layout lands (Phase 4), book_dir == job_dir.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from .. import books
from . import prompts as prompts_pkg


@dataclass(frozen=True)
class ExtractionContext:
    book: books.Book
    job_dir: Path      # shared artifacts: upload.pdf, pages/, classification.json
    book_dir: Path     # this book's artifacts: candidates, facts, usage, ...
    prompts: ModuleType

    @property
    def pages_dir(self) -> Path:
        return self.job_dir / "pages"

    @property
    def usage_dir(self) -> Path:
        """Directory whose usage.jsonl receives this book's LLM call usage."""
        return self.book_dir


def make(book: books.Book, job_dir: Path, book_dir: Path | None = None) -> ExtractionContext:
    return ExtractionContext(book=book, job_dir=job_dir,
                             book_dir=book_dir or job_dir,
                             prompts=prompts_pkg.get(book.prompts_module))
