truckee-sfr-review.md# Plan-Check Review — 12345 Ridge Road, Truckee, CA

**Project type:** single-family detached dwelling  
**Scope:** new construction  
**Occupancy:** R-3  
**SDC:** D1  
**FHSZ:** Very High  
**Wind speed:** 110 mph  
**Climate zone:** 16  

## Summary

- **22** rules fired
- **11** compliance chains (`6` multi-rule, `5` singleton, `2` cross-pack)
- **11** unique standards required
- **76** evidence items to verify

## Chain Index

| # | Cite | Title | Rules | Standards | Cross-pack |
|---|---|---|---|---|---|
| 1 | `R602.10.9.1` | In SDC D0-D2 braced wall panel footings shall meet Sect | 5 | 0 |  |
| 2 | `R324.4.1.2` | Rooftop PV designed for component-and-cladding wind loa | 3 | 3 |  |
| 3 | `R602.10.2` | Build braced wall panels as full-height segments withou | 3 | 1 | 🔗 |
| 4 | `R902.1.1` | Class A roof required in Fire Hazard Severity Zones | 2 | 3 |  |
| 5 | `R902.4` | Rooftop-mounted PV panel systems — UL 2703 fire classif | 2 | 1 | 🔗 |
| 6 | `R337.5.1` | WUI roofing general — Class A in FHSZ | 2 | 2 |  |
| 7 | `R337.9` | WUI decking walking surface within 10 ft of building | 1 | 4 |  |
| 8 | `R324.4.3` | Rooftop PV roof penetrations flashed and sealed | 1 | 0 |  |
| 9 | `R316.3` | Foam plastic surface burning characteristics | 1 | 1 |  |
| 10 | `R602.10.4` | Construct intermittent and continuously sheathed braced | 1 | 0 |  |
| 11 | `R337.7` | WUI exterior covering scope (parent) | 1 | 0 |  |

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
  - [ ] **[R301.2.2]** Seismic Design Category determination per Section R301.2.2.1
  - [ ] **[R301.2.2]** Identification of building type (detached 1-2 family dwelling vs. townhouse)
  - [ ] **[R301.2.2]** If SDC E: engineered design per California Building Code or reclassification documentation per R301.2.2.1.2
  - [ ] **[R301.2.2]** Statement that seismic provisions of this code are applied
  - [ ] **[R403.1.6.1]** Anchor-bolt schedule with plate washers (3x3x0.229) called out along all required braced wall lines
  - [ ] **[R403.1.6.1]** Foundation plan showing interior braced wall and bearing-wall anchor bolt spacing <= 6 ft (or 4 ft if >2 stories) and within 12 in. of plate ends
  - [ ] **[R403.1.6.1]** Stepped cripple wall detail per R602.11.2 if applicable
  - [ ] **[R403.1.6.1]** Force-transfer detail at continuous wood foundations matching R602.11.1 capacity
  - [ ] **[R602.10.8.1]** Foundation anchorage detail at each braced wall panel matching R602.11.1 (plate washers, anchor bolts)
  - [ ] **[R602.10.8.1]** Top-plate splice detail showing 8-16d face nails on each side of the splice
  - [ ] **[R602.10.8.1]** Bracing plan note pointing to R602.10.8.1 in SDC D0/D1/D2

---

## Chain: `R324.4.1.2` — Rooftop PV designed for component-and-cladding wind loads

**Rules:** 3  •  **Standards:** 3  •  **Evidence items:** 9
**Pack:** PV Systems & Roof Coverings

### Rules


### `R324.4.1.1` — Roof load cases for portions covered and not covered by PV

**Jurisdiction:** model_IRC   
**Severity:** required  
**Intent:** Defines the specific load combinations the roof must be designed for so PV addition does not under-stress areas with PV (snow case) or leave bare areas under-designed for live/snow load.

**Triggered by:**
  - `is_rooftop_mounted_pv_system` ✓

