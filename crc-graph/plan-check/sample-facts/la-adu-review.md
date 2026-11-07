# Plan-Check Review — 1234 Hyperion Ave, Los Angeles, CA 90027

**Project type:** detached accessory dwelling unit (ADU)  
**Scope:** new construction on existing single-family lot  
**Occupancy:** R-3  
**SDC:** D1  
**FHSZ:** None (urban infill, outside FHSZ)  
**Wind speed:** 95 mph  
**Climate zone:** 9  

## Summary

- **11** rules fired
- **5** compliance chains (`2` multi-rule, `3` singleton, `1` cross-pack)
- **3** unique standards required
- **37** evidence items to verify

## Chain Index

| # | Cite | Title | Rules | Standards | Cross-pack |
|---|---|---|---|---|---|
| 1 | `R602.10.9.1` | In SDC D0-D2 braced wall panel footings shall meet Sect | 5 | 0 |  |
| 2 | `R602.10.9` | Support braced wall panels on cantilevered joists, post | 3 | 1 | 🔗 |
| 3 | `R902.1.2` | Class C roof required in all other areas | 1 | 2 |  |
| 4 | `R303` | Scope: Light, ventilation and heating for habitable spa | 1 | 0 |  |
| 5 | `R602.10.4` | Construct intermittent and continuously sheathed braced | 1 | 0 |  |

---
# Compliance Chains


## Chain: `R602.10.9.1` — In SDC D0-D2 braced wall panel footings shall meet Section R403.1.2

**Rules:** 5  •  **Standards:** 0  •  **Evidence items:** 18
**Pack:** Wind/Seismic Bracing & SDC Provisions

### Rules


### `R602.11.1` — In SDC D0-D2 (and SDC C townhouses) provide 0.229 x 3 x 3 plate washers at all sill anchor bolts (slotted hole permitted within limits)

**Jurisdiction:** model_IRC   
**Severity:** required  
**Intent:** Spread the anchor-bolt clamp force across the sill plate so it does not split or shear, and allow practical slotted holes only within strict size limits.

**Triggered by:**
  - `in_seismic_design_category_d0_d1_or_d2` ✓

**Requires:**
  - **type**: plate_washers
  - **min_thickness_in**: 0.229
  - **min_size_in**: 3 x 3
  - **between_sill_plate_and_nut**: True
  - **approved_anchor_straps_alternative**: True
  - **diagonally_slotted_hole_max_extra_width_in**: 0.1875
  - **diagonally_slotted_hole_max_length_in**: 1.75
  - **standard_cut_washer_required_between_plate_washer_and_nut_when_slotted**: True
  - **tested_per**: 

### `R602.10.8.1` — In SDC D0-D2 fasten braced wall panels to required foundations per R602.11.1 and use 8-16d top plate splice

**Jurisdiction:** model_IRC   
**Severity:** required  
**Intent:** Tie braced wall panels into the foundation with the higher-seismic anchorage and preserve top plate continuity to act as a chord/collector.

**Triggered by:**
  - `in_seismic_design_category_d0_d1_or_d2` ✓
  - `is_braced_wall_panel` ✓

**Requires:**
  - **type**: connections
  - **panel_to_required_foundation_per**: section_r602_11_1
  - **top_plate_lap_splice_face_nails_each_side**: 8
  - **top_plate_lap_splice_nail_size**: 16d
  - **tested_per**: 

### `R301.2.2` — Apply IRC seismic provisions to townhouses and dwellings in SDC C/D0/D1/D2; SDC E uses the California Building Code

**Jurisdiction:** California 🇺🇸  
**Severity:** required  
**Intent:** Define which buildings are bound by the IRC seismic provisions and require engineered (CBC) design for SDC E unless reclassified.

**Triggered by:**
  - `is_detached_one_or_two_family_dwelling_in_sdc_d0_d1_or_d2` ✓

**Requires:**
  - **type**: scope_reference
  - **comply_with_seismic_requirements_of**: this_code
  - **tested_per**: 

**Exceptions:**
  - **ex1**: use_california_building_code_for_seismic_design_unless_reclassified_per_r301_2_2_1 (✗ inactive)

### `R403.1.6.1` — In SDC C (townhouses) and SDC D0/D1/D2 add plate washers, tighter interior anchor-bolt spacing, and 4-ft anchor spacing >2 stories

**Jurisdiction:** California 🇺🇸  
**Severity:** required  
**Intent:** Provide hold-down-grade sill anchorage so braced wall panel sills transfer seismic shear to the foundation without splitting and so multi-story buildings get extra anchor density.

