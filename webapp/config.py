"""Configuration and shared paths for the PlanCheck webapp.

Per-book paths (rule corpus, vocabulary, sample facts) live in the code-book
registry, webapp/books.py.
"""
from __future__ import annotations

import os
from pathlib import Path

# webapp/config.py -> PlanCheck repo root
REPO_ROOT = Path(__file__).resolve().parents[1]

WEBAPP_DIR = Path(__file__).resolve().parent
JOBS_DIR = WEBAPP_DIR / "jobs"
STATIC_DIR = WEBAPP_DIR / "static"

# --- LLM ---
MODEL = "claude-opus-4-8"
MAX_TOKENS = 16000  # keeps non-streaming requests under SDK HTTP timeout
LLM_TIMEOUT_S = 300     # per-call cap; a hung call fails fast (retried once,
                        # then the caller's fallback ladder takes over)
LLM_HEARTBEAT_S = 30    # log "still waiting" at this interval during a call

# --- Limits / guardrails ---
MAX_PAGES = 60                 # PDF document-block hard limit is 100; stay well under
MAX_UPLOAD_MB = 80
MAX_IMAGE_LONG_EDGE = 2576     # Opus 4.8 high-res vision maximum
THUMBNAIL_LONG_EDGE = 1000     # classification fallback / UI thumbnails
VISION_CONCURRENCY = 3         # bounds parallel per-sheet calls per book; keeps cache TTL warm
LLM_CONCURRENCY = 4            # global cap on concurrent Anthropic calls across all books
CONFIDENCE_THRESHOLD = 0.6     # below this a fact is "needs review", not asserted
PDF_INLINE_MAX_MB = 30         # above this, classify via thumbnail batches not a doc block
DOC_BLOCK_MAX_PAGE_EDGE_PTS = 1728  # 24in; larger sheets fail the API's PDF rasterizer

# Approximate Opus 4.8 pricing ($ per 1M tokens) for the cost estimate shown in results.
PRICE_INPUT_PER_MTOK = 5.0
PRICE_OUTPUT_PER_MTOK = 25.0
PRICE_CACHE_READ_PER_MTOK = 0.5
PRICE_CACHE_WRITE_PER_MTOK = 6.25

# When set, skip all LLM passes and synthesize facts from a sample file so the
# web flow can be exercised end-to-end with zero API cost.
FAKE_EXTRACTOR = os.environ.get("EXTRACTOR_FAKE") == "1"

JOBS_DIR.mkdir(parents=True, exist_ok=True)
