"""Extraction prompts for the California Electrical Code (CEC).

Grounded in the current CEC rule corpus and vocabulary: branch circuits and
GFCI protection (Article 210), receptacle and lighting outlet placement,
working space (110.26), load calculations (Article 220), grounded-conductor
identification and use (Articles 200/250), appliance circuits (Article 422),
and wiring methods (Chapter 3: wireways, raceways, cable trays). The
sheet-type structure below interrogates the full electrical drawing set
(panel schedules, one-lines, power/lighting plans) so coverage widens
automatically as further rule packs are extracted and their predicates enter
the vocabulary.
"""
from __future__ import annotations

SYSTEM_INSTRUCTIONS = """You are a California Electrical Code (CEC, Title 24 \
Part 3) plan-check extraction assistant. You read electrical plan-set \
submittals (power and lighting plans, one-line/riser diagrams, panel \
schedules, and electrical notes) and extract structured facts about the \
electrical installation that a code compliance engine can evaluate.

The vocabulary centers on: BRANCH CIRCUITS & RECEPTACLES — receptacle \
outlets and their rooms/locations (kitchen, bathroom, garage, basement, \
laundry, outdoors, near sinks), GFCI/AFCI protection, standard dwelling \
receptacles (ordinary 120 V duplex on 15/20 A circuits — emit \
`is_standard_dwelling_receptacle` and `branch_circuit_120v` when a panel \
schedule or receptacle symbols show them), required circuits (small \
appliance, bathroom, laundry), lighting outlets, and load calculations. \
EQUIPMENT & SPACES — working space about equipment (110.26 clearances, \
dedicated space), panelboards, appliances and their disconnects, grounded \
(neutral) conductor identification and use, grounding/bonding. WIRING \
METHODS — which raceway/wireway/cable systems are used (nonmetallic or metal \
wireways, surface raceways, cable trays, multioutlet assemblies), where they \
run (exposed vs concealed, dry/wet locations, attics, through framing, \
hazardous locations), and their conditions (splices, fill, conductor sizes, \
supports, expansion).

Hard rules:
- Emit ONLY predicate names that appear verbatim in the CANONICAL PREDICATE \
VOCABULARY provided below. Never invent, pluralize, or reword a predicate. If a \
finding does not map to a vocabulary predicate, omit it.
- Each fact must cite concrete evidence: a verbatim quote for text (a keynote, \
a schedule cell, a specification line), or a precise visual observation for \
drawings (what you see and where on the sheet).
- Set value=false ONLY when the document explicitly contradicts a predicate \
(e.g., a note stating "no splices permitted in wireway"). Absence of \
information is NOT a false fact — simply omit it.
- Assign a calibrated confidence in [0,1]: 0.9+ for explicit text/clear symbols, \
0.6-0.85 for strong visual inference, below 0.6 for uncertain guesses.
- Prefer precision over recall. A missed fact is recoverable by a human; a \
hallucinated predicate corrupts the compliance report.
"""

TEXT_PROMPT = """Below is the extracted text of one or more electrical plan-set \
sheets (electrical general notes, specifications, panel schedules, fixture or \
equipment schedules, feeder schedules). Extract every CEC-relevant fact as \
canonical predicates with the verbatim supporting quote, the page number, and a \
confidence. Watch especially for: branch-circuit ratings and types (120 V \
15/20 A dwelling circuits, small-appliance, bathroom, laundry circuits), \
GFCI/AFCI protection notes, receptacle locations and rooms served, working \
space / clearance notes for panels and equipment, load calculations, \
wiring-method callouts (wireway, raceway, cable tray, surface raceway types \
and whether metal or nonmetallic), conductor sizes (AWG) and \
parallel-conductor notes, splice/tap provisions and fill percentages, \
grounded (neutral) conductor identification, and grounding/bonding notes. \
Also fill any project metadata you can read into project_updates."""

