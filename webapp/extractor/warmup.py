"""Pre-compile structured-output grammars at startup.

The API compiles each output schema into a constrained-decoding grammar
server-side and caches it (~24h), keyed to the exact schema. Any schema
change invalidates that cache, and the next call pays a fresh compile —
which under load fails with 'Grammar compilation timed out' (a 400), costing
~100s per attempt inside a job while re-uploading multi-megabyte PDF payloads
on every retry.

This module plays that compile lottery off the critical path instead: at
server startup (live mode only) it sends one tiny call per output schema and
retries patiently until each grammar is compiled and cached. User jobs then
start with every grammar warm. Warm-up failure is never fatal — the first
job call simply pays the compile as before.
"""
from __future__ import annotations

import asyncio
import logging

from . import llm
from .schemas import ReconciledFacts, SheetExtraction, SheetIndex

log = logging.getLogger("plancheck.warmup")

# Small dedicated system block — grammar identity depends only on the output
# schema, so the cheapest possible prompt around it is fine.
_WARMUP_SYSTEM = [{
    "type": "text",
    "text": "This is a warm-up request. Return the smallest valid object "
            "matching the required output schema.",
}]

_SCHEMAS = [
    ("SheetIndex", SheetIndex,
     "Warm-up: return an empty sheets list and a project object with every "
     "field null."),
    ("SheetExtraction", SheetExtraction,
     "Warm-up: return an empty candidates list and null project_updates."),
    ("ReconciledFacts", ReconciledFacts,
     "Warm-up: return empty predicates and false_predicates lists and a "
     "project object with every field null."),
]

MAX_ATTEMPTS = 8       # failing compile attempts take ~100s server-side each
RETRY_DELAY_S = 60
JOB_WAIT_S = 120       # how long a starting job waits for warm-up to finish

_task: asyncio.Task | None = None


def start() -> None:
    """Kick off background warm-up (called once at server startup)."""
    global _task
    _task = asyncio.create_task(warm_schemas())


async def wait_ready(timeout: float = JOB_WAIT_S) -> None:
    """Give an in-flight warm-up a head start before a job begins, so the job
    doesn't race it for the same cold grammars. Never blocks past `timeout`
    and never raises."""
    if _task is None or _task.done():
        return
    log.info("job start: waiting up to %ds for grammar warm-up", int(timeout))
    try:
        await asyncio.wait_for(asyncio.shield(_task), timeout)
    except asyncio.TimeoutError:
        log.warning("grammar warm-up still running after %ds — job proceeding; "
                    "cold grammars may retry in-job", int(timeout))
    except Exception:  # noqa: BLE001 - warm-up failures are already logged
        pass


async def _warm_one(name: str, output_model, prompt: str) -> bool:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            # retries=0: this loop owns the pacing (parse_call's quick backoff
            # is tuned for in-job calls, not a 20-minute patience budget).
            await llm.parse_call(
                [{"role": "user", "content": prompt}], output_model,
                system=_WARMUP_SYSTEM, max_tokens=2048, retries=0,
                context=f"warmup: {name}")
            log.info("warmup: %s grammar compiled and cached", name)
            return True
        except Exception as exc:  # noqa: BLE001 - warm-up must never propagate
            log.warning("warmup: %s attempt %d/%d failed: %s",
                        name, attempt, MAX_ATTEMPTS, exc)
            if attempt < MAX_ATTEMPTS:
                await asyncio.sleep(RETRY_DELAY_S)
    log.warning("warmup: %s gave up after %d attempts — the first job call "
                "using it will pay the compile instead", name, MAX_ATTEMPTS)
    return False


async def warm_schemas() -> None:
    """Warm every output schema, one at a time.

    Sequential on purpose: a struggling compile service is not helped by
    parallel attempts, and one warm-up call at a time leaves the global LLM
    semaphore's remaining slots free for any job that starts meanwhile.
    """
    ok = 0
    for name, model, prompt in _SCHEMAS:
        if await _warm_one(name, model, prompt):
            ok += 1
    log.info("warmup complete: %d/%d schema grammars compiled", ok, len(_SCHEMAS))
