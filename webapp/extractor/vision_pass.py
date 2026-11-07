"""Pass C — per-drawing-sheet vision extraction (bounded concurrency)."""
from __future__ import annotations

import asyncio

from .. import config
from . import llm, pdf_io
from .context import ExtractionContext
from .prompts import base
from .schemas import CandidateFact, DRAWING_TYPES, SheetExtraction, SheetIndex


async def extract_vision_facts(ctx: ExtractionContext, index: SheetIndex,
                               on_progress=None, warn=None) -> list[CandidateFact]:
    drawing_sheets = [s for s in index.sheets
                      if (not s.is_text_dominant) and s.sheet_type in DRAWING_TYPES]
    total = len(drawing_sheets)
    sem = asyncio.Semaphore(config.VISION_CONCURRENCY)
    done = 0
    lock = asyncio.Lock()

    async def one(sheet) -> list[CandidateFact]:
        nonlocal done
        async with sem:
            b64 = pdf_io.saved_page_png_base64(ctx.pages_dir, sheet.page)
            header = (f"Sheet {sheet.sheet_id or '?'} (page {sheet.page}).\n"
                      f"{base.vision_prompt(ctx.prompts, sheet.sheet_type)}")
            content = [
                {"type": "text", "text": header},
                {"type": "image", "source": {"type": "base64",
                 "media_type": "image/png", "data": b64}},
            ]
            try:
                result = await llm.parse_call(
                    [{"role": "user", "content": content}], SheetExtraction,
                    job_dir=ctx.usage_dir, book_id=ctx.book.id,
                    context=f"vision: page {sheet.page} ({sheet.sheet_id or '?'})")
                facts = []
                for c in result.candidates:
                    c.page = c.page or sheet.page
                    c.sheet_id = c.sheet_id or sheet.sheet_id
                    c.source = "vision"
                    facts.append(c)
            except Exception as exc:  # noqa: BLE001 - skip a bad sheet, keep the rest
                if warn:
                    warn("vision_pass", f"Skipped drawing analysis for sheet "
                         f"{sheet.sheet_id or sheet.page}", page=sheet.page,
                         sheet_id=sheet.sheet_id, detail=str(exc))
                facts = []
        async with lock:
            done += 1
            if on_progress:
                on_progress(done, total)
        return facts

    results = await asyncio.gather(*(one(s) for s in drawing_sheets))
    return [c for sub in results for c in sub]