**Triggered by:**
  - `is_wood_light_frame_in_sdc_d0_d1_or_d2` ✓

**Requires:**
  - **type**: anchorage
  - **in_addition_to**: section_r403_1_6
  - **plate_washers_per**: section_r602_11_1
  - **plate_washers_required_along**: full_length_of_required_braced_wall_lines_unless_approved_anchor_straps_used
  - **interior_braced_wall_plate_anchor_bolt_max_spacing_in**: 72
  - **interior_braced_wall_plate_anchor_within_in_of_plate_ends**: 12
  - **interior_bearing_wall_sole_plate_anchor_bolt_max_spacing_in**: 72
  - **interior_bearing_wall_sole_plate_anchor_within_in_of_plate_ends**: 12
  - **max_anchor_bolt_spacing_in_for_buildings_over_two_stories_in**: 48
  - **stepped_cripple_walls_per**: section_r602_11_2
  - **continuous_wood_foundations_force_transfer_per**: section_r602_11_1, table_r602_3_1_braced_wall_panel_to_floor_fastening
  - **tested_per**: 

### `R602.10.9.1` — In SDC D0-D2 braced wall panel footings shall meet Section R403.1.2

**Jurisdiction:** model_IRC   
**Severity:** required  
**Intent:** Force the higher-seismic continuous-foundation rule to the panel level so each braced wall panel sits on a continuous concrete or fully grouted masonry footing.

**Triggered by:**
  - `in_seismic_design_category_d0_d1_or_d2` ✓
  - `is_braced_wall_panel` ✓

**Requires:**
  - **type**: support
  - **footing_per_section**: r403_1_2
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[R602.10.9.1]** Foundation plan showing every required braced wall panel supported on a continuous footing complying with R403.1.2
  - [ ] **[R602.10.9.1]** Plan note linking R602.10.9.1 to the foundation plan
  - [ ] **[R602.10.9.1]** Documentation of any R403.1.2 exception used (two-story with cripple wall <= 4 ft, etc.)
  - [ ] **[R602.11.1]** Hardware schedule listing 3x3x0.229 plate washers (or approved anchor straps) at every required braced wall line anchor
  - [ ] **[R602.11.1]** Detail showing slot dimensions <= bolt+3/16" wide and <= 1-3/4" long with cut washer above plate washer
  - [ ] **[R602.11.1]** Plan note linking R602.11.1 to the SDC of the project
  - [ ] **[R602.11.1]** Manufacturer spec sheet for anchor straps if used as alternative
  - [ ] **[R602.10.8.1]** Foundation anchorage detail at each braced wall panel matching R602.11.1 (plate washers, anchor bolts)
  - [ ] **[R602.10.8.1]** Top-plate splice detail showing 8-16d face nails on each side of the splice
  - [ ] **[R602.10.8.1]** Bracing plan note pointing to R602.10.8.1 in SDC D0/D1/D2
  - [ ] **[R301.2.2]** Seismic Design Category determination per Section R301.2.2.1
  - [ ] **[R301.2.2]** Identification of building type (detached 1-2 family dwelling vs. townhouse)
  - [ ] **[R301.2.2]** If SDC E: engineered design per California Building Code or reclassification documentation per R301.2.2.1.2
  - [ ] **[R301.2.2]** Statement that seismic provisions of this code are applied
  - [ ] **[R403.1.6.1]** Anchor-bolt schedule with plate washers (3x3x0.229) called out along all required braced wall lines
  - [ ] **[R403.1.6.1]** Foundation plan showing interior braced wall and bearing-wall anchor bolt spacing <= 6 ft (or 4 ft if >2 stories) and within 12 in. of plate ends
  - [ ] **[R403.1.6.1]** Stepped cripple wall detail per R602.11.2 if applicable
  - [ ] **[R403.1.6.1]** Force-transfer detail at continuous wood foundations matching R602.11.1 capacity

---

## Chain: `R602.10.9` — Support braced wall panels on cantilevered joists, post/pier, or stem walls only as R602.10.9 permits

**Rules:** 3  •  **Standards:** 1  •  **Evidence items:** 11
**Cross-pack chain** spanning: Wind/Seismic Bracing & SDC Provisions, Wood Wall Fastening & Stud Sizing

### Rules


### `R602.10.2` — Build braced wall panels as full-height segments without offsets and place them per Section R602.10

**Jurisdiction:** model_IRC   
**Severity:** required  
**Intent:** Guarantee each braced wall panel is a continuous full-height shear element so the prescriptive lengths and capacities apply.

