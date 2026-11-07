"""Book-neutral prompt scaffolding shared by every code book.

Classification is a single shared pass over the whole plan set (one sheet
index serves every selected book), so its prompt and system block live here
and mention no specific code. Book-specific extraction prompts live in the
sibling modules (crc.py, cec.py, ...), selected via prompts.get().
"""
from __future__ import annotations

# Dedicated system block for the classification pass. Deliberately small —
# classification needs sheet-reading skill, not the (large, book-specific)
# predicate vocabulary, so classify calls don't pay for or depend on it.
CLASSIFY_SYSTEM = """You are a construction plan-set triage assistant. You \
look at every page of a permit submittal (architectural, structural, \
electrical, mechanical, or plumbing drawings and notes) and classify each \
sheet accurately from its title block, contents, and drawing conventions. \
You also read project-level metadata off cover sheets and general notes. Be \
precise: a wrong sheet type sends the wrong analysis to the sheet later."""

CLASSIFY_SYSTEM_BLOCKS = [
    {"type": "text", "text": CLASSIFY_SYSTEM,
     "cache_control": {"type": "ephemeral"}},
]

CLASSIFY_PROMPT = """Classify every page of this plan set.

For each page return: the 1-based page number, the sheet ID from the title block \
(e.g. "A2.1", "S1.0", "E1.0" — null if none), the sheet title, the sheet_type \
(from the enum), and is_text_dominant (true for notes/schedules/specifications, \
false for drawings).

Also extract project-level metadata from the cover sheet / general notes into the \
project object: address, building type, scope of work (new construction / \
addition / alteration), number of stories, occupancy group, design wind speed \
(mph), ground snow load (psf), seismic design category, soil class, climate zone, \
and fire hazard severity zone. Use null for anything not stated."""


def vision_prompt(module, sheet_type: str) -> str:
    """Per-sheet-type vision guidance from a book's prompts module."""
    return module.VISION_PROMPTS.get(sheet_type, module.VISION_DEFAULT)