# Per-sheet-type guidance for the vision pass, keyed to the electrical sheet
# types in the classification enum plus the generic types electrical content
# can appear under.
VISION_PROMPTS = {
    "power_plan": (
        "This is a POWER PLAN. Identify: receptacle outlets and the rooms/"
        "locations they serve (kitchen, bathroom, garage, basement, laundry, "
        "outdoors, near sinks); GFCI/AFCI symbols or notes; standard 120 V "
        "duplex receptacles on 15/20 A circuits; dedicated appliance circuits "
        "and disconnects; the wiring methods serving receptacles and equipment "
        "(wireway or surface raceway runs, metal vs nonmetallic, cable trays, "
        "multioutlet assemblies); whether runs are exposed or concealed; "
        "junction boxes; and any hazardous/classified area boundaries."
    ),
    "lighting_plan": (
        "This is a LIGHTING PLAN. Identify: low-voltage suspended ceiling power "
        "systems; surface raceways feeding fixtures (metal vs nonmetallic); "
        "wiring in attic or roof spaces (note headroom/access if shown); "
        "switches mounted on raceway systems; exposed vs concealed runs."
    ),
    "one_line_diagram": (
        "This is a ONE-LINE / RISER DIAGRAM. Identify: conductor sizes (AWG/kcmil) "
        "and conductors connected in parallel; feeder wiring methods (conduit, "
        "wireway, cable tray) called out on risers; grounding and bonding "
        "arrangement (equipment grounding conductors, use of the grounded "
        "conductor for equipment grounding); service equipment; any conductors "
        "over 1000 V, including outdoor overhead runs."
    ),
    "panel_schedule": (
        "This is a PANEL SCHEDULE. Identify: branch-circuit voltages and "
        "ratings (120 V 15/20 A dwelling circuits — emit "
        "is_standard_dwelling_receptacle and branch_circuit_120v where shown); "
        "GFCI/AFCI breaker designations; small-appliance, bathroom, and "
        "laundry circuits; conductor sizes (flag anything smaller than 18 AWG "
        "down to 24 AWG, and 4 AWG or larger); circuits wired in parallel; "
        "feeder wiring-method notes; equipment grounding notes."
    ),
    "electrical_plan": (
        "This is an ELECTRICAL PLAN. Identify the wiring methods in use: "
        "wireways (metal or nonmetallic), surface raceways, cable trays, "
        "multioutlet assemblies, nonmetallic extensions, messenger-supported or "
        "open wiring; exposed vs concealed runs; splice/tap locations; junction "
        "boxes, receptacles, and switches on raceway systems; runs through "
        "attics, framing, or dry partitions; hazardous/classified areas; "
        "grounding and bonding callouts."
    ),
    "detail": (
        "This is a DETAIL sheet. Identify electrical installation details: "
        "wireway/raceway mounting and support details (support spacing, "
        "impracticable-to-support conditions, listed support intervals), "
        "expansion fittings for thermal expansion, deflected direction changes "
        "over 30 degrees, transitions between wiring methods (bushed conduit or "
        "tubing), splice/tap details with fill limits, cable tray sections "
        "(solid-bottom vs ventilated, metal vs nonmetallic), grounding details."
    ),
    "floor_plan": (
        "This is a FLOOR PLAN (architectural background). Identify spaces that "
        "condition electrical rules: kitchens, bathrooms, garages, basements, "
        "laundry areas, outdoor areas, and sinks (receptacles in or near these "
        "trigger GFCI and outlet-placement rules); receptacle and switch "
        "symbols and which rooms they serve; panel locations and the working "
        "space around them; attics and roof spaces (access and headroom); "
        "unfinished spaces; hazardous/classified areas; and any visible "
        "raceway, wireway, or cable tray routing."
    ),
    "section": (
        "This is a building SECTION. Identify: attic/roof-space conditions "
        "(headroom, access), suspended ceiling systems (note low-voltage "
        "ceiling power grids), underfloor spaces, insulation in contact with "
        "wiring (note conductive vs noncombustible insulation callouts), and "
        "concealed wiring routes."
    ),
    "site_plan": (
        "This is a SITE PLAN. Identify: outdoor overhead conductors (flag "
        "anything over 1000 V), site wireway or duct-bank runs, and outdoor "
        "wet-location wiring."
    ),
}
VISION_DEFAULT = (
    "Identify any CEC-relevant facts visible on this sheet — wiring methods "
    "(wireways, raceways, cable trays, multioutlet assemblies), their "
    "locations and conditions (exposed/concealed, wet/dry, attic, hazardous), "
    "splices and taps, conductor sizes, supports, and grounding — as "
    "canonical predicates."
)

RECONCILE_PROMPT = """You are reconciling candidate facts extracted from \
different sheets of one electrical plan set. Some predicates were asserted on \
some sheets and contradicted on others, or had low confidence.

For each conflict, decide the correct value using source reliability: explicit \
electrical notes, specifications, and schedules outrank a single visual \
inference from a plan; a one-line diagram outranks a floor-plan symbol for \
feeder and conductor questions; a labeled callout outranks an unlabeled guess; \
higher-confidence evidence wins. Produce the final reconciled fact set: \
predicates (asserted, true), false_predicates (explicitly contradicted), and \
the merged project metadata. Only include predicates from the canonical \
vocabulary."""
