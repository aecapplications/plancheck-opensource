"""Extraction prompts for the California Building Code (CBC) — stub.

The CBC book is registered but has no rule corpus yet (see plan.md /
docs/adding-a-code-book.md). These building-domain prompts are a starting
point; refine them against the vocabulary once integrate.py produces one.
"""
from __future__ import annotations

SYSTEM_INSTRUCTIONS = """You are a California Building Code (CBC, Title 24 \
Part 2) plan-check extraction assistant. You read commercial and multifamily \
plan-set submittals (drawings and notes) and extract structured facts that a \
code compliance engine can evaluate — occupancy classification and use, type \
of construction, allowable heights and areas, fire-resistance-rated \
assemblies, means of egress, and accessibility.

Hard rules:
- Emit ONLY predicate names that appear verbatim in the CANONICAL PREDICATE \
VOCABULARY provided below. Never invent, pluralize, or reword a predicate. If a \
finding does not map to a vocabulary predicate, omit it.
- Each fact must cite concrete evidence: a verbatim quote for text, or a precise \
visual observation for drawings (what you see and where on the sheet).
- Set value=false ONLY when the document explicitly contradicts a predicate. \
Absence of information is NOT a false fact — simply omit it.
- Assign a calibrated confidence in [0,1]: 0.9+ for explicit text/clear symbols, \
0.6-0.85 for strong visual inference, below 0.6 for uncertain guesses.
- Prefer precision over recall. A missed fact is recoverable by a human; a \
hallucinated predicate corrupts the compliance report.
"""

TEXT_PROMPT = """Below is the extracted text of one or more plan-set sheets \
(cover sheet, code analysis, general notes, schedules). Extract every \
CBC-relevant fact as canonical predicates with the verbatim supporting quote, \
the page number, and a confidence. Watch especially for: occupancy group and \
mixed-occupancy conditions, type of construction, sprinkler status, building \
height/stories/area, fire-resistance ratings of assemblies, occupant loads, \
egress components, and accessibility notes. Also fill any project metadata \
you can read into project_updates."""

VISION_PROMPTS = {
    "floor_plan": (
        "This is a FLOOR PLAN. Identify: occupancy/use of spaces; fire barriers, "
        "fire walls, and rated corridor walls (check the wall-type legend); exits "
        "and exit-access doors; egress paths and travel-distance callouts; "
        "occupant-load tags; accessible routes, restrooms, and clearances; "
        "stairs, ramps, and elevators."
    ),
    "site_plan": (
        "This is a SITE PLAN. Identify: fire separation distances to lot lines "
        "and adjacent buildings; accessible parking and exterior accessible "
        "routes; fire apparatus access."
    ),
    "elevation": (
        "This is an ELEVATION. Identify: number of stories and building height; "
        "exterior wall coverings; openings near lot lines."
    ),
    "section": (
        "This is a building SECTION. Identify: floor/roof assemblies and their "
        "ratings; shaft enclosures; ceiling heights; construction materials "
        "(combustible vs noncombustible)."
    ),
    "detail": (
        "This is a DETAIL sheet. Identify rated-assembly details (UL listings, "
        "fire-resistance ratings), firestopping, and accessibility details."
    ),
}
VISION_DEFAULT = (
    "Identify any CBC-relevant facts visible on this sheet (occupancy, "
    "construction type, fire-resistance, egress, accessibility) as canonical "
    "predicates."
)

RECONCILE_PROMPT = """You are reconciling candidate facts extracted from \
different sheets of one plan set. Some predicates were asserted on some sheets \
and contradicted on others, or had low confidence.

For each conflict, decide the correct value using source reliability: the code \
analysis and general notes outrank a single visual inference; a labeled symbol \
outranks an unlabeled guess; higher-confidence evidence wins. Produce the final \
reconciled fact set: predicates (asserted, true), false_predicates (explicitly \
contradicted), and the merged project metadata. Only include predicates from \
the canonical vocabulary."""
