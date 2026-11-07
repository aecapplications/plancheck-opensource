"""FastAPI app: upload a plan-check PDF, run extraction + the CRC pipeline,
serve per-sheet compliance flags.

Run from crc-graph/:
    uvicorn webapp.app:app --port 8000 --reload
"""
from __future__ import annotations

import asyncio
import json
import logging
import re

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import books as book_registry
from . import config
from .jobs import store
from .pipeline import run_job

app = FastAPI(title="CRC Plan-Check")


class _StatusPollFilter(logging.Filter):
    """Drop access-log lines for the UI's 2.5s status polls; they bury the
    plancheck stage/call lines. Result/report/page fetches still log."""

    _POLL = re.compile(r'"GET /api/jobs/\w+ HTTP')

    def filter(self, record: logging.LogRecord) -> bool:
        return not self._POLL.search(record.getMessage())


@app.on_event("startup")
async def _check_env() -> None:
    import os
    # uvicorn only attaches handlers to its own loggers; give plancheck.* a
    # root handler so job/LLM lifecycle lines reach the terminal.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S")
    logging.getLogger("uvicorn.access").addFilter(_StatusPollFilter())
    if not config.FAKE_EXTRACTOR and not os.environ.get("ANTHROPIC_API_KEY"):
        print("WARNING: ANTHROPIC_API_KEY is not set. Set it, or run with "
              "EXTRACTOR_FAKE=1 to test the flow without the API.")
    if not config.FAKE_EXTRACTOR and os.environ.get("ANTHROPIC_API_KEY"):
        # Pre-compile output-schema grammars in the background so jobs never
        # pay (or retry) the server-side compile mid-run.
        from .extractor import warmup
        warmup.start()
    interrupted = store.mark_interrupted()
    if interrupted:
        logging.getLogger("plancheck.jobs").info(
            "%d unfinished job(s) from a previous server marked as interrupted",
            interrupted)


@app.post("/api/jobs", status_code=202)
async def create_job(file: UploadFile = File(...),
                     books: list[str] | None = Form(None)) -> JSONResponse:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Upload must be a .pdf file")

    book_ids = list(dict.fromkeys(books)) if books else ["crc"]
    for bid in book_ids:
        if bid not in book_registry.REGISTRY:
            raise HTTPException(400, f"Unknown code book '{bid}'")
        if not book_registry.available(book_registry.get(bid)):
            raise HTTPException(400, f"Code book '{bid}' has no extracted "
                                     f"rules yet and cannot be checked")

    data = await file.read()
    size_mb = len(data) / (1024 * 1024)
    if size_mb > config.MAX_UPLOAD_MB:
        raise HTTPException(400, f"File is {size_mb:.0f} MB; limit is "
                                 f"{config.MAX_UPLOAD_MB} MB")
    if not data[:5].startswith(b"%PDF"):
        raise HTTPException(400, "File does not look like a PDF")

    status = store.create(file.filename, book_ids)
    (store.job_dir(status.job_id) / "upload.pdf").write_bytes(data)

    asyncio.create_task(run_job(status.job_id))
    return JSONResponse({"job_id": status.job_id}, status_code=202)


@app.get("/api/books")
async def list_books() -> list[dict]:
    """Registered code books with availability and rule counts."""
    return [book_registry.book_info(b) for b in book_registry.REGISTRY.values()]


@app.get("/api/jobs")
async def list_jobs() -> list[dict]:
    """All jobs known on disk, newest first (for browsing past results)."""
    jobs = []
    for d in config.JOBS_DIR.iterdir():
        path = d / "status.json"
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        jobs.append({k: data.get(k) for k in
                     ("job_id", "state", "phase", "message", "error",
                      "filename", "created_at", "updated_at")})
    jobs.sort(key=lambda j: j.get("created_at") or 0, reverse=True)
    return jobs


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    status = store.get(job_id)
    if not status:
        raise HTTPException(404, "Unknown job")
    return status.to_dict()


@app.delete("/api/jobs/{job_id}", status_code=204)
async def delete_job(job_id: str) -> Response:
    # Job ids are 12 hex chars; rejecting anything else also blocks path
    # tricks like ".." from ever reaching the filesystem delete.
    if not re.fullmatch(r"[0-9a-f]{12}", job_id):
        raise HTTPException(404, "Unknown job")
    status = store.get(job_id)
    if not status:
        raise HTTPException(404, "Unknown job")
    if status.state in ("queued", "running"):
        raise HTTPException(409, "Job is still running — wait for it to "
                                 "finish (or restart the server) first")
    store.delete(job_id)
    return Response(status_code=204)


_ARTIFACTS = {"result": "result.json", "report": "report.md",
              "facts": "facts.json"}


def _artifact_path(job_id: str, name: str, book_id: str | None = None):
    """Resolve an artifact: per-book path when book_id is given; otherwise the
    first selected book's copy, falling back to the top-level file so
    pre-multi-book job dirs keep serving."""
    job_dir = store.job_dir(job_id)
    if book_id:
        return job_dir / "books" / book_id / name
    status = store.get(job_id)
    if status and status.books:
        per_book = job_dir / "books" / status.books[0] / name
        if per_book.exists():
            return per_book
    return job_dir / name


def _serve_artifact(path, artifact: str):
    if not path.exists():
        raise HTTPException(404, f"{artifact.capitalize()} not ready")
    if artifact == "report":
        return PlainTextResponse(path.read_text())
    return JSONResponse(json.loads(path.read_text()))


@app.get("/api/jobs/{job_id}/books/{book_id}/{artifact}")
async def get_book_artifact(job_id: str, book_id: str, artifact: str):
    if artifact not in _ARTIFACTS:
        raise HTTPException(404, "Unknown artifact")
    return _serve_artifact(_artifact_path(job_id, _ARTIFACTS[artifact], book_id),
                           artifact)


@app.get("/api/jobs/{job_id}/result")
async def get_result(job_id: str):
    return _serve_artifact(_artifact_path(job_id, "result.json"), "result")


@app.get("/api/jobs/{job_id}/report", response_class=PlainTextResponse)
async def get_report(job_id: str):
    return _serve_artifact(_artifact_path(job_id, "report.md"), "report")


@app.get("/api/jobs/{job_id}/facts")
async def get_facts(job_id: str):
    return _serve_artifact(_artifact_path(job_id, "facts.json"), "facts")


@app.get("/api/jobs/{job_id}/pages/{n}.png")
async def get_page(job_id: str, n: int) -> FileResponse:
    path = store.job_dir(job_id) / "pages" / f"page_{n}.png"
    if not path.exists():
        raise HTTPException(404, "Page image not found")
    return FileResponse(path, media_type="image/png")


# Static UI mounted last so /api/* takes precedence.
app.mount("/", StaticFiles(directory=str(config.STATIC_DIR), html=True), name="static")