**Triggered by:**
  - `is_braced_wall_panel` ✓

**Requires:**
  - **type**: geometry
  - **panel_full_height**: True
  - **no_vertical_or_horizontal_offsets**: True
  - **construction_methods_per_section**: section_r602_10_4
  - **panel_locations_per_section**: section_r602_10_2_2
  - **tested_per**: 

### `R602.10.8` — Connect braced wall panels to floor framing or foundation with rim/blocking and Table R602.3(1) fastening

**Jurisdiction:** model_IRC   
**Severity:** required  
**Intent:** Provide a continuous shear-and-uplift load path from each braced wall panel into the floor diaphragm or foundation by requiring rim joists, end joists, or blocking and prescribed nailing.

**Triggered by:**
  - `is_braced_wall_panel` ✓

**Requires:**
  - **type**: load_path_connection
  - **case_joists_perpendicular_to_panel**:
    - provide_along_entire_panel_length: rim_joist_or_band_joist_or_blocking
    - per_figure: FIGURE R602.10.8(1)
    - fasten_top_and_bottom_plates_to_framing_per_table: TABLE R602.3(1)
  - **case_joists_parallel_to_panel**:
    - provide_directly_above_and_below_panel: rim_joist_or_end_joist_or_other_parallel_framing_member
    - per_figure: FIGURE R602.10.8(2)
    - if_parallel_member_cannot_be_located_directly_above_and_below: {'provide': 'full_depth_blocking_at_16_inch_spacing_between_parallel_members_each_side_of_panel', 'per_figure': 'FIGURE R602.10.8(2)'}
    - fasten_blocking_and_wall_plates_per_table: TABLE R602.3(1)
  - **case_connection_to_concrete_or_masonry**:
    - per_section: R403.1.6
  - **tested_per**: 

### `R602.10.9` — Support braced wall panels on cantilevered joists, post/pier, or stem walls only as R602.10.9 permits

**Jurisdiction:** model_IRC   
**Severity:** required  
**Intent:** Restrict the kinds of substructure that can carry a braced wall panel so the panel's overturning and shear can be resisted by the supporting element.

**Triggered by:**
  - `is_braced_wall_panel` ✓

**Requires:**
  - **type**: support
  - **permitted_supports**: cantilevered_floor_joists_per_section_r502_3_3, raised_floor_post_or_pier_designed_per_accepted_engineering_practice, masonry_stem_walls_<=_48_in_long_reinforced_per_figure_r602_10_9, masonry_stem_walls_>_48_in_long_per_section_r403_1, concrete_stem_walls_<=_48_in_long_>_12_in_tall_<_6_in_thick_reinforced_per_figure_r602_10_9
  - **abw_or_pfh_to_masonry_stem_walls**: not_permitted
  - **tested_per**: 

### Standards Required

  - `table_r602_3_1`

### Evidence Checklist

  - [ ] **[R602.10.9]** Foundation/floor-framing detail at each braced wall panel matching one of the permitted support types
  - [ ] **[R602.10.9]** Engineered design for raised-floor post/pier supports
  - [ ] **[R602.10.9]** Reinforcement schedule per Figure R602.10.9 for short masonry/concrete stem walls
  - [ ] **[R602.10.9]** Statement that ABW and PFH panels are not attached to masonry stem walls
  - [ ] **[R602.10.2]** Wall elevations showing each braced wall panel from top plate to bottom plate without offsets
  - [ ] **[R602.10.2]** Bracing plan citing Section R602.10.4 method for each panel
  - [ ] **[R602.10.2]** Confirmation that panel placement complies with R602.10.2.2 / R602.10.2.2.1
  - [ ] **[R602.10.8]** Braced wall panel connection details showing rim joist, band joist, end joist, or blocking along the full panel length above and below
  - [ ] **[R602.10.8]** Plate-to-framing nailing call-outs taken from Table R602.3(1)
  - [ ] **[R602.10.8]** Where joists are parallel and a parallel member cannot be located above/below the panel, details of full-depth blocking at 16 inches o.c. on each side
  - [ ] **[R602.10.8]** For panels bearing on concrete or masonry, anchor bolt schedule and detail per Section R403.1.6

---

## Chain: `R902.1.2` — Class C roof required in all other areas

**Rules:** 1  •  **Standards:** 2  •  **Evidence items:** 3
**Pack:** WUI Fire Compliance & PV Fire Class

### Rules


### `R902.1.2` — Class C roof required in all other areas