**Requires:**
  - **type**: structural_load_cases
  - **uncovered_roof_designed_for**: dead_load_per_R301_4, roof_load_per_R301_6
  - **pv_covered_roof_designed_for_load_cases**: {'case': 1, 'combination': 'dead_load_including_pv_panel_weight + snow_load', 'snow_load_per': 'table_r301_2'}, {'case': 2, 'combination': 'dead_load_excluding_pv_panel_weight + greater_of(roof_live_load, snow_load)', 'live_or_snow_per': 'R301.6'}

### `R324.4.1` — Rooftop PV systems and their supporting roofs designed for applicable gravity loads

**Jurisdiction:** model_IRC   
**Severity:** required  
**Intent:** Ensures both the PV array structure and the roof underneath can carry the weight and gravity loads that come with adding PV.

**Triggered by:**
  - `is_rooftop_mounted_pv_system` ✓

**Requires:**
  - **type**: structural_design
  - **pv_system_supports_itself_and_gravity_loads_per**: Chapter 3
  - **supporting_roof_designed_per**: chapter_8

### `R324.4.1.2` — Rooftop PV designed for component-and-cladding wind loads

**Jurisdiction:** model_IRC   
**Severity:** required  
**Intent:** Ensures rooftop PV panels and supports resist wind uplift using component-and-cladding pressures, adjusted for site height and exposure.

**Triggered by:**
  - `is_rooftop_mounted_pv_system` ✓

**Requires:**
  - **type**: wind_load_design
  - **component_and_cladding_loads_per**: table_r301_2_1_1
  - **height_and_exposure_adjustment_per**: Table R301.2.1(2)

### Standards Required

  - `chapter_8`
  - `table_r301_2`
  - `table_r301_2_1_1`

### Evidence Checklist

  - [ ] **[R324.4.1.2]** Wind-load calculations for the PV array using Table R301.2.1(1) C&C loads
  - [ ] **[R324.4.1.2]** Site exposure category and mean roof height documented in calculations
  - [ ] **[R324.4.1.2]** Attachment / anchor capacity calculations stamped by an engineer
  - [ ] **[R324.4.1.1]** Structural calculations showing both load cases for PV-covered roof areas
  - [ ] **[R324.4.1.1]** Structural calculations showing dead + roof live/snow for non-PV-covered roof areas
  - [ ] **[R324.4.1.1]** Reference to Table R301.2 climatic snow load on plans
  - [ ] **[R324.4.1]** Structural calculations for the PV racking/support system signed by a licensed engineer
  - [ ] **[R324.4.1]** Roof framing calculations or analysis demonstrating capacity to carry added PV dead load
  - [ ] **[R324.4.1]** Plan note referencing Chapter 3 (gravity loads) and Chapter 8 (roof-ceiling construction)

---

## Chain: `R602.10.2` — Build braced wall panels as full-height segments without offsets and place them per Section R602.10

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

### Standards Required

  - `table_r602_3_1`

### Evidence Checklist

  - [ ] **[R602.10.2]** Wall elevations showing each braced wall panel from top plate to bottom plate without offsets
  - [ ] **[R602.10.2]** Bracing plan citing Section R602.10.4 method for each panel
  - [ ] **[R602.10.2]** Confirmation that panel placement complies with R602.10.2.2 / R602.10.2.2.1
  - [ ] **[R602.10.9]** Foundation/floor-framing detail at each braced wall panel matching one of the permitted support types
  - [ ] **[R602.10.9]** Engineered design for raised-floor post/pier supports
  - [ ] **[R602.10.9]** Reinforcement schedule per Figure R602.10.9 for short masonry/concrete stem walls
  - [ ] **[R602.10.9]** Statement that ABW and PFH panels are not attached to masonry stem walls
  - [ ] **[R602.10.8]** Braced wall panel connection details showing rim joist, band joist, end joist, or blocking along the full panel length above and below
  - [ ] **[R602.10.8]** Plate-to-framing nailing call-outs taken from Table R602.3(1)
  - [ ] **[R602.10.8]** Where joists are parallel and a parallel member cannot be located above/below the panel, details of full-depth blocking at 16 inches o.c. on each side
  - [ ] **[R602.10.8]** For panels bearing on concrete or masonry, anchor bolt schedule and detail per Section R403.1.6

