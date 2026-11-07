"""Extraction passes: PDF -> facts.json (with provenance), per code book.

classify_pass runs once per job (one sheet index serves every selected book).
extract_book_facts runs the book-specific passes (text -> vision -> reconcile)
for one book's ExtractionContext. fake_facts synthesizes a book's facts from
its sample file (EXTRACTOR_FAKE mode) so the web flow can be exercised for
free.
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import books, config
from ..jobs import store


async def classify_pass(job_id: str, job_dir: Path, pdf_path: Path,
                        page_count: int):
    """Pass A, shared across books. Writes classification.json in job_dir."""
    from . import classify

    def warn(phase, message, page=None, sheet_id=None, detail=None):
        store.add_warning(job_id, phase, message, page=page,
                          sheet_id=sheet_id, detail=detail)

    def cls_progress(done, total):
        store.set_phase(job_id, "classifying", "Classifying sheets", done, total)

    store.set_phase(job_id, "classifying", "Classifying sheets", 0, page_count)
    return await classify.classify_sheets(job_dir, pdf_path, page_count, warn,
                                          cls_progress)


async def extract_book_facts(job_id: str, ctx, pdf_path: Path, index) -> dict:
    """Passes B-D for one book. Artifacts land in ctx.book_dir."""
    from . import text_pass, vision_pass, reconcile

    book_id = ctx.book.id

    def warn(phase, message, page=None, sheet_id=None, detail=None):
        store.add_warning(job_id, f"{book_id}:{phase}", message, page=page,
                          sheet_id=sheet_id, detail=detail)

    store.set_book(job_id, book_id, phase="text_pass",
                   message="Reading notes & schedules")
    text_cands, text_project = await text_pass.extract_text_facts(
        ctx, pdf_path, index, warn)

    def vis_progress(done, total):
        store.set_book(job_id, book_id, message="Analyzing drawings",
                       progress_done=done, progress_total=total)

    store.set_book(job_id, book_id, phase="vision_pass",
                   message="Analyzing drawings")
    vision_cands = await vision_pass.extract_vision_facts(ctx, index,
                                                          vis_progress, warn)

    store.set_book(job_id, book_id, phase="reconciling",
                   message="Reconciling facts")
    return await reconcile.reconcile_async(ctx, index, text_cands,
                                           vision_cands, text_project, warn)


def fake_facts(book: books.Book, page_count: int) -> dict:
    """Load the book's sample fact file with synthetic page provenance."""
    sample = book.sample_facts_path
    if sample is None or not sample.is_file():
        raise FileNotFoundError(
            f"no FAKE sample facts for book '{book.id}' "
            f"({sample or 'none registered'})")
    data = json.loads(sample.read_text())
    prov = {}
    for i, pred in enumerate(data.get("predicates", [])):
        page = (i % max(page_count, 1)) + 1
        prov[pred] = [{
            "page": page, "sheet_id": f"A{page}.0", "sheet_type": "floor_plan",
            "source": "vision", "evidence": f"[FAKE] synthetic provenance for {pred}",
            "confidence": 0.9, "value": True,
        }]
    data["_provenance"] = prov
    data["_needs_review"] = []
    data["_notes"] = "[FAKE EXTRACTOR] facts loaded from sample for flow testing."
    return data
