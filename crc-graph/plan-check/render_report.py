"""
Render a plan-check report as Markdown.

Inputs:
  facts.json        - declared/expanded project facts
  rules.json        - all_rules.json (for full rule lookup)
  violations.json   - engine output (which rules fired)
  chains.json       - chain output (chains + sub-clusters + deduplicated evidence)

Output:
  <project>-review.md - top-to-bottom plan-check report

Layout:
  1. Header (project metadata, summary)
  2. Compliance summary table (chains by community)
  3. Per-chain sections:
       - Chain title + spanned communities
       - Trigger conditions (predicate set that matched)
       - Sub-clusters if present
       - Per-rule cards: cite, title, verbatim, requires, exceptions
       - Terminal standards stack
       - Evidence checklist (markdown checkboxes)
  4. Appendix: declared facts, derived facts, skipped rules
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def normalize(p: str) -> str:
    s = p.lower().strip()
    s = re.sub(r'[\s\-]+', '_', s)
    s = re.sub(r'_+', '_', s)
    return s


def render_clause(clause, indent=0) -> str:
    """Render an applies_when clause as a human-readable line."""
    pad = '  ' * indent
    if not isinstance(clause, dict):
        return f'{pad}{clause}'
    p = clause.get('predicate')
    if p == 'any_of':
        children = clause.get('of') or clause.get('clauses') or []
        return f'{pad}**any of:**\n' + '\n'.join(render_clause(c, indent + 1) for c in children)
    if p == 'all_of':
        children = clause.get('of') or clause.get('clauses') or []
        return f'{pad}**all of:**\n' + '\n'.join(render_clause(c, indent + 1) for c in children)
    if p == 'not':
        children = clause.get('of') or clause.get('clauses') or []
        if children:
            return f'{pad}**not:**\n' + '\n'.join(render_clause(c, indent + 1) for c in children)
        return f'{pad}**not** (empty)'
    if p:
        return f'{pad}- `{p}`'
    return f'{pad}- _(unrecognized clause)_'


def matched_predicates(applies_when, facts: set[str]) -> list[str]:
    """Recursively find atomic predicates in applies_when that are in facts."""
    matched = []

    def walk(c):
        if not isinstance(c, dict):
            return
        p = c.get('predicate')
        if p in ('any_of', 'all_of', 'not'):
            for child in (c.get('of') or c.get('clauses') or []):
                walk(child)
        elif p:
            if normalize(p) in facts:
                matched.append(p)

    for c in applies_when or []:
        walk(c)
    return matched


def render_rule_card(rule: dict, facts: set[str]) -> str:
    """Render one rule as a Markdown card with cite, verbatim, requires, evidence."""
    out = []
    cite = rule.get('cite', '?')
    title = rule.get('title', '')
    out.append(f'\n### `{cite}` — {title}\n')

    if rule.get('jurisdiction'):
        jur = rule['jurisdiction']
        emoji = '🇺🇸' if jur == 'California' else ''
        out.append(f'**Jurisdiction:** {jur} {emoji}  ')
    if rule.get('severity'):
        out.append(f'**Severity:** {rule["severity"]}  ')
    if rule.get('intent'):
        out.append(f'**Intent:** {rule["intent"]}\n')

    if rule.get('verbatim'):
        out.append(f'\n> {rule["verbatim"]}\n')

    out.append('**Triggered by:**')
    matched = matched_predicates(rule.get('applies_when', []), facts)
    if matched:
        for m in matched:
            out.append(f'  - `{m}` ✓')
    else:
        out.append('  - _(matched via composite expansion or no explicit trigger)_')

    requires = rule.get('requires')
    if requires and isinstance(requires, dict):
        out.append('\n**Requires:**')
        for k, v in requires.items():
            if isinstance(v, list):
                out.append(f'  - **{k}**: {", ".join(map(str, v))}')
            elif isinstance(v, dict):
                out.append(f'  - **{k}**:')
                for k2, v2 in v.items():
                    out.append(f'    - {k2}: {v2}')
            else:
                out.append(f'  - **{k}**: {v}')

    if rule.get('exceptions'):
        out.append('\n**Exceptions:**')
        for ex in rule['exceptions']:
            preds = matched_predicates(ex.get('applies_when', []), facts)
            satisfied = '✓ ACTIVE — rule may be suppressed' if preds else '✗ inactive'
            out.append(f'  - **{ex.get("id","?")}**: {ex.get("effect","?")} ({satisfied})')

    return '\n'.join(out)


def render_chain(chain: dict, rules_by_id: dict, facts: set[str]) -> str:
    """Render one chain section."""
    out = []
    head = chain['head']
    rule_count = len(chain['rules'])
    spans = chain.get('rule_packs_spanned', [])

    out.append(f'\n## Chain: `{head["cite"]}` — {head["title"]}\n')
    out.append(f'**Rules:** {rule_count}  •  '
               f'**Standards:** {len(chain.get("terminal_standards", []))}  •  '
               f'**Evidence items:** {len(chain.get("evidence_required", []))}')
    if chain.get('cross_pack'):
        out.append(f'**Cross-pack chain** spanning: {", ".join(spans)}')
    else:
        out.append(f'**Pack:** {spans[0] if spans else "?"}')
    out.append('')

    if chain.get('subclusters'):
        out.append(f'### Sub-clusters ({len(chain["subclusters"])})\n')
        for i, sc in enumerate(chain['subclusters'], 1):
            out.append(f'**{i}. `{sc["head_cite"]}`** — {sc["head_title"][:60]}  '
                       f'_({sc["rule_count"]} rules, {", ".join(sc["packs"])})_')
        out.append('')

    out.append('### Rules\n')
    for r in chain['rules']:
        rid = r['rule_id']
        full_rule = rules_by_id.get(rid, r)
        out.append(render_rule_card(full_rule, facts))

    if chain.get('terminal_standards'):
        out.append('\n### Standards Required\n')
        for s in chain['terminal_standards']:
            out.append(f'  - `{s}`')

    if chain.get('evidence_required'):
        out.append('\n### Evidence Checklist\n')
        for ev in chain['evidence_required']:
            cite = ev.get('first_required_by', '?')
            out.append(f'  - [ ] **[{cite}]** {ev.get("item","")}')

    out.append('\n---')
    return '\n'.join(out)


def render_report(facts_doc: dict, rules_doc: dict, violations_doc: dict, chains_doc: dict) -> str:
    out = []
    project = facts_doc.get('project', {})
    declared_facts = set(normalize(p) for p in facts_doc.get('predicates', []))
    fired_rules = violations_doc.get('fires', [])
    rules_by_id = {r['id']: r for r in rules_doc.get('rules', [])}

    # ── HEADER ──
    addr = project.get('address', 'unknown')
    proj_type = project.get('type', 'unknown')
    out.append(f'# Plan-Check Review — {addr}\n')
    out.append(f'**Project type:** {proj_type}  ')
    if project.get('scope'):
        out.append(f'**Scope:** {project["scope"]}  ')
    if project.get('occupancy'):
        out.append(f'**Occupancy:** {project["occupancy"]}  ')
    if project.get('seismic_design_category'):
        out.append(f'**SDC:** {project["seismic_design_category"]}  ')
    if project.get('fire_hazard_severity_zone'):
        out.append(f'**FHSZ:** {project["fire_hazard_severity_zone"]}  ')
    if project.get('design_wind_speed_mph'):
        out.append(f'**Wind speed:** {project["design_wind_speed_mph"]} mph  ')
    if project.get('climate_zone'):
        out.append(f'**Climate zone:** {project["climate_zone"]}  ')
    out.append('')

    # ── EXECUTIVE SUMMARY ──
    summary = chains_doc.get('summary', {})
    rules_fired = summary.get('rules_fired', len(fired_rules))
    chains = chains_doc.get('chains', [])
    total_evidence = sum(len(c.get('evidence_required', [])) for c in chains)
    unique_standards = set()
    for c in chains:
        unique_standards.update(c.get('terminal_standards', []))

    out.append('## Summary\n')
    out.append(f'- **{rules_fired}** rules fired')
    out.append(f'- **{len(chains)}** compliance chains '
               f'(`{summary.get("multi_rule_chains",0)}` multi-rule, '
               f'`{summary.get("singleton_chains",0)}` singleton, '
               f'`{summary.get("cross_pack_chains",0)}` cross-pack)')
    out.append(f'- **{len(unique_standards)}** unique standards required')
    out.append(f'- **{total_evidence}** evidence items to verify')
    out.append('')

    # Chain index table
    out.append('## Chain Index\n')
    out.append('| # | Cite | Title | Rules | Standards | Cross-pack |')
    out.append('|---|---|---|---|---|---|')
    for i, c in enumerate(chains, 1):
        head = c['head']
        marker = '🔗' if c.get('cross_pack') else ''
        out.append(f'| {i} | `{head["cite"]}` | {head["title"][:55]} | '
                   f'{len(c["rules"])} | {len(c.get("terminal_standards",[]))} | {marker} |')
    out.append('')

    # ── PER-CHAIN SECTIONS ──
    out.append('---\n# Compliance Chains\n')
    for c in chains:
        out.append(render_chain(c, rules_by_id, declared_facts))

    # ── APPENDIX ──
    out.append('\n# Appendix\n')

    decomp = facts_doc.get('_decomposition')
    if decomp:
        out.append('## Fact Decomposition\n')
        out.append(f'- **Declared facts:** {decomp.get("declared",0)}')
        out.append(f'- **Derived facts:** {decomp.get("derived",0)} (via aliases, compounds, patterns)')
        out.append(f'- **Final fact set:** {decomp.get("final",0)} ({decomp.get("iterations",0)} iterations to fixed point)')
        out.append('')

    # Asserted facts table
    out.append('## Asserted Facts\n')
    sorted_facts = sorted(declared_facts)
    out.append('```')
    for f in sorted_facts:
        out.append(f)
    out.append('```\n')

    # Skipped rules count
    skipped = violations_doc.get('does_not_apply', [])
    out.append('## Skipped Rules\n')
    out.append(f'**{len(skipped)}** rules evaluated but did not fire (conditions did not match the project facts).')
    out.append('')

    out.append('---\n')
    out.append('_Generated by the CRC plan-check pipeline (graphify → rule extraction → fact decomposition → engine → chain analysis → report rendering)._')

    return '\n'.join(out)


def main():
    if len(sys.argv) < 6:
        print('usage: render_report.py <facts.json> <rules.json> <violations.json> <chains.json> <output.md>',
              file=sys.stderr)
        sys.exit(1)
    facts = json.loads(Path(sys.argv[1]).read_text())
    rules = json.loads(Path(sys.argv[2]).read_text())
    vios = json.loads(Path(sys.argv[3]).read_text())
    chains = json.loads(Path(sys.argv[4]).read_text())
    out_path = Path(sys.argv[5])
    md = render_report(facts, rules, vios, chains)
    out_path.write_text(md)
    print(f'Wrote {out_path}', file=sys.stderr)
    print(f'  {len(md.splitlines())} lines, {len(md):,} chars', file=sys.stderr)


if __name__ == '__main__':
    main()