---

## Chain: `R902.1.1` — Class A roof required in Fire Hazard Severity Zones

**Rules:** 2  •  **Standards:** 3  •  **Evidence items:** 8
**Pack:** WUI Fire Compliance & PV Fire Class

### Rules


### `R324.4.2` — Rooftop PV fire classification matches roof assembly

**Jurisdiction:** model_IRC   
**Severity:** required  
**Intent:** Ensure rooftop-mounted photovoltaic systems do not degrade the fire classification of the roof they are installed on.

**Triggered by:**
  - `is_pv_rooftop_mounted` ✓
  - `installed_on_or_above_roof_covering` ✓

**Requires:**
  - **type**: pv_fire_classification
  - **must_match**: fire_classification_of_roof_assembly_per_r902
  - **tested_per**: std_ul_2703
  - **depends_on_section**: section_r902

### `R902.1.1` — Class A roof required in Fire Hazard Severity Zones

**Jurisdiction:** California 🇺🇸  
**Severity:** required  
**Intent:** Require Class A roof coverings on all new structures and substantial roof replacements within Fire Hazard Severity Zones to defend against ember and direct flame exposure.

**Triggered by:**
  - `in_fire_hazard_severity_zone` ✓
  - `is_new_structure` ✓

**Requires:**
  - **type**: fire_rated_roof_covering
  - **minimum_class**: A
  - **fire_retardant**: True
  - **tested_per**: std_astm_e108, std_ul_790

**Exceptions:**
  - **ex1**: rule_does_not_apply (✗ inactive)

### Standards Required

  - `std_astm_e108`
  - `std_ul_2703`
  - `std_ul_790`

### Evidence Checklist

  - [ ] **[R324.4.2]** PV module/system listing showing UL 2703 fire classification (Class A, B, or C)
  - [ ] **[R324.4.2]** Roof assembly fire classification (Class A in FHSZ per R902.1.1)
  - [ ] **[R324.4.2]** Cross-check showing PV class is at least equal to roof class
  - [ ] **[R324.4.2]** Manufacturer installation instructions and product listing
  - [ ] **[R902.1.1]** FHSZ determination for project address (CAL FIRE map screenshot or jurisdiction declaration)
  - [ ] **[R902.1.1]** Roof covering listing showing ASTM E108 or UL 790 Class A result
  - [ ] **[R902.1.1]** For replacements: roof area calc showing % replaced in past 12 months
  - [ ] **[R902.1.1]** Confirmation jurisdiction has not adopted SFM model ordinance per Gov Code 51189

---

## Chain: `R902.4` — Rooftop-mounted PV panel systems — UL 2703 fire classification

**Rules:** 2  •  **Standards:** 1  •  **Evidence items:** 8
**Cross-pack chain** spanning: PV Systems & Roof Coverings, WUI Fire Compliance & PV Fire Class

### Rules


### `R902.4` — Rooftop-mounted PV panel systems — UL 2703 fire classification

**Jurisdiction:** model_IRC   
**Severity:** required  
**Intent:** Require rooftop-mounted PV panel systems to be tested/listed/identified for a fire classification (UL 2703) and installed per their listing where the law or lot-line proximity requires it.

**Triggered by:**
  - `is_pv_rooftop_mounted` ✓
  - `installed_on_or_above_roof_covering` ✓

**Requires:**
  - **type**: rooftop_pv_fire_classification
  - **tested_listed_identified_per**: std_ul_2703
  - **installed_per**: manufacturer instructions and listing
  - **class_required_when**: jurisdictions designated by law OR roof edge < 3 ft (914 mm) from a lot line
  - **minimum_class**: C

### `R902.4` — Rooftop-mounted PV systems: tested and identified to UL 2703

**Jurisdiction:** California 🇺🇸  
**Severity:** required  
**Intent:** Requires rooftop-mounted PV (mounted on or above the roof covering) to carry a UL 2703 fire-classification listing and to be installed per the listing.

