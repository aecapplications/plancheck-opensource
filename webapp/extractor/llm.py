"""AsyncAnthropic wrapper with per-book prompt-cached vocabulary system blocks.

Each book's vocabulary + extraction instructions are rendered once and marked
cache_control: ephemeral so every per-sheet call for that book reuses the
prefix (one cached prefix per book). A global semaphore caps total concurrent
Anthropic calls across all books. Per-call usage is appended to
job_dir/usage.jsonl (the caller passes the book's dir, or the job dir for the
shared classify pass).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from functools import lru_cache
from pathlib import Path
from typing import Type, TypeVar

import anthropic
from pydantic import BaseModel

from .. import books, config
from . import prompts, vocab

T = TypeVar("T", bound=BaseModel)

log = logging.getLogger("plancheck.llm")

_client: anthropic.AsyncAnthropic | None = None

# Global cap on concurrent Anthropic calls across all books in a job.
_llm_sem = asyncio.Semaphore(config.LLM_CONCURRENCY)


def client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic()
    return _client


@lru_cache(maxsize=None)
def system_blocks(book_id: str = "crc") -> list[dict]:
    """Two system blocks per book; cache_control on the last so both are
    cached together. Byte-identical across a book's calls -> prefix cache
    hits after that book's first call.
    """
    book = books.get(book_id)
    instructions = prompts.get(book.prompts_module).SYSTEM_INSTRUCTIONS
    return [
        {"type": "text", "text": instructions},
        {
            "type": "text",
            "text": ("CANONICAL PREDICATE VOCABULARY — you may ONLY emit predicate "
                     "names that appear verbatim in this list:\n\n"
                     + vocab.rendered_text(book_id)),
            "cache_control": {"type": "ephemeral"},
        },
    ]


def _log_usage(job_dir: Path | None, usage) -> None:
    if job_dir is None or usage is None:
        return
    rec = {
        "input_tokens": getattr(usage, "input_tokens", 0),
        "output_tokens": getattr(usage, "output_tokens", 0),
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0),
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0),
    }
    with (job_dir / "usage.jsonl").open("a") as f:
        f.write(json.dumps(rec) + "\n")


class ExtractionCallError(RuntimeError):
    """An LLM call failed. `context` says which pass/page; `retryable` is False
    for 4xx invalid-request failures where re-sending the payload cannot help
    (callers should fall back instead of retrying)."""

    def __init__(self, context: str, cause: Exception, retryable: bool):
        super().__init__(f"[{context or 'llm'}] {cause}")
        self.context = context
        self.cause = cause
        self.retryable = retryable


# 4xx errors where the request itself is unacceptable — retrying the same
# payload is pointless and the caller should fall back to another strategy.
_FATAL_API_ERRORS = (
    anthropic.BadRequestError,
    anthropic.AuthenticationError,
    anthropic.PermissionDeniedError,
    anthropic.NotFoundError,
    anthropic.UnprocessableEntityError,
)


def _classify_exc(exc: Exception) -> str:
    """'fatal' (never retry), 'transient' (retry unchanged), or 'parse'
    (retry with a corrective message appended)."""
    # A 400, but actually a server-side timeout compiling the structured-output
    # grammar: the compiled grammar is cached on their end, so an identical
    # retry regularly succeeds once a compile gets through.
    if (isinstance(exc, anthropic.BadRequestError)
            and "Grammar compilation timed out" in str(exc)):
        return "transient"
    if isinstance(exc, _FATAL_API_ERRORS):
        return "fatal"
    if isinstance(exc, (anthropic.APIConnectionError, anthropic.RateLimitError)):
        return "transient"
    if isinstance(exc, anthropic.APIStatusError) and exc.status_code >= 500:
        return "transient"
    return "parse"


async def parse_call(messages: list[dict], output_model: Type[T],
                     job_dir: Path | None = None, max_tokens: int | None = None,
                     retries: int = 2, context: str = "",
                     book_id: str = "crc",
                     system: list[dict] | None = None) -> T:
    """Structured-output call. Transient API errors retry unchanged; parse /
    validation failures retry with the error appended so the model can
    self-correct; fatal 4xx errors raise immediately so callers can fall back.
    All failures surface as ExtractionCallError tagged with `context`.

    `book_id` selects the book's cached system prefix; `system` overrides it
    entirely (used by the shared classify pass). `job_dir` is where this
    call's usage.jsonl line lands (per-book dir, or job dir for classify)."""
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        started = time.monotonic()
        log.info("call %s: sending (attempt %d/%d)",
                 context or "llm", attempt + 1, retries + 1)

        async def _heartbeat() -> None:
            while True:
                await asyncio.sleep(config.LLM_HEARTBEAT_S)
                log.info("call %s: still waiting (%.0fs elapsed, times out at %ds)",
                         context or "llm", time.monotonic() - started,
                         config.LLM_TIMEOUT_S)

        beat = asyncio.create_task(_heartbeat())
        try:
            async with _llm_sem:
                resp = await client().messages.parse(
                    model=config.MODEL,
                    max_tokens=max_tokens or config.MAX_TOKENS,
                    system=system if system is not None else system_blocks(book_id),
                    thinking={"type": "adaptive"},
                    messages=messages,
                    output_format=output_model,
                    timeout=config.LLM_TIMEOUT_S,
                )
            _log_usage(job_dir, getattr(resp, "usage", None))
            if resp.parsed_output is None:
                raise ValueError("Model returned no parseable structured output")
            u = getattr(resp, "usage", None)
            log.info("call %s: ok in %.1fs (in=%d out=%d cache_read=%d)",
                     context or "llm", time.monotonic() - started,
                     getattr(u, "input_tokens", 0), getattr(u, "output_tokens", 0),
                     getattr(u, "cache_read_input_tokens", 0))
            return resp.parsed_output
        except Exception as exc:  # noqa: BLE001
            kind = _classify_exc(exc)
            log.warning("call %s: %s failure in %.1fs (attempt %d/%d): %s",
                        context or "llm", kind, time.monotonic() - started,
                        attempt + 1, retries + 1, exc)
            if kind == "fatal":
                raise ExtractionCallError(context, exc, retryable=False) from exc
            last_exc = exc
            if attempt < retries and kind == "parse":
                messages = messages + [{
                    "role": "user",
                    "content": f"The previous response could not be parsed "
                               f"({exc}). Return only valid output matching the "
                               f"required schema.",
                }]
            elif attempt < retries and kind == "transient":
                await asyncio.sleep(5 * (attempt + 1))
        finally:
            beat.cancel()
    raise ExtractionCallError(
        context, RuntimeError(f"failed after {retries + 1} attempts: {last_exc}"),
        retryable=True)
