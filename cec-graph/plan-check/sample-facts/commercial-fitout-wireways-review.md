# Plan-Check Review — 500 Industrial Pkwy, Sacramento, CA 95814

**Project type:** commercial tenant improvement  
**Scope:** feeder and branch-circuit distribution in an exposed warehouse fit-out  
**Occupancy:** F-1 / B  

## Summary

- **24** rules fired
- **24** compliance chains (`0` multi-rule, `24` singleton, `0` cross-pack)
- **2** unique standards required
- **64** evidence items to verify

## Chain Index

| # | Cite | Title | Rules | Standards | Cross-pack |
|---|---|---|---|---|---|
| 1 | `378.56` | Keep splices accessible and within 75 percent fill | 1 | 0 |  |
| 2 | `386.56` | Limit splices and taps in surface metal raceway | 1 | 0 |  |
| 3 | `388.56` | Limit splices and taps in surface nonmetallic raceway | 1 | 0 |  |
| 4 | `386.10` | Limit surface metal raceway to permitted uses | 1 | 0 |  |
| 5 | `392.18` | Install cable tray as complete, accessible system | 1 | 0 |  |
| 6 | `388.12` | Prohibit surface nonmetallic raceway in unsuitable cond | 1 | 0 |  |
| 7 | `388.10` | Limit surface nonmetallic raceway to permitted uses | 1 | 0 |  |
| 8 | `378.12` | Prohibit nonmetallic wireway in unsuitable locations | 1 | 0 |  |
| 9 | `378.10` | Limit nonmetallic wireway to permitted uses | 1 | 0 |  |
| 10 | `392.20` | Separate over-1000V cables and group parallel conductor | 1 | 0 |  |
| 11 | `386.30` | Support surface metal raceway per manufacturer instruct | 1 | 0 |  |
| 12 | `392.80` | Determine conductor ampacity per cable tray rules | 1 | 0 |  |
| 13 | `392.22` | Limit number/fill of cables in cable tray | 1 | 1 |  |
| 14 | `380.12` | Prohibit multioutlet assembly in unsuitable conditions | 1 | 0 |  |
| 15 | `392.100` | Construct cable trays with adequate strength and smooth | 1 | 0 |  |
| 16 | `380.10` | Limit multioutlet assembly to dry locations | 1 | 0 |  |
| 17 | `392.10` | Use cable tray only for permitted wiring methods | 1 | 1 |  |
| 18 | `392.12` | Prohibit cable tray in hoistways or where damaged | 1 | 0 |  |
| 19 | `392.30` | Secure and support cable trays, cables, and conductors | 1 | 0 |  |
| 20 | `378.120` | Mark wireway with manufacturer and interior area | 1 | 0 |  |
| 21 | `386.12` | Prohibit surface metal raceway in unsuitable conditions | 1 | 0 |  |
| 22 | `378.30` | Support nonmetallic wireway at required intervals | 1 | 0 |  |
| 23 | `386.22` | Limit conductors to raceway design number | 1 | 0 |  |
| 24 | `378.22` | Limit conductor fill to 20 percent | 1 | 0 |  |

---
# Compliance Chains


## Chain: `378.56` — Keep splices accessible and within 75 percent fill

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 2
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `378.56` — Keep splices accessible and within 75 percent fill

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Ensure splices remain accessible and do not overfill the wireway.

**Triggered by:**
  - `is_nonmetallic_wireway` ✓
  - `contains_splices_or_taps` ✓

**Requires:**
  - **type**: splice_limit
  - **splices_must_be_accessible**: True
  - **max_fill_at_splice_point_percent**: 75
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[378.56]** Detail showing splice/tap locations accessible after installation
  - [ ] **[378.56]** Fill calculation at splice points showing conductors + splices <= 75% of area

---

## Chain: `386.56` — Limit splices and taps in surface metal raceway

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 3
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `386.56` — Limit splices and taps in surface metal raceway

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Ensure accessible covers and 75 percent fill limit at splice points, or splice in boxes.

**Triggered by:**
  - `is_surface_metal_raceway` ✓
  - `contains_splices_or_taps` ✓

**Requires:**
  - **type**: splice_limit
  - **splices_permitted_only_with_removable_accessible_cover**: True
  - **max_fill_at_splice_point_percent**: 75
  - **splices_without_removable_cover_only_in_boxes**: True
  - **type_fc_cable_taps_per**: 322.56(B)
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[386.56]** Detail showing removable cover accessible after installation at splice locations
  - [ ] **[386.56]** Fill calculation at splice points <= 75% of area
  - [ ] **[386.56]** Box detail where raceway lacks removable cover

