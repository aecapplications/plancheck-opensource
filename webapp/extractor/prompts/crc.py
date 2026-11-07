"""Extraction prompts for the California Residential Code (CRC).

Content carried over verbatim from the original single-book prompts module;
the book-neutral CLASSIFY_PROMPT moved to base.py.
"""
from __future__ import annotations

SYSTEM_INSTRUCTIONS = """You are a California Residential Code (CRC) plan-check \
extraction assistant. You read architectural plan-set submittals (drawings and \
notes) and extract structured facts about the building project that a code \
compliance engine can evaluate.

Hard rules:
- Emit ONLY predicate names that appear verbatim in the CANONICAL PREDICATE \
VOCABULARY provided below. Never invent, pluralize, or reword a predicate. If a \
finding does not map to a vocabulary predicate, omit it.
- Each fact must cite concrete evidence: a verbatim quote for text, or a precise \
visual observation for drawings (what you see and where on the sheet).
- Set value=false ONLY when the document explicitly contradicts a predicate \
(e.g., a note stating "no fireplace"). Absence of information is NOT a false fact \
— simply omit it.
- Assign a calibrated confidence in [0,1]: 0.9+ for explicit text/clear symbols, \
0.6-0.85 for strong visual inference, below 0.6 for uncertain guesses.
- Prefer precision over recall. A missed fact is recoverable by a human; a \
hallucinated predicate corrupts the compliance report.
"""

TEXT_PROMPT = """Below is the extracted text of one or more plan-set sheets \
(cover sheet, general notes, structural notes, schedules, or Title-24 energy \
forms). Extract every CRC-relevant fact as canonical predicates with the verbatim \
supporting quote, the page number, and a confidence. Also fill any project \
metadata you can read into project_updates."""

# Per-sheet-type guidance for the vision pass. Keyed to the highest-impact
# predicates in the rule corpus.
VISION_PROMPTS = {
    "floor_plan": (
        "This is a FLOOR PLAN. Identify: rooms and which are bedrooms; whether a "
        "garage is attached vs detached; the dwelling/garage separation wall and "
        "the door between them; stairs; emergency escape/rescue openings (egress "
        "windows) in bedrooms; smoke and carbon-monoxide alarm symbols (check the "
        "legend); fuel-burning appliances (furnace, water heater, range); EV "
        "charging in the garage; habitable attic/basement."
    ),
    "elevation": (
        "This is an ELEVATION. Identify: number of stories; roof covering type and "
        "fire class; decks, porches, balconies, or exterior stairs; foam plastic / "
        "exterior insulation callouts; chimneys and fireplaces; exterior wall "
        "finish."
    ),
    "section": (
        "This is a building SECTION. Identify: wall and roof assemblies; insulation "
        "type and thickness (note foam plastic and spray foam, with thickness); "
        "foundation type; framing materials; habitable attic; deck/stair "
        "construction."
    ),
    "foundation_plan": (
        "This is a FOUNDATION PLAN. Identify: concrete vs other foundation; "
        "continuous footings; stem walls; anchor bolts and hold-downs; frost line / "
        "footing depth callouts; slab-on-grade vs crawlspace."
    ),
    "framing_plan": (
        "This is a FRAMING / STRUCTURAL PLAN. Identify: wood wall framing; braced "
        "wall lines and braced wall panels; bracing method tags (CS-WSP, WSP, "
        "etc.); shear walls; hold-downs and anchor bolts; engineered members."
    ),
    "roof_plan": (
        "This is a ROOF PLAN. Identify: roof covering and fire class; roof-mounted "
        "PV / solar panels and whether they sit on or above the roof covering; "
        "roof penetrations; ventilation."
    ),
    "site_plan": (
        "This is a SITE PLAN. Identify: detached accessory structures; anything "
        "within 10 ft of the building; wildland-urban-interface / fire hazard "
        "severity zone notes; flood hazard area; setbacks."
    ),
    "detail": (
        "This is a DETAIL sheet. Identify any code-relevant assemblies: "
        "dwelling/garage separation, foam plastic protection, anchor bolts, "
        "fire-rated assemblies, deck/stair construction, foundation details."
    ),
    "electrical_plan": (
        "This is an ELECTRICAL PLAN. Identify: smoke/CO alarms; EV charging "
        "circuits in the garage; service equipment."
    ),
    "plumbing_mechanical": (
        "This is a PLUMBING/MECHANICAL PLAN. Identify: fuel-burning appliances; "
        "water heaters; HVAC equipment locations."
    ),
}
VISION_DEFAULT = (
    "Identify any CRC-relevant facts visible on this sheet (building type, "
    "construction, fire protection, egress, structural, foundation, or site "
    "features) as canonical predicates."
)

RECONCILE_PROMPT = """You are reconciling candidate facts extracted from \
different sheets of one plan set. Some predicates were asserted on some sheets \
and contradicted on others, or had low confidence.

For each conflict, decide the correct value using source reliability: explicit \
structural/general notes and schedules outrank a single visual inference; a \
labeled symbol outranks an unlabeled guess; higher-confidence evidence wins. \
Produce the final reconciled fact set: predicates (asserted, true), \
false_predicates (explicitly contradicted), and the merged project metadata. \
Only include predicates from the canonical vocabulary."""
