"""Pass B — extract facts from text-bearing sheets (notes, schedules, cover)."""
from __future__ import annotations

from pathlib import Path

from . import llm, pdf_io
from .context import ExtractionContext
from .schemas import (CandidateFact, ProjectMeta, SheetExtraction, SheetIndex,
                      TEXT_TYPES)

MIN_TEXT_CHARS = 200  # below this a "text" sheet is likely scanned -> use vision


async def extract_text_facts(ctx: ExtractionContext, pdf_path: Path,
                             index: SheetIndex,
                             warn=None) -> tuple[list[CandidateFact], ProjectMeta]:
    candidates: list[CandidateFact] = []
    project = ProjectMeta()

    text_pages = [s for s in index.sheets
                  if s.is_text_dominant or s.sheet_type in TEXT_TYPES]

    for sheet in text_pages:
        try:
            raw = pdf_io.page_text(pdf_path, sheet.page - 1)
            if len(raw.strip()) < MIN_TEXT_CHARS:
                # Scanned/flattened note sheet — send the rendered image instead.
                content = _image_content(ctx, sheet.page, sheet)
            else:
                content = _text_content(ctx, raw, sheet)

            result = await llm.parse_call(
                [{"role": "user", "content": content}], SheetExtraction,
                job_dir=ctx.usage_dir, book_id=ctx.book.id,
                context=f"text: page {sheet.page} ({sheet.sheet_id or '?'})")
        except Exception as exc:  # noqa: BLE001 - skip a bad sheet, keep the rest
            if warn:
                warn("text_pass", f"Skipped text extraction for sheet "
                     f"{sheet.sheet_id or sheet.page}", page=sheet.page,
                     sheet_id=sheet.sheet_id, detail=str(exc))
            continue
        for c in result.candidates:
            c.page = c.page or sheet.page
            c.sheet_id = c.sheet_id or sheet.sheet_id
            c.source = "text"
            candidates.append(c)
        project = project.merge(result.project_updates)

    return candidates, project


def _header(sheet) -> str:
    return (f"Sheet {sheet.sheet_id or '?'} (page {sheet.page}, "
            f"type {sheet.sheet_type}).\n")


def _text_content(ctx: ExtractionContext, raw: str, sheet) -> list[dict]:
    return [{"type": "text",
             "text": ctx.prompts.TEXT_PROMPT + "\n\n" + _header(sheet) + "\n" + raw}]


def _image_content(ctx: ExtractionContext, page: int, sheet) -> list[dict]:
    b64 = pdf_io.saved_page_png_base64(ctx.pages_dir, page)
    return [
        {"type": "text", "text": ctx.prompts.TEXT_PROMPT + "\n\n" + _header(sheet) +
         "(Sheet text was not machine-readable; read it from the image.)"},
        {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                      "data": b64}},
    ]