---

## Chain: `388.56` — Limit splices and taps in surface nonmetallic raceway

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 3
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `388.56` — Limit splices and taps in surface nonmetallic raceway

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Ensure openable accessible covers and 75 percent fill limit at splices, or splice in boxes.

**Triggered by:**
  - `is_surface_nonmetallic_raceway` ✓
  - `contains_splices_or_taps` ✓

**Requires:**
  - **type**: splice_limit
  - **splices_permitted_only_with_cover_openable_in_place_accessible**: True
  - **max_fill_at_splice_point_percent**: 75
  - **splices_without_openable_cover_only_in_boxes**: True
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[388.56]** Detail showing cover capable of being opened in place and accessible after installation
  - [ ] **[388.56]** Fill calculation at splice points <= 75% of area
  - [ ] **[388.56]** Box detail where raceway lacks openable cover

---

## Chain: `386.10` — Limit surface metal raceway to permitted uses

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 3
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `386.10` — Limit surface metal raceway to permitted uses

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Restrict surface metal raceway to dry locations and specifically permitted special conditions.

**Triggered by:**
  - `is_surface_metal_raceway` ✓

**Requires:**
  - **type**: use_limitation
  - **permitted_uses**: dry_locations, class_i_division_2_per_501_10_b_3, under_raised_floors_per_645_5_e_2, unbroken_extension_through_dry_walls_partitions_floors_with_access_both_sides
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[386.10]** Location classification confirming dry location use
  - [ ] **[386.10]** Pass-through detail showing unbroken length and conductor access on both sides
  - [ ] **[386.10]** Documentation for special uses (Class I Div 2 or raised-floor)

---

## Chain: `392.18` — Install cable tray as complete, accessible system

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 4
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `392.18` — Install cable tray as complete, accessible system

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Ensure continuity, completion before cabling, exposure/accessibility, and proper marking of high-voltage trays.

**Triggered by:**
  - `is_cable_tray` ✓

**Requires:**
  - **type**: installation_condition
  - **complete_system_with_maintained_continuity**: True
  - **run_completed_before_cable_installation**: True
  - **exposed_and_accessible_except_through_walls_per_392_18_d**: True
  - **pass_through_partitions_per**: 300.21
  - **over_600v_warning_marking_max_interval_ft**: 10
  - **tested_per**: 

**Exceptions:**
  - **ex1**: rule_does_not_apply (✗ inactive)

### Evidence Checklist

  - [ ] **[392.18]** Tray installation detail showing complete system with maintained electrical continuity and support
  - [ ] **[392.18]** Confirmation each run is completed before cables are installed
  - [ ] **[392.18]** Over-600 V warning notices placed at intervals not exceeding 10 ft where applicable
  - [ ] **[392.18]** Wall/floor penetration detail per 300.21

---

## Chain: `388.12` — Prohibit surface nonmetallic raceway in unsuitable conditions

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 3
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `388.12` — Prohibit surface nonmetallic raceway in unsuitable conditions

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Prevent use where concealment, damage, voltage, hoistway, hazard, or temperature conditions exceed the listing.

**Triggered by:**
  - `is_surface_nonmetallic_raceway` ✓

**Requires:**
  - **type**: use_prohibition
  - **prohibited_when**:
    - any_of: [{'is_concealed_not_permitted_by_388_10_2': True}, {'subject_to_severe_physical_damage': True}, {'voltage_>=_300v_and_not_listed_for_higher_voltage': True}, {'in_hoistway': True}, {'is_hazardous_classified_location': True}, {'ambient_temperature_exceeds_listed': True}, {'conductor_insulation_temp_exceeds_raceway_listing': True}]
  - **tested_per**: 

**Exceptions:**
  - **ex1**: rule_does_not_apply (✗ inactive)
  - **ex2**: rule_does_not_apply (✗ inactive)

### Evidence Checklist

  - [ ] **[388.12]** Location detail confirming no concealment, hoistway, or hazardous area
  - [ ] **[388.12]** Listing voltage rating where voltage between conductors is 300 V or more
  - [ ] **[388.12]** Conductor insulation and ambient temperature vs raceway listed ratings

---