**Jurisdiction:** California 🇺🇸  
**Severity:** required  
**Intent:** Set baseline Class C fire-retardant roof covering requirement for new structures and substantial replacements outside FHSZ.

**Triggered by:**
  - `is_new_structure` ✓

**Requires:**
  - **type**: fire_rated_roof_covering
  - **minimum_class**: C
  - **fire_retardant**: True
  - **tested_per**: std_astm_e108, std_ul_790

### Standards Required

  - `std_astm_e108`
  - `std_ul_790`

### Evidence Checklist

  - [ ] **[R902.1.2]** FHSZ determination showing project is NOT in FHSZ
  - [ ] **[R902.1.2]** Roof covering listing showing ASTM E108 or UL 790 Class C (or higher) result
  - [ ] **[R902.1.2]** For replacements: roof area calc showing % replaced in past 12 months

---

## Chain: `R303` — Scope: Light, ventilation and heating for habitable space

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 2
**Pack:** Habitable Space & Fire Separation

### Rules


### `R303` — Scope: Light, ventilation and heating for habitable space

**Jurisdiction:** model_IRC   
**Severity:** required  
**Intent:** Establishes the umbrella trigger for natural/mechanical light and ventilation and heating requirements applicable to habitable rooms and dwelling units.

**Triggered by:**
  - `is_dwelling_unit` ✓

**Requires:**
  - **type**: scope_pointer
  - **subordinate_sections**: R303.1, R303.2, R303.3, R303.4, R303.5, R303.6, R303.7, R303.8, R303.9, R303.10
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[R303]** Code analysis identifying which rooms are habitable per the Chapter 2 definition
  - [ ] **[R303]** Room finish/use schedule distinguishing habitable rooms from bathrooms, closets, halls, storage and utility spaces

---

## Chain: `R602.10.4` — Construct intermittent and continuously sheathed braced wall panels per Table R602.10.4

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 3
**Pack:** Wind/Seismic Bracing & SDC Provisions

### Rules


### `R602.10.4` — Construct intermittent and continuously sheathed braced wall panels per Table R602.10.4

**Jurisdiction:** model_IRC   
**Severity:** required  
**Intent:** Bind each prescriptive method (LIB, DWB, WSP, SFB, GB, PBS, PCP, HPS, ABW, PFH, PFG, BV-WSP, CS-WSP, CS-G, CS-PF, CS-SFB) to a specific material, thickness and fastening so the assumed lateral capacity is realized.

**Triggered by:**
  - `is_braced_wall_panel` ✓

**Requires:**
  - **type**: construction_methods
  - **methods_per_table**: table_r602_10_4
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[R602.10.4]** Method label for each panel cross-referenced to Table R602.10.4 row
  - [ ] **[R602.10.4]** Sheathing/material thickness, fastener type and spacing on the wall details
  - [ ] **[R602.10.4]** Notes prohibiting adhesive attachment in SDC C, D0, D1 and D2 (per Table R602.10.4 note a)

---

# Appendix

## Fact Decomposition

- **Declared facts:** 26
- **Derived facts:** 9 (via aliases, compounds, patterns)
- **Final fact set:** 35 (2 iterations to fixed point)

## Asserted Facts

```
has_anchor_bolts
has_bedroom
has_braced_wall_lines
has_carbon_monoxide_alarm_required
has_continuous_footing
has_emergency_escape_opening_in_bedroom
has_fuel_burning_appliance
has_habitable_space
has_smoke_alarm_required
in_sdc_c_d0_d1_or_d2
in_sdc_d0_d1
in_sdc_d0_d1_or_d2
in_sdc_d0_or_d1
in_sdc_d1
in_seismic_design_category_c_d0_d1_or_d2
in_seismic_design_category_d0_d1_or_d2
in_seismic_design_category_d0_or_d1
in_seismic_design_category_d1
is_accessory_dwelling_unit
is_braced_wall_panel
is_concrete_foundation
is_detached_dwelling
is_detached_one_or_two_family_dwelling
is_detached_one_or_two_family_dwelling_in_sdc_d0_d1_or_d2
is_dwelling_unit
is_in_seismic_design_category_d1
is_new_building
is_new_structure
is_one_or_two_family_dwelling
is_one_story
is_slab_on_grade
is_wood_framed
is_wood_light_frame
is_wood_light_frame_in_sdc_d0_d1_or_d2
is_wood_wall_framing
```

## Skipped Rules

**252** rules evaluated but did not fire (conditions did not match the project facts).

---

_Generated by the CRC plan-check pipeline (graphify → rule extraction → fact decomposition → engine → chain analysis → report rendering)._