"""
Wire plan-check chains into the existing graphify Obsidian vault.

Inputs (per project):
  facts.expanded.json
  rules.json (= all_rules.json)
  violations.json
  chains.json
  graph.json (for ID → label lookup)

Outputs (into graphify-out/obsidian/):
  _PROJECT_<slug>.md          — project landing note with chain index
  _CHAIN_<head>_<slug>.md     — one note per chain, linking to graph node notes

Each chain note uses [[wikilinks]] to existing graph node notes by label,
so opening Obsidian shows the chains as an overlay on the graph view.
The graph view colors persist (community membership) and chain notes
appear as a separate cluster connected to the rule notes they cite.
"""

import json
import re
import sys
from pathlib import Path
from networkx.readwrite import json_graph


PLAN_DIR = Path(__file__).parent
VAULT_DIR = PLAN_DIR.parent / 'graphify-out' / 'obsidian'
GRAPH_PATH = PLAN_DIR.parent / 'graphify-out' / 'graph.json'


def filename_safe(s: str) -> str:
    """Match graphify export's sanitization — strip filesystem-forbidden chars."""
    return re.sub(r'[/\\:*?"<>|]', '', s)


def slugify(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def load_graph():
    data = json.loads(GRAPH_PATH.read_text())
    G = json_graph.node_link_graph(data, edges='links')
    id_to_label = {n: d.get('label', n) for n, d in G.nodes(data=True)}
    return id_to_label


def wikilink(node_id: str, id_to_label: dict, fallback: str | None = None) -> str:
    """Return [[Wikilink]] using the node's label (matching the existing vault filenames)."""
    label = id_to_label.get(node_id) or fallback or node_id
    return f'[[{filename_safe(label)}]]'


def render_project_note(facts_doc: dict, vios_doc: dict, chains_doc: dict, slug: str, id_to_label: dict) -> str:
    project = facts_doc.get('project', {})
    chains = chains_doc.get('chains', [])
    summary = chains_doc.get('summary', {})
    fires = vios_doc.get('fires', [])

    out = []
    out.append('---')
    out.append(f'type: plan-check-project')
    out.append(f'project_slug: "{slug}"')
    if project.get('address'):
        out.append(f'address: "{project["address"]}"')
    if project.get('type'):
        out.append(f'project_type: "{project["type"]}"')
    if project.get('seismic_design_category'):
        out.append(f'sdc: "{project["seismic_design_category"]}"')
    if project.get('fire_hazard_severity_zone'):
        out.append(f'fhsz: "{project["fire_hazard_severity_zone"]}"')
    out.append(f'rules_fired: {len(fires)}')
    out.append(f'chains: {len(chains)}')
    out.append(f'cross_pack_chains: {summary.get("cross_pack_chains", 0)}')
    out.append('tags:')
    out.append('  - plan-check')
    out.append(f'  - plan-check/project/{slug}')
    out.append('---\n')

    out.append(f'# 📋 Plan-Check Project — {project.get("address", slug)}\n')
    if project.get('type'):
        out.append(f'**Type:** {project["type"]}  ')
    if project.get('scope'):
        out.append(f'**Scope:** {project["scope"]}  ')
    if project.get('seismic_design_category'):
        out.append(f'**SDC:** {project["seismic_design_category"]}  ')
    if project.get('fire_hazard_severity_zone'):
        out.append(f'**FHSZ:** {project["fire_hazard_severity_zone"]}  ')
    if project.get('design_wind_speed_mph'):
        out.append(f'**Wind speed:** {project["design_wind_speed_mph"]} mph  ')
    out.append('')

    out.append('## Summary\n')
    out.append(f'- **{len(fires)}** rules fired')
    out.append(f'- **{len(chains)}** compliance chains '
               f'(`{summary.get("multi_rule_chains",0)}` multi-rule, `{summary.get("singleton_chains",0)}` singleton, '
               f'`{summary.get("cross_pack_chains",0)}` cross-pack)')
    unique_stds = set()
    for c in chains:
        unique_stds.update(c.get('terminal_standards', []))
    out.append(f'- **{len(unique_stds)}** standards required')
    total_evidence = sum(len(c.get('evidence_required', [])) for c in chains)
    out.append(f'- **{total_evidence}** evidence items\n')

    # Chain index
    out.append('## Compliance Chains\n')
    for c in chains:
        head = c['head']
        chain_filename = f'_CHAIN_{filename_safe(head["cite"])}_{slug}'
        marker = '🔗 ' if c.get('cross_pack') else ''
        out.append(f'- {marker}[[{chain_filename}|{head["cite"]} — {head["title"][:60]}]] '
                   f'_({len(c["rules"])} rules, {len(c.get("terminal_standards",[]))} standards)_')
    out.append('')

    # Asserted facts
    out.append('## Asserted Facts (project context)\n')
    out.append('```')
    for f in sorted(facts_doc.get('predicates', [])):
        out.append(f)
    out.append('```\n')

    out.append('## Tags')
    out.append(f'#plan-check #plan-check/project/{slug}')
    return '\n'.join(out)


def render_chain_note(chain: dict, slug: str, project_addr: str, rules_by_id: dict,
                      id_to_label: dict, declared_facts: set) -> str:
    head = chain['head']
    cite = head['cite']
    title = head['title']
    out = []

    out.append('---')
    out.append(f'type: plan-check-chain')
    out.append(f'project_slug: "{slug}"')
    out.append(f'chain_head: "{cite}"')
    out.append(f'chain_title: "{(title or "")[:80]}"')
    out.append(f'rule_count: {len(chain["rules"])}')
    out.append(f'standard_count: {len(chain.get("terminal_standards", []))}')
    out.append(f'cross_pack: {str(chain.get("cross_pack", False)).lower()}')
    out.append('rule_packs:')
    for p in chain.get('rule_packs_spanned', []):
        out.append(f'  - "{p}"')
    out.append('tags:')
    out.append('  - plan-check')
    out.append(f'  - plan-check/project/{slug}')
    out.append(f'  - plan-check/chain')
    out.append('---\n')

    out.append(f'# 🔗 Chain: `{cite}` — {title}\n')
    out.append(f'**Project:** [[_PROJECT_{slug}|{project_addr}]]  ')
    out.append(f'**Rules:** {len(chain["rules"])}  •  '
               f'**Standards:** {len(chain.get("terminal_standards", []))}  •  '
               f'**Evidence items:** {len(chain.get("evidence_required", []))}  ')
    if chain.get('cross_pack'):
        out.append(f'**Cross-pack** spanning: {", ".join(chain["rule_packs_spanned"])}\n')
    else:
        out.append(f'**Pack:** {chain["rule_packs_spanned"][0] if chain["rule_packs_spanned"] else "?"}\n')

    # Sub-clusters if present
    if chain.get('subclusters'):
        out.append(f'## Sub-clusters ({len(chain["subclusters"])})\n')
        for i, sc in enumerate(chain['subclusters'], 1):
            out.append(f'**{i}. `{sc["head_cite"]}`** — {sc["head_title"][:60]} '
                       f'_({sc["rule_count"]} rules)_')
        out.append('')

    # Rules — each one a wikilink to the existing graph note
    out.append('## Rules in This Chain\n')
    out.append('Each rule below links to its node in the code graph.\n')
    for r in chain['rules']:
        rid = r['rule_id']
        full_rule = rules_by_id.get(rid, r)
        section_node = full_rule.get('section_node')
        link_target = section_node if section_node else rid
        link = wikilink(link_target, id_to_label, fallback=full_rule.get('cite'))
        depth = r.get('depth_from_head', 0)
        marker = '★' if depth == 0 else f'+{depth}' if depth > 0 else ''
        cite_str = full_rule.get('cite', '?')
        title_str = full_rule.get('title', '')[:55]
        jur = full_rule.get('jurisdiction', '')
        jur_marker = '🇺🇸 CA' if jur == 'California' else ''
        out.append(f'- {marker:>2} `{cite_str}` {link} — {title_str} {jur_marker}')
        # Verbatim as collapsed callout
        if full_rule.get('verbatim'):
            v = full_rule['verbatim'].replace('\n', ' ').strip()
            out.append(f'  > {v[:200]}{"..." if len(v) > 200 else ""}')
    out.append('')

    # Standards required
    if chain.get('terminal_standards'):
        out.append('## Standards Required\n')
        for s in chain['terminal_standards']:
            link = wikilink(s, id_to_label)
            out.append(f'- {link} _(`{s}`)_')
        out.append('')

    # Evidence checklist
    if chain.get('evidence_required'):
        out.append('## Evidence Checklist\n')
        for ev in chain['evidence_required']:
            cite = ev.get('first_required_by', '?')
            out.append(f'- [ ] **[{cite}]** {ev.get("item","")}')
        out.append('')

    # Tags + backlinks
    out.append('## Related\n')
    out.append(f'- [[_PROJECT_{slug}]]')
    if chain.get('rule_packs_spanned'):
        for pack in chain['rule_packs_spanned']:
            pack_filename = f'_COMMUNITY_{filename_safe(pack)}'
            out.append(f'- [[{pack_filename}]]')
    out.append('')
    out.append(f'#plan-check #plan-check/project/{slug} #plan-check/chain')

    return '\n'.join(out)


def wire(facts_path: Path, rules_path: Path, vios_path: Path, chains_path: Path):
    facts_doc = json.loads(facts_path.read_text())
    rules_doc = json.loads(rules_path.read_text())
    vios_doc = json.loads(vios_path.read_text())
    chains_doc = json.loads(chains_path.read_text())

    id_to_label = load_graph()
    rules_by_id = {r['id']: r for r in rules_doc.get('rules', [])}

    project = facts_doc.get('project', {})
    addr = project.get('address', 'unknown')
    slug = slugify(addr)[:30] or 'project'

    declared_facts = set(facts_doc.get('predicates', []))

    # Project landing note
    project_note = render_project_note(facts_doc, vios_doc, chains_doc, slug, id_to_label)
    proj_path = VAULT_DIR / f'_PROJECT_{slug}.md'
    proj_path.write_text(project_note)
    print(f'  wrote {proj_path.name}')

    # Chain notes
    written = 0
    for chain in chains_doc.get('chains', []):
        head = chain['head']
        cite = head['cite']
        chain_filename = f'_CHAIN_{filename_safe(cite)}_{slug}.md'
        chain_note = render_chain_note(chain, slug, addr, rules_by_id, id_to_label, declared_facts)
        (VAULT_DIR / chain_filename).write_text(chain_note)
        written += 1
    print(f'  wrote {written} chain notes')

    return slug


def main():
    if len(sys.argv) < 5:
        print('usage: wire_obsidian.py <facts.json> <rules.json> <violations.json> <chains.json>', file=sys.stderr)
        sys.exit(1)
    slug = wire(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    print(f'\nProject slug: {slug}')
    print(f'Open: {VAULT_DIR}/_PROJECT_{slug}.md')


if __name__ == '__main__':
    main()