## Chain: `388.10` — Limit surface nonmetallic raceway to permitted uses

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 2
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `388.10` — Limit surface nonmetallic raceway to permitted uses

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Restrict surface nonmetallic raceway to dry locations and unbroken dry pass-throughs.

**Triggered by:**
  - `is_surface_nonmetallic_raceway` ✓

**Requires:**
  - **type**: use_limitation
  - **permitted_uses**: dry_locations, unbroken_extension_through_dry_walls_partitions_floors_with_access_both_sides
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[388.10]** Location classification confirming dry location use
  - [ ] **[388.10]** Pass-through detail showing unbroken length and conductor access on both sides

---

## Chain: `378.12` — Prohibit nonmetallic wireway in unsuitable locations

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 3
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `378.12` — Prohibit nonmetallic wireway in unsuitable locations

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Prevent use of nonmetallic wireways where physical, thermal, environmental, or hazard conditions exceed their listing.

**Triggered by:**
  - `is_nonmetallic_wireway` ✓

**Requires:**
  - **type**: use_prohibition
  - **prohibited_when**:
    - any_of: [{'subject_to_physical_damage': True}, {'is_hazardous_classified_location': True}, {'exposed_to_sunlight_and_not_listed_for_sunlight': True}, {'ambient_temperature_outside_listed_range': True}, {'conductor_insulation_temp_exceeds_wireway_listing': True}]
  - **tested_per**: 

**Exceptions:**
  - **ex1**: rule_does_not_apply (✗ inactive)

### Evidence Checklist

  - [ ] **[378.12]** Location classification confirming no hazardous (classified) area or physical-damage exposure
  - [ ] **[378.12]** Listing mark for sunlight resistance where exposed to sun
  - [ ] **[378.12]** Conductor insulation temperature rating vs wireway listed temperature comparison

---

## Chain: `378.10` — Limit nonmetallic wireway to permitted uses

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 3
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `378.10` — Limit nonmetallic wireway to permitted uses

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Restrict nonmetallic wireways to the environments and configurations for which they are suited and identified.

**Triggered by:**
  - `is_nonmetallic_wireway` ✓

**Requires:**
  - **type**: use_limitation
  - **permitted_uses**: exposed_work_only_except_378_10_4, corrosive_environment_where_identified, wet_location_where_listed, extension_through_wall_unbroken_with_access_both_sides
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[378.10]** Plan/spec showing wireway run as exposed work
  - [ ] **[378.10]** Listing/identification mark for wet or corrosive use where applicable
  - [ ] **[378.10]** Detail showing unbroken length and conductor access on both sides at any wall pass-through

---

## Chain: `392.20` — Separate over-1000V cables and group parallel conductors

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 3
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `392.20` — Separate over-1000V cables and group parallel conductors

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Prevent unsafe mixing of voltage classes and current imbalance in paralleled single conductors.

**Triggered by:**
  - `is_cable_tray` ✓

**Requires:**
  - **type**: cable_installation
  - **over_1000v_with_under_1000v_in_same_tray_requires**:
    - any_of: [{'over_1000v_cables_are_type_mc': True}, {'solid_fixed_barrier_between_voltage_classes': True}]
  - **parallel_single_conductors_one_per_phase_neutral_grounded_per_group**: True
  - **single_conductors_securely_bound_in_circuit_groups**: True
  - **single_conductors_1_0_through_4_0_in_single_layer**: True
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[392.20]** Cable schedule showing over-1000 V cables are Type MC or separated by a solid fixed barrier
  - [ ] **[392.20]** Parallel conductor grouping detail (one per phase/neutral/grounded per group)
  - [ ] **[392.20]** Single-layer arrangement detail for 1/0 through 4/0 AWG single conductors

---

## Chain: `386.30` — Support surface metal raceway per manufacturer instructions

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 2
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `386.30` — Support surface metal raceway per manufacturer instructions

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Ensure raceway support follows the listed installation instructions.

**Triggered by:**
  - `is_surface_metal_raceway` ✓

**Requires:**
  - **type**: support_spacing
  - **support_per**: manufacturer_installation_instructions
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[386.30]** Manufacturer installation instructions showing support requirements
  - [ ] **[386.30]** Support layout consistent with manufacturer instructions

---

## Chain: `392.80` — Determine conductor ampacity per cable tray rules

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 3
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `392.80` — Determine conductor ampacity per cable tray rules

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Apply the correct ampacity tables and derating for cables installed in cable trays.