**Triggered by:**
  - `is_rooftop_mounted_pv_system` ✓

**Requires:**
  - **type**: fire_classification
  - **tested_listed_and_identified_to**: std_ul_2703
  - **install_per_manufacturer_and_listing**: True
  - **fire_classes_recognized**: A, B, C
  - **mandatory_class_a_b_or_c_when**:
    - any_of: ['jurisdiction_designated_by_law', 'edge_of_roof_<3_ft_from_lot_line']
  - **tested_per**: std_ul_2703

### Standards Required

  - `std_ul_2703`

### Evidence Checklist

  - [ ] **[R902.4]** PV system UL 2703 listing showing fire classification
  - [ ] **[R902.4]** Manufacturer's installation instructions and listing details
  - [ ] **[R902.4]** Site plan showing lot line distance to roof edge
  - [ ] **[R902.4]** Local jurisdiction PV-class requirement reference (if applicable)
  - [ ] **[R902.4]** PV system UL 2703 listing/label and fire-classification documentation
  - [ ] **[R902.4]** Manufacturer installation instructions consistent with the listing
  - [ ] **[R902.4]** Site plan dimensioning roof edge to lot lines
  - [ ] **[R902.4]** Plan note declaring jurisdictional fire class requirement, if any

---

## Chain: `R337.5.1` — WUI roofing general — Class A in FHSZ

**Rules:** 2  •  **Standards:** 2  •  **Evidence items:** 6
**Pack:** WUI Fire Compliance & PV Fire Class

### Rules


### `R902.1.3` — WUI roofing additional compliance with R337.5

**Jurisdiction:** California 🇺🇸  
**Severity:** required  
**Intent:** Layer WUI-specific roofing requirements (R337.5) on top of base roof fire-classification rules for buildings located in WUI fire areas.

**Triggered by:**
  - `in_wildland_urban_interface_fire_area` ✓

**Requires:**
  - **type**: additional_section_compliance
  - **must_also_comply_with**: r337_5, r337_5_1, r337_5_2, r337_5_3

### `R337.5.1` — WUI roofing general — Class A in FHSZ

**Jurisdiction:** California 🇺🇸  
**Severity:** required  
**Intent:** Require Class A roof assemblies in WUI Fire Hazard Severity Zones to resist burning ember and direct flame exposure on the roof.

**Triggered by:**
  - `in_wildland_urban_interface_fire_area` ✓
  - `in_fire_hazard_severity_zone` ✓

**Requires:**
  - **type**: fire_rated_roof_covering
  - **minimum_class**: A
  - **tested_per**: std_astm_e108, std_ul_790
  - **must_also_comply_with**: section_r902
  - **installation**: per listing and manufacturer's instructions

### Standards Required

  - `std_astm_e108`
  - `std_ul_790`

### Evidence Checklist

  - [ ] **[R337.5.1]** Roof covering listing showing ASTM E108 or UL 790 Class A result
  - [ ] **[R337.5.1]** FHSZ determination for project address
  - [ ] **[R337.5.1]** Manufacturer installation instructions matched to permit drawings
  - [ ] **[R337.5.1]** Roofing assembly approval documentation
  - [ ] **[R902.1.3]** WUI Fire Area determination for project address
  - [ ] **[R902.1.3]** Cross-reference to R337.5 compliance documentation (Class A roof, cap sheet, valley flashing)

---

## Chain: `R337.9` — WUI decking walking surface within 10 ft of building

**Rules:** 1  •  **Standards:** 4  •  **Evidence items:** 4
**Pack:** WUI Fire Compliance & PV Fire Class

### Rules


### `R337.9` — WUI decking walking surface within 10 ft of building

**Jurisdiction:** California 🇺🇸  
**Severity:** required  
**Intent:** Prevent decks/porches/balconies/stairs near a building from igniting under burning brand exposure and contributing to building ignition.

**Triggered by:**
  - `in_wildland_urban_interface_fire_area` ✓
  - `is_deck_porch_balcony_or_stair_walking_surface` ✓
  - `any_portion_within_10_ft_of_building` ✓

