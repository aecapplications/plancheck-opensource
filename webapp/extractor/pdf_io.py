"""PyMuPDF helpers: validation, text extraction, page rendering, base64."""
from __future__ import annotations

import base64
from pathlib import Path

import fitz  # PyMuPDF

from .. import config


def validate_pdf(path: Path) -> tuple[int, list[str]]:
    """Return (page_count, errors). Empty errors list means OK."""
    errors: list[str] = []
    try:
        doc = fitz.open(path)
    except Exception as exc:  # noqa: BLE001
        return 0, [f"Could not open PDF: {exc}"]
    try:
        if doc.is_encrypted and not doc.authenticate(""):
            errors.append("PDF is password-protected")
        n = doc.page_count
        if n == 0:
            errors.append("PDF has no pages")
        if n > config.MAX_PAGES:
            errors.append(f"PDF has {n} pages; limit is {config.MAX_PAGES}")
        return n, errors
    finally:
        doc.close()


def _zoom_for(page: "fitz.Page", long_edge: int) -> float:
    longest = max(page.rect.width, page.rect.height) or 1.0
    return min(long_edge / longest, 4.0)


def render_page_png(doc: "fitz.Document", page_index: int, long_edge: int) -> bytes:
    """Render a 0-based page to PNG bytes at the given long-edge pixel target."""
    page = doc.load_page(page_index)
    zoom = _zoom_for(page, long_edge)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return pix.tobytes("png")


def render_all_pages(pdf_path: Path, out_dir: Path,
                     long_edge: int | None = None) -> int:
    """Render every page to out_dir/page_<1based>.png. Returns page count."""
    out_dir.mkdir(parents=True, exist_ok=True)
    long_edge = long_edge or config.MAX_IMAGE_LONG_EDGE
    doc = fitz.open(pdf_path)
    try:
        for i in range(doc.page_count):
            png = render_page_png(doc, i, long_edge)
            (out_dir / f"page_{i + 1}.png").write_bytes(png)
        return doc.page_count
    finally:
        doc.close()


def downscale_png(png_bytes: bytes, long_edge: int) -> bytes:
    """Downscale PNG bytes so the longest edge is at most long_edge pixels."""
    doc = fitz.open(stream=png_bytes, filetype="png")
    try:
        page = doc.load_page(0)
        longest = max(page.rect.width, page.rect.height) or 1.0
        if longest <= long_edge:
            return png_bytes
        zoom = long_edge / longest
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return pix.tobytes("png")
    finally:
        doc.close()


def max_page_edge_pts(pdf_path: Path) -> float:
    """Longest page edge in the document, in PDF points (1/72 inch)."""
    doc = fitz.open(pdf_path)
    try:
        return max((max(doc.load_page(i).rect.width, doc.load_page(i).rect.height)
                    for i in range(doc.page_count)), default=0.0)
    finally:
        doc.close()


def page_text(pdf_path: Path, page_index: int) -> str:
    doc = fitz.open(pdf_path)
    try:
        return doc.load_page(page_index).get_text("text")
    finally:
        doc.close()


def all_page_texts(pdf_path: Path) -> list[str]:
    doc = fitz.open(pdf_path)
    try:
        return [doc.load_page(i).get_text("text") for i in range(doc.page_count)]
    finally:
        doc.close()


def pdf_base64(pdf_path: Path) -> str:
    return base64.standard_b64encode(pdf_path.read_bytes()).decode("ascii")


def png_base64(png_bytes: bytes) -> str:
    return base64.standard_b64encode(png_bytes).decode("ascii")


def saved_page_png_base64(job_pages_dir: Path, page_1based: int) -> str:
    return png_base64((job_pages_dir / f"page_{page_1based}.png").read_bytes())


def pdf_size_mb(pdf_path: Path) -> float:
    return pdf_path.stat().st_size / (1024 * 1024)