**Triggered by:**
  - `is_cable_tray` ✓

**Requires:**
  - **type**: ampacity
  - **multiconductor_2000v_or_less_per**: table_310_16, table_310_18
  - **covered_tray_over_6ft_solid_cover_max_percent_multiconductor**: 95
  - **single_conductor_600kcmil_and_larger_uncovered_max_percent**: 75
  - **single_conductor_1_0_to_500kcmil_uncovered_max_percent**: 65
  - **adjustment_factors_310_15_c_1_apply_only_to_multiconductor_over_3_ccc**: True
  - **tested_per**: 

**Exceptions:**
  - **ex1**: rule_does_not_apply (✗ inactive)

### Evidence Checklist

  - [ ] **[392.80]** Ampacity calculation citing the applicable Table 310.16/310.17/310.18/310.19 values
  - [ ] **[392.80]** Derating worksheet for covered trays (95%/70%/60% as applicable) and single-layer spacing
  - [ ] **[392.80]** Identification of current-carrying conductor counts for adjustment factor application

---

## Chain: `392.22` — Limit number/fill of cables in cable tray

**Rules:** 1  •  **Standards:** 1  •  **Evidence items:** 3
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `392.22` — Limit number/fill of cables in cable tray

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Prevent overfill and overheating by limiting cable fill per tray type and conductor size.

**Triggered by:**
  - `is_cable_tray` ✓

**Requires:**
  - **type**: fill_limit
  - **multiconductor_fill_per**: table_392_22_a
  - **ventilated_channel_fill_per**: table_392_22_a_5
  - **solid_channel_fill_per**: table_392_22_a_6
  - **single_conductor_fill_per**: table_392_22_b_1
  - **control_signal_only_ladder_vented_max_fill_percent**: 50
  - **control_signal_only_solid_bottom_max_fill_percent**: 40
  - **fill_calculated_per_divided_section_where_dividers_used**: True
  - **tested_per**: 

### Standards Required

  - `09_chapter_3_wiring_methods_and_materials_article_378_nonmetallic_wireways_article_table_392_22_a`

### Evidence Checklist

  - [ ] **[392.22]** Cable fill calculation per the applicable Table 392.22 column for tray type and cable size
  - [ ] **[392.22]** Single-layer arrangement detail for 4/0 AWG and larger cables
  - [ ] **[392.22]** Per-section fill calculation where dividers are used

---

## Chain: `380.12` — Prohibit multioutlet assembly in unsuitable conditions

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 3
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `380.12` — Prohibit multioutlet assembly in unsuitable conditions

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Prevent installation where concealment, damage, voltage, corrosion, or hazard conditions make the assembly unsafe.

**Triggered by:**
  - `is_multioutlet_assembly` ✓

**Requires:**
  - **type**: use_prohibition
  - **prohibited_when**:
    - any_of: [{'is_concealed_not_otherwise_permitted': True}, {'subject_to_severe_physical_damage': True}, {'voltage_>=_300v_and_metal_thickness_<_0.040_in': True}, {'subject_to_corrosive_vapors': True}, {'in_hoistway': True}, {'is_hazardous_classified_location': True}, {'is_cord_and_plug_connected': True}]
  - **tested_per**: 

**Exceptions:**
  - **ex1**: rule_does_not_apply (✗ inactive)

### Evidence Checklist

  - [ ] **[380.12]** Location/installation detail showing no concealment, hoistway, or corrosive vapor exposure
  - [ ] **[380.12]** Metal thickness >= 0.040 in. where voltage between conductors is 300 V or more
  - [ ] **[380.12]** Connection method confirming not cord-and-plug connected

---

## Chain: `392.100` — Construct cable trays with adequate strength and smooth edges

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 3
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `392.100` — Construct cable trays with adequate strength and smooth edges

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Ensure trays support wiring without damaging insulation and resist corrosion.

**Triggered by:**
  - `is_cable_tray` ✓

**Requires:**
  - **type**: construction
  - **adequate_strength_and_rigidity**: True
  - **no_sharp_edges_burrs_or_projections**: True
  - **corrosion_resistant_ferrous_protected_per**: 300.6
  - **has_side_rails_or_equivalent**: True
  - **nonmetallic_trays_flame_retardant**: True
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[392.100]** Tray construction/listing showing strength, rigidity, and smooth edges
  - [ ] **[392.100]** Corrosion protection documentation for ferrous trays per 300.6
  - [ ] **[392.100]** Flame-retardant material confirmation for nonmetallic trays