**Requires:**
  - **type**: deck_walking_surface
  - **any_of**: {'method': 'tested_per_astm_e2632_and_astm_e2726_meeting_r337_9_4', 'tested_per': ['std_astm_e2632', 'std_astm_e2726'], 'peak_heat_release_max_kw_per_ft2': 25}, {'method': 'ignition_resistant_material_per_r337_9_4'}, {'method': 'tested_per_sfm_12_7a_4_and_r337_4_3', 'tested_per': ['std_sfm_12_7a_4']}, {'method': 'exterior_fire_retardant_treated_wood'}, {'method': 'noncombustible_material'}, {'method': 'tested_per_sfm_12_7a_4a_with_noncombustible_or_ir_walls'}, {'method': 'tested_per_astm_e2632_with_noncombustible_or_ir_walls'}
  - **flashing_required_at_deck_to_wall**: min 6-inch (150 mm) metal flashing applied vertically

**Exceptions:**
  - **ex1**: wall_material_may_be_any_complying_chapter_material (✗ inactive)

### Standards Required

  - `std_astm_e2632`
  - `std_astm_e2726`
  - `std_astm_e84`
  - `std_sfm_12_7a_4`

### Evidence Checklist

  - [ ] **[R337.9]** Decking product test report (ASTM E2632 + ASTM E2726, SFM 12-7A-4, or alternates)
  - [ ] **[R337.9]** Conditions of acceptance verification (peak HRR <= 25 kW/ft^2; no sustained combustion)
  - [ ] **[R337.9]** Deck plan showing surfaces within 10 ft of building
  - [ ] **[R337.9]** Detail showing 6-inch vertical metal flashing at deck-to-wall intersections

---

## Chain: `R324.4.3` — Rooftop PV roof penetrations flashed and sealed

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 3
**Pack:** WUI Fire Compliance & PV Fire Class

### Rules


### `R324.4.3` — Rooftop PV roof penetrations flashed and sealed

**Jurisdiction:** model_IRC   
**Severity:** required  
**Intent:** Prevent water intrusion and maintain roof assembly integrity at PV mounting penetrations.

**Triggered by:**
  - `is_pv_rooftop_mounted` ✓
  - `creates_roof_penetration` ✓

**Requires:**
  - **type**: roof_penetration_flashing_and_sealing
  - **must_comply_with**: Chapter 9

### Evidence Checklist

  - [ ] **[R324.4.3]** Mounting detail drawings showing flashing at every roof penetration
  - [ ] **[R324.4.3]** Manufacturer-approved flashing/sealant product cut sheets
  - [ ] **[R324.4.3]** Inspection sign-off for roof penetration weatherproofing

---

## Chain: `R316.3` — Foam plastic surface burning characteristics

**Rules:** 1  •  **Standards:** 1  •  **Evidence items:** 4
**Pack:** WUI Fire Compliance & PV Fire Class

### Rules


### `R316.3` — Foam plastic surface burning characteristics

**Jurisdiction:** model_IRC   
**Severity:** required  
**Intent:** Limit flame spread and smoke development of foam plastic used in building construction so that it does not contribute to rapid interior fire growth.

**Triggered by:**
  - `uses_foam_plastic_in_building_construction` ✓

**Requires:**
  - **type**: foam_plastic_surface_burning_characteristics
  - **flame_spread_index_max**: 75
  - **smoke_developed_index_max**: 450
  - **tested_per**: std_astm_e84
  - **alternate_tested_per**: UL 723
  - **thickness_rules**:
    - <=4_in: test at maximum thickness and density intended for use
    - >4_in: test at 4-inch thickness; end use approved per R316.6
  - **loose_fill_treatment**: tested as board stock

**Exceptions:**
  - **ex1**: alternative_thresholds: flame_spread_index_max=25, smoke_developed_index_max=450 at 4-inch test thickness; must be separated from interior by 1/2-inch gypsum or NFPA 275 tested material (✓ ACTIVE — rule may be suppressed)
  - **ex2**: rule_does_not_apply (✗ inactive)

### Standards Required

  - `std_astm_e84`

### Evidence Checklist

  - [ ] **[R316.3]** Foam plastic product spec sheet listing flame spread index and smoke-developed index values
  - [ ] **[R316.3]** ASTM E84 or UL 723 test report at intended thickness and density
  - [ ] **[R316.3]** Manufacturer's listing showing thickness, density, and end-use configuration
  - [ ] **[R316.3]** If thicker than 4 in: R316.6 specific approval documentation

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

## Chain: `R337.7` — WUI exterior covering scope (parent)

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 2
**Pack:** WUI Fire Compliance & PV Fire Class

### Rules


### `R337.7` — WUI exterior covering scope (parent)

**Jurisdiction:** California 🇺🇸  
**Severity:** required  
**Intent:** Scope rule: triggers exterior covering compliance for wall coverings/assemblies, eaves, soffits, porch ceilings, floor projections, and underfloor areas in WUI areas.

**Triggered by:**
  - `in_wildland_urban_interface_fire_area` ✓

**Requires:**
  - **type**: scope_trigger
  - **covered_elements**: exterior_wall_coverings, exterior_wall_assemblies, exposed_underside_of_roof_eave_overhangs, exposed_underside_of_roof_eave_soffits, exposed_underside_of_exterior_porch_ceilings, exposed_underside_of_floor_projections, exterior_underfloor_areas

**Exceptions:**
  - **ex1**: rule_does_not_apply (✗ inactive)
  - **ex2**: rule_does_not_apply (✗ inactive)
  - **ex3**: covered_under_r337_9_only (✗ inactive)

### Evidence Checklist

  - [ ] **[R337.7]** Building elevations identifying exterior covering material at each face
  - [ ] **[R337.7]** Schedule of exterior assemblies cross-referenced to R337.7.3 / R337.7.4 compliance

---

# Appendix

## Fact Decomposition

- **Declared facts:** 41
- **Derived facts:** 9 (via aliases, compounds, patterns)
- **Final fact set:** 50 (2 iterations to fixed point)

## Asserted Facts

```
any_portion_within_10_ft_of_building
creates_roof_penetration
frost_line_depth_>=_36_in
garage_has_ev_charging
has_anchor_bolts
has_attached_garage
has_bedroom
has_braced_wall_lines
has_carbon_monoxide_alarm_required
has_continuous_footing
has_dwelling_garage_separation
has_emergency_escape_opening_in_bedroom
has_fuel_burning_appliance
has_habitable_attic
has_rooftop_pv
in_fhsz
in_fire_hazard_severity_zone
in_flood_hazard_area
in_sdc_c_d0_d1_or_d2
in_sdc_d0_d1
in_sdc_d0_d1_or_d2
in_sdc_d0_or_d1
in_sdc_d1
in_seismic_design_category_c_d0_d1_or_d2
in_seismic_design_category_d0_d1_or_d2
in_seismic_design_category_d0_or_d1
in_seismic_design_category_d1
in_wildland_urban_interface_fire_area
in_wui
in_wui_fire_area
installed_on_or_above_roof_covering
is_braced_wall_panel
is_concrete_foundation
is_deck_porch_balcony_or_stair_walking_surface
is_detached_dwelling
is_detached_one_or_two_family_dwelling
is_detached_one_or_two_family_dwelling_in_sdc_d0_d1_or_d2
is_in_seismic_design_category_d1
is_new_building
is_new_structure
is_one_or_two_family_dwelling
is_pv_rooftop_mounted
is_rooftop_mounted_pv_system
is_spray_foam_plastic_insulation
is_wood_framed
is_wood_light_frame
is_wood_light_frame_in_sdc_d0_d1_or_d2
is_wood_wall_framing
thickness_>_4_in
uses_foam_plastic_in_building_construction
```

## Skipped Rules

**241** rules evaluated but did not fire (conditions did not match the project facts).

---

_Generated by the CRC plan-check pipeline (graphify → rule extraction → fact decomposition → engine → chain analysis → report rendering)._
