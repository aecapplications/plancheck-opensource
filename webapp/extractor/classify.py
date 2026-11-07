"""Pass A — classify every page (sheet type, ID) and read project metadata.

Shared across code books: one classification serves every selected book, so
it uses the book-neutral prompt and its own small system block (not any
book's vocabulary prefix). Fallback ladder: whole-document block -> thumbnail
batches -> single pages -> backfill as 'other'. Only total failure (no page
classifies) raises.
"""
from __future__ import annotations

from pathlib import Path

from .. import config
from . import llm, pdf_io
from .prompts import base
from .schemas import ProjectMeta, SheetIndex, SheetInfo

BATCH_SIZE = 10


async def classify_sheets(job_dir: Path, pdf_path: Path, page_count: int,
                          warn=None, progress=None) -> SheetIndex:
    index: SheetIndex | None = None
    # The API rasterizes PDF document blocks server-side; oversized sheets
    # (full-format plan sets) predictably fail it, so route those straight to
    # locally rendered thumbnails.
    doc_block_ok = (
        pdf_io.pdf_size_mb(pdf_path) <= config.PDF_INLINE_MAX_MB
        and pdf_io.max_page_edge_pts(pdf_path) <= config.DOC_BLOCK_MAX_PAGE_EDGE_PTS
    )
    if doc_block_ok:
        try:
            index = await _classify_via_document(job_dir, pdf_path)
        except llm.ExtractionCallError as exc:
            if warn:
                warn("classify", "Whole-document classification failed; "
                     "falling back to per-page thumbnails", detail=str(exc))
    if index is None:
        index = await _classify_via_thumbnails(job_dir, pdf_path, page_count,
                                               warn, progress)
    if progress:
        progress(page_count, page_count)
    index = _backfill_pages(index, page_count)
    (job_dir / "classification.json").write_text(index.model_dump_json(indent=2))
    return index


async def _classify_via_document(job_dir: Path, pdf_path: Path) -> SheetIndex:
    messages = [{
        "role": "user",
        "content": [
            {"type": "document", "source": {
                "type": "base64", "media_type": "application/pdf",
                "data": pdf_io.pdf_base64(pdf_path)}},
            {"type": "text", "text": base.CLASSIFY_PROMPT},
        ],
    }]
    return await llm.parse_call(messages, SheetIndex, job_dir=job_dir,
                                system=base.CLASSIFY_SYSTEM_BLOCKS,
                                context="classify: whole document")


async def _classify_via_thumbnails(job_dir: Path, pdf_path: Path,
                                   page_count: int, warn=None,
                                   progress=None) -> SheetIndex:
    sheets: list[SheetInfo] = []
    project = ProjectMeta()
    done = 0

    def advance(n: int) -> None:
        nonlocal done
        done += n
        if progress:
            progress(done, page_count)

    async def classify_pages(pages: list[int], context: str) -> None:
        nonlocal project
        content: list[dict] = []
        for p in pages:
            content.append({"type": "text", "text": f"Page {p}:"})
            content.append({"type": "image", "source": {
                "type": "base64", "media_type": "image/png",
                "data": _page_thumb_b64(job_dir, pdf_path, p)}})
        content.append({"type": "text", "text": base.CLASSIFY_PROMPT})
        batch = await llm.parse_call([{"role": "user", "content": content}],
                                     SheetIndex, job_dir=job_dir,
                                     system=base.CLASSIFY_SYSTEM_BLOCKS,
                                     context=context)
        sheets.extend(batch.sheets)
        project = project.merge(batch.project)

    for start in range(0, page_count, BATCH_SIZE):
        pages = list(range(start + 1, min(start + BATCH_SIZE, page_count) + 1))
        try:
            await classify_pages(pages, f"classify: pages {pages[0]}-{pages[-1]}")
            advance(len(pages))
        except llm.ExtractionCallError as exc:
            if warn:
                warn("classify", f"Batch classification failed for pages "
                     f"{pages[0]}-{pages[-1]}; retrying page-by-page",
                     detail=str(exc))
            for p in pages:
                try:
                    await classify_pages([p], f"classify: page {p}")
                except llm.ExtractionCallError as exc_page:
                    if warn:
                        warn("classify", f"Could not classify page {p}; "
                             f"treating it as 'other'", page=p,
                             detail=str(exc_page))
                advance(1)

    if page_count and not sheets:
        raise RuntimeError("classification failed for every page — cannot proceed")
    return SheetIndex(sheets=sheets, project=project)


def _page_thumb_b64(job_dir: Path, pdf_path: Path, page_1based: int) -> str:
    """Thumbnail from the already-rendered page PNG when available (avoids
    re-rendering the PDF); falls back to rendering the page directly."""
    png_path = job_dir / "pages" / f"page_{page_1based}.png"
    if png_path.exists():
        return pdf_io.png_base64(pdf_io.downscale_png(
            png_path.read_bytes(), config.THUMBNAIL_LONG_EDGE))
    import fitz
    doc = fitz.open(pdf_path)
    try:
        png = pdf_io.render_page_png(doc, page_1based - 1, config.THUMBNAIL_LONG_EDGE)
    finally:
        doc.close()
    return pdf_io.png_base64(png)


def _backfill_pages(index: SheetIndex, page_count: int) -> SheetIndex:
    """Ensure every page 1..N has a SheetInfo (default to 'other')."""
    by_page = {s.page: s for s in index.sheets if 1 <= s.page <= page_count}
    for p in range(1, page_count + 1):
        if p not in by_page:
            by_page[p] = SheetInfo(page=p, sheet_type="other", is_text_dominant=False)
    return SheetIndex(sheets=[by_page[p] for p in sorted(by_page)],
                      project=index.project)
