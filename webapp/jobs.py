"""In-memory job registry backed by on-disk job directories.

Each job gets webapp/jobs/<uuid>/ holding the upload, all pipeline artifacts,
rendered page PNGs, and a status.json mirror so completed jobs survive a server
restart.
"""
from __future__ import annotations

import json
import logging
import shutil
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from . import config

log = logging.getLogger("plancheck.jobs")

# Ordered top-level phases for progress display in the UI. Book-specific
# stages (text_pass, vision_pass, reconciling, plan_check) happen inside
# per_book, tracked per book in JobStatus.book_status.
PHASES = [
    "queued",
    "validating",
    "classifying",
    "per_book",
    "done",
]

# Per-book stage template for book_status entries.
def _new_book_status() -> dict:
    return {"state": "pending", "phase": "pending", "message": "",
            "progress_done": 0, "progress_total": 0, "error": None}


@dataclass
class JobStatus:
    job_id: str
    state: str = "queued"        # queued | running | done | error
    phase: str = "queued"
    progress_done: int = 0
    progress_total: int = 0
    message: str = ""
    error: Optional[str] = None
    filename: str = ""
    books: list = field(default_factory=lambda: ["crc"])
    book_status: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["progress"] = {"done": self.progress_done, "total": self.progress_total}
        return d


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobStatus] = {}

    def job_dir(self, job_id: str) -> Path:
        return config.JOBS_DIR / job_id

    def create(self, filename: str, books: list[str] | None = None) -> JobStatus:
        job_id = uuid.uuid4().hex[:12]
        self.job_dir(job_id).mkdir(parents=True, exist_ok=True)
        books = list(books) if books else ["crc"]
        status = JobStatus(job_id=job_id, filename=filename, books=books,
                           book_status={b: _new_book_status() for b in books})
        self._jobs[job_id] = status
        self._persist(status)
        return status

    def get(self, job_id: str) -> Optional[JobStatus]:
        if job_id in self._jobs:
            return self._jobs[job_id]
        # Recover a finished job from disk after a restart.
        path = self.job_dir(job_id) / "status.json"
        if path.exists():
            data = json.loads(path.read_text())
            data.pop("progress", None)
            status = JobStatus(**{k: v for k, v in data.items()
                                  if k in JobStatus.__dataclass_fields__})
            self._jobs[job_id] = status
            return status
        return None

    def update(self, job_id: str, **fields) -> JobStatus:
        status = self._jobs[job_id]
        for k, v in fields.items():
            setattr(status, k, v)
        status.updated_at = time.time()
        self._persist(status)
        if fields.get("state") in ("done", "error"):
            log.info("job %s: %s — %s", job_id, status.state,
                     status.error or status.message)
        return status

    def add_warning(self, job_id: str, phase: str, message: str,
                    page: Optional[int] = None, sheet_id: Optional[str] = None,
                    detail: Optional[str] = None) -> None:
        """Record a non-fatal extraction problem (skipped sheet, fallback, ...)."""
        status = self._jobs.get(job_id)
        if status is None:
            return
        entry = {"phase": phase, "message": message, "ts": time.time()}
        if page is not None:
            entry["page"] = page
        if sheet_id is not None:
            entry["sheet_id"] = sheet_id
        if detail is not None:
            entry["detail"] = detail[:500]
        status.warnings.append(entry)
        status.updated_at = time.time()
        self._persist(status)
        log.warning("job %s [%s]: %s%s", job_id, phase, message,
                    f" | {detail[:200]}" if detail else "")

    def delete(self, job_id: str) -> None:
        """Permanently remove a job: its registry entry and its whole job dir
        (upload, page images, all pipeline artifacts)."""
        self._jobs.pop(job_id, None)
        d = self.job_dir(job_id)
        if d.is_dir():
            shutil.rmtree(d)
        log.info("job %s: deleted", job_id)

    def set_phase(self, job_id: str, phase: str, message: str = "",
                  done: int = 0, total: int = 0) -> JobStatus:
        progress = f" ({done}/{total})" if total else ""
        log.info("job %s: %s — %s%s", job_id, phase, message, progress)
        return self.update(job_id, state="running", phase=phase, message=message,
                           progress_done=done, progress_total=total)

    def set_book(self, job_id: str, book_id: str, **fields) -> None:
        """Update one book's status; during per_book, the top-level message
        and progress aggregate across all selected books."""
        status = self._jobs[job_id]
        bs = status.book_status.setdefault(book_id, _new_book_status())
        bs.update(fields)
        if "phase" in fields or "state" in fields:
            log.info("job %s [%s]: %s — %s", job_id, book_id,
                     bs.get("phase"), bs.get("error") or bs.get("message"))
        if status.phase == "per_book":
            parts, done, total = [], 0, 0
            for bid in status.books:
                b = status.book_status.get(bid)
                if not b:
                    continue
                parts.append(f"{bid.upper()}: {b.get('error') or b.get('message') or b.get('phase')}")
                done += b.get("progress_done", 0)
                total += b.get("progress_total", 0)
            status.message = " | ".join(parts)
            status.progress_done, status.progress_total = done, total
        status.updated_at = time.time()
        self._persist(status)

    def mark_interrupted(self) -> int:
        """Flip on-disk jobs stuck in queued/running to error at server startup.

        Jobs run as in-process tasks, so anything unfinished when the previous
        server exited can never complete; without this it polls as 'running'
        forever."""
        count = 0
        for d in config.JOBS_DIR.iterdir():
            path = d / "status.json"
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("state") not in ("queued", "running"):
                continue
            data.pop("progress", None)
            status = JobStatus(**{k: v for k, v in data.items()
                                  if k in JobStatus.__dataclass_fields__})
            status.state = "error"
            status.phase = "error"
            status.error = (f"Interrupted by server restart during "
                            f"'{data.get('phase', 'unknown')}'")
            status.updated_at = time.time()
            self._jobs[status.job_id] = status
            self._persist(status)
            log.warning("job %s: marked interrupted (was %s/%s)",
                        status.job_id, data.get("state"), data.get("phase"))
            count += 1
        return count

    def _persist(self, status: JobStatus) -> None:
        path = self.job_dir(status.job_id) / "status.json"
        path.write_text(json.dumps(status.to_dict(), indent=2))


store = JobStore()