---

## Chain: `380.10` — Limit multioutlet assembly to dry locations

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 1
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `380.10` — Limit multioutlet assembly to dry locations

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Restrict multioutlet assemblies to dry locations for which they are suited.

**Triggered by:**
  - `is_multioutlet_assembly` ✓

**Requires:**
  - **type**: use_limitation
  - **permitted_uses**: dry_locations_only
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[380.10]** Location classification confirming dry location for the assembly run

---

## Chain: `392.10` — Use cable tray only for permitted wiring methods

**Rules:** 1  •  **Standards:** 1  •  **Evidence items:** 3
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `392.10` — Use cable tray only for permitted wiring methods

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Restrict cable tray contents to permitted wiring methods and require sunlight-resistant cables where sun-exposed.

**Triggered by:**
  - `is_cable_tray` ✓

**Requires:**
  - **type**: use_limitation
  - **permitted_wiring_methods_per**: table_392_10_a
  - **single_insulated_conductors_only_per**: 392.10(B)(1)
  - **sunlight_exposed_cables_must_be_sunlight_resistant**: True
  - **trays_and_fittings_identified_for_use**: True
  - **tested_per**: 

### Standards Required

  - `09_chapter_3_wiring_methods_and_materials_article_378_nonmetallic_wireways_article_table_392_10_a`

### Evidence Checklist

  - [ ] **[392.10]** Cable/raceway schedule confirming only Table 392.10(A) wiring methods are in the tray
  - [ ] **[392.10]** Sunlight-resistance marking for cables exposed to direct sun
  - [ ] **[392.10]** Listing/identification of trays and fittings for the intended use

---

## Chain: `392.12` — Prohibit cable tray in hoistways or where damaged

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 1
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `392.12` — Prohibit cable tray in hoistways or where damaged

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Prevent cable tray use where physical damage or hoistway conditions are unsafe.

**Triggered by:**
  - `is_cable_tray` ✓

**Requires:**
  - **type**: use_prohibition
  - **prohibited_when**:
    - any_of: [{'in_hoistway': True}, {'subject_to_severe_physical_damage': True}]
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[392.12]** Location detail confirming tray is not in a hoistway and not subject to severe physical damage

---

## Chain: `392.30` — Secure and support cable trays, cables, and conductors

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 3
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `392.30` — Secure and support cable trays, cables, and conductors

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Ensure trays and their contents are supported per instructions and transitions are protected.

**Triggered by:**
  - `is_cable_tray` ✓

**Requires:**
  - **type**: support_spacing
  - **trays_supported_per**: installation_instructions
  - **cables_fastened_to_transverse_members_in_non_horizontal_runs**: True
  - **support_at_raceway_entries_to_prevent_stress**: True
  - **max_unsupported_transition_distance_ft**: 6
  - **cable_ties_listed_and_identified**: True
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[392.30]** Tray support layout per manufacturer installation instructions
  - [ ] **[392.30]** Detail showing cables fastened to transverse members in non-horizontal runs
  - [ ] **[392.30]** Transition detail showing distance to raceway/equipment not exceeding 6 ft with conductors secured and protected

---

## Chain: `378.120` — Mark wireway with manufacturer and interior area

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 2
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `378.120` — Mark wireway with manufacturer and interior area

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Ensure identification and fill information remains visible for inspection.

**Triggered by:**
  - `is_nonmetallic_wireway` ✓

**Requires:**
  - **type**: marking
  - **marking_visible_after_installation**: manufacturer_name_or_trademark, interior_cross_sectional_area_sq_in
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[378.120]** Product marking showing manufacturer name/trademark visible after installation
  - [ ] **[378.120]** Marking showing interior cross-sectional area in square inches

---

## Chain: `386.12` — Prohibit surface metal raceway in unsuitable conditions

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 2
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `386.12` — Prohibit surface metal raceway in unsuitable conditions

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Prevent use where damage, voltage/thickness, corrosion, hoistway, or concealment conditions are unsafe.

**Triggered by:**
  - `is_surface_metal_raceway` ✓

**Requires:**
  - **type**: use_prohibition
  - **prohibited_when**:
    - any_of: [{'subject_to_severe_physical_damage_unless_approved': True}, {'voltage_>=_300v_and_metal_thickness_<_0.040_in': True}, {'subject_to_corrosive_vapors': True}, {'in_hoistway': True}, {'is_concealed_not_permitted_by_386_10': True}]
  - **tested_per**: 

**Exceptions:**
  - **ex1**: rule_does_not_apply (✗ inactive)

### Evidence Checklist

  - [ ] **[386.12]** Metal thickness >= 0.040 in. where voltage between conductors is 300 V or more
  - [ ] **[386.12]** Location detail confirming no concealment, hoistway, or corrosive vapor exposure

---

## Chain: `378.30` — Support nonmetallic wireway at required intervals

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 3
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `378.30` — Support nonmetallic wireway at required intervals

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Maintain mechanical integrity and prevent sag or joint failure.

**Triggered by:**
  - `is_nonmetallic_wireway` ✓

**Requires:**
  - **type**: support_spacing
  - **horizontal_support_interval_max_ft**: 3
  - **horizontal_absolute_max_between_supports_ft**: 10
  - **horizontal_support_at_each_end_or_joint**: True
  - **vertical_support_interval_max_ft**: 4
  - **vertical_max_joints_between_supports**: 1
  - **rigid_joints_required**: True
  - **listed_for_other_intervals_permitted**: True
  - **tested_per**: 

**Exceptions:**
  - **ex1**: rule_does_not_apply (✗ inactive)

### Evidence Checklist

  - [ ] **[378.30]** Support layout showing horizontal intervals <= 3 ft (<= 10 ft absolute) and at each end/joint
  - [ ] **[378.30]** Vertical support detail at intervals <= 4 ft with no more than one joint between supports
  - [ ] **[378.30]** Listing documentation where alternative support intervals are used

---

## Chain: `386.22` — Limit conductors to raceway design number

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 3
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `386.22` — Limit conductors to raceway design number

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Prevent overfill by limiting conductor count to the raceway's designed number.

**Triggered by:**
  - `is_surface_metal_raceway` ✓

**Requires:**
  - **type**: fill_limit
  - **max_conductors**: number_for_which_raceway_designed
  - **adjustment_factors_310_15_c_1_not_apply_when**:
    - all_of: [{'raceway_cross_sectional_area_>_4_sq_in': True}, {'current_carrying_conductors_<=_30': True}, {'conductor_fill_<=_20_percent': True}]
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[386.22]** Raceway design/listing showing maximum number of conductors
  - [ ] **[386.22]** Conductor schedule confirming count within designed number
  - [ ] **[386.22]** Documentation supporting non-application of 310.15(C)(1) where claimed

---

## Chain: `378.22` — Limit conductor fill to 20 percent

**Rules:** 1  •  **Standards:** 0  •  **Evidence items:** 3
**Pack:** Nonmetallic Wireways — Article 378

### Rules


### `378.22` — Limit conductor fill to 20 percent

**Jurisdiction:** model_NEC   
**Severity:** required  
**Intent:** Prevent overheating and damage by limiting cross-sectional fill of the wireway.

**Triggered by:**
  - `is_nonmetallic_wireway` ✓

**Requires:**
  - **type**: fill_limit
  - **max_conductor_fill_percent**: 20
  - **basis**: interior_cross_sectional_area_at_any_cross_section
  - **exclude_from_current_carrying**: signaling_circuit_conductors, motor_starter_starting_duty_conductors
  - **adjustment_factors_apply**: 310.15(C)(1)
  - **tested_per**: 

### Evidence Checklist

  - [ ] **[378.22]** Conductor fill calculation showing total conductor area <= 20% of interior cross-sectional area
  - [ ] **[378.22]** Wireway interior cross-sectional area from listing/marking
  - [ ] **[378.22]** Conductor schedule identifying any excluded signaling or motor-starting conductors

---

# Appendix

## Fact Decomposition

- **Declared facts:** 10
- **Derived facts:** 0 (via aliases, compounds, patterns)
- **Final fact set:** 10 (1 iterations to fixed point)

## Asserted Facts

```
contains_splices_or_taps
in_dry_location
is_cable_tray
is_dry_location
is_exposed
is_multioutlet_assembly
is_nonmetallic_wireway
is_surface_metal_raceway
is_surface_nonmetallic_raceway
location_dry
```

## Skipped Rules

**66** rules evaluated but did not fire (conditions did not match the project facts).

---

_Generated by the CRC plan-check pipeline (graphify → rule extraction → fact decomposition → engine → chain analysis → report rendering)._