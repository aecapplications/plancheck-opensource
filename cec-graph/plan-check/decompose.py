"""
Predicate decomposition / fact expansion.

Reads:
  facts.json          — declared atomic facts
  predicate_decomposition.json — alias groups, compounds, regex patterns
  rules.json           — used to discover which composites need to be checked

Produces:
  expanded_facts: a superset of declared facts that includes every composite
                  predicate whose decomposition is satisfied by the atomic set.

Algorithm:
  1. Seed asserted = normalize(declared facts)
  2. Expand via aliases (transitive closure over alias groups)
  3. Iterate to fixed point:
       For every composite predicate referenced in any rule's applies_when,
         if its decomposition is satisfied by current asserted set,
         add it to asserted.
       For every regex-pattern composite,
         if it matches a referenced predicate AND its decomposition is satisfied,
         add it.
  4. Return final asserted set.
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path


PLAN_DIR = Path(__file__).parent
DECOMP_PATH = PLAN_DIR / 'predicate_decomposition.json'


def normalize(p: str) -> str:
    s = p.lower().strip()
    s = re.sub(r'[\s\-]+', '_', s)
    s = re.sub(r'_+', '_', s)
    return s


def collect_referenced_predicates(rules: list) -> set[str]:
    """Walk every rule and return the set of atomic predicate names referenced."""
    out = set()

    def visit(c):
        if not isinstance(c, dict):
            return
        p = c.get('predicate')
        if p in ('any_of', 'all_of', 'not'):
            for child in (c.get('of') or c.get('clauses') or []):
                visit(child)
        elif p:
            out.add(p)

    for r in rules:
        for c in (r.get('applies_when') or []):
            visit(c)
        for ex in (r.get('exceptions') or []):
            for c in (ex.get('applies_when') or []):
                visit(c)
    return out


def expand_aliases(asserted: set[str], alias_groups: list[list[str]]) -> set[str]:
    """Transitive closure over alias groups: if any spelling is asserted, all are."""
    out = set(asserted)
    changed = True
    while changed:
        changed = False
        for group in alias_groups:
            if any(g in out for g in group):
                for g in group:
                    if g not in out:
                        out.add(g)
                        changed = True
    return out


def evaluate_decomp(decomp, asserted: set[str]) -> bool:
    """Evaluate a decomposition spec against the asserted set."""
    if isinstance(decomp, str):
        return decomp in asserted
    if not isinstance(decomp, dict):
        return False
    if 'all_of' in decomp:
        return all(evaluate_decomp(c, asserted) for c in decomp['all_of'])
    if 'any_of' in decomp:
        return any(evaluate_decomp(c, asserted) for c in decomp['any_of'])
    if 'not' in decomp:
        return not evaluate_decomp(decomp['not'], asserted)
    if 'predicate' in decomp:
        return decomp['predicate'] in asserted
    return False


def decompose_pattern(predicate: str, table: dict) -> dict | None:
    """If `predicate` matches a pattern rule, return its decomposition dict."""
    for rule in table.get('patterns', {}).get('rules', []):
        regex = rule.get('match')
        if not regex:
            continue
        m = re.match(regex, predicate)
        if not m:
            continue
        spec = rule['decompose']
        # Materialize captures
        return materialize_pattern(spec, m)
    return None


def materialize_pattern(spec, match) -> dict:
    """Substitute capture references in a pattern decomposition.

    Supported capture forms (domain-neutral):
      {"predicate_capture": <group>}  → {"predicate": <captured text>}
      {"any_of_capture": {"group": <group>, "token_regex": "...", "template": "in_{}_location"}}
            → splits the captured text into tokens and templates each into an any_of.
    """
    if isinstance(spec, str):
        return spec
    if not isinstance(spec, dict):
        return spec
    if 'predicate_capture' in spec:
        return {'predicate': match.group(spec['predicate_capture'])}
    if 'any_of_capture' in spec:
        cap = spec['any_of_capture']
        captured = match.group(cap['group']) or ''
        tokens = re.findall(cap.get('token_regex', r'\w+'), captured)
        template = cap.get('template', '{}')
        return {'any_of': [template.format(t) for t in tokens]}
    out = {}
    for k, v in spec.items():
        if isinstance(v, list):
            out[k] = [materialize_pattern(c, match) for c in v]
        else:
            out[k] = materialize_pattern(v, match)
    return out


def expand_facts(declared_facts: set[str], rule_predicates: set[str], table: dict) -> tuple[set[str], dict]:
    """Iteratively expand declared facts by asserting composites whose decomposition holds.

    Returns (expanded_facts, derivation_trace)
    """
    asserted = expand_aliases(set(declared_facts), table.get('aliases', {}).get('groups', []))
    derivations = []
    initial_size = len(asserted)

    compounds = table.get('compounds', {})

    changed = True
    iters = 0
    while changed and iters < 20:
        iters += 1
        changed = False
        # Explicit compounds — defined in table
        for composite, decomp in compounds.items():
            if composite.startswith('_'):
                continue
            if composite in asserted:
                continue
            if evaluate_decomp(decomp, asserted):
                asserted.add(composite)
                derivations.append({'asserted': composite, 'via': 'table', 'decomp': decomp})
                changed = True
        # Pattern-based — only check predicates referenced in rules
        for pred in sorted(rule_predicates):
            if pred in asserted:
                continue
            decomp = decompose_pattern(pred, table)
            if decomp and evaluate_decomp(decomp, asserted):
                asserted.add(pred)
                derivations.append({'asserted': pred, 'via': 'pattern', 'decomp': decomp})
                changed = True
        # Re-apply aliases after each round
        new_asserted = expand_aliases(asserted, table.get('aliases', {}).get('groups', []))
        if len(new_asserted) > len(asserted):
            for added in sorted(new_asserted - asserted):
                derivations.append({'asserted': added, 'via': 'alias'})
            asserted = new_asserted
            changed = True

    trace = {
        'iterations': iters,
        'initial_facts': initial_size,
        'final_facts': len(asserted),
        'derived': len(asserted) - initial_size,
        'derivations': derivations,
    }
    return asserted, trace


def main(argv):
    if len(argv) < 4:
        print('usage: decompose.py <facts.json> <rules.json> <expanded_facts.json>', file=sys.stderr)
        sys.exit(1)
    facts_doc = json.loads(Path(argv[1]).read_text())
    rules_doc = json.loads(Path(argv[2]).read_text())
    out_path = Path(argv[3])
    table = json.loads(DECOMP_PATH.read_text())

    declared = set()
    for p in facts_doc.get('predicates', []):
        declared.add(normalize(p))
    for k, v in facts_doc.items():
        if k in ('predicates', 'false_predicates', 'project', '_notes'):
            continue
        if v is True:
            declared.add(normalize(k))

    rule_preds = collect_referenced_predicates(rules_doc.get('rules', []))
    expanded, trace = expand_facts(declared, rule_preds, table)

    # Build expanded facts file (drop-in replacement for facts.json)
    out_facts = dict(facts_doc)
    out_facts['predicates'] = sorted(expanded)
    out_facts['_decomposition'] = {
        'declared': trace['initial_facts'],
        'derived':  trace['derived'],
        'final':    trace['final_facts'],
        'iterations': trace['iterations'],
    }
    out_path.write_text(json.dumps(out_facts, indent=2))

    print(f'Declared facts:  {trace["initial_facts"]}')
    print(f'Derived facts:   {trace["derived"]}')
    print(f'Final fact set:  {trace["final_facts"]}')
    print(f'Iterations:      {trace["iterations"]}')
    print(f'\nDerivations (top 20):')
    for d in trace['derivations'][:20]:
        print(f'  [{d["via"]:>7}]  {d["asserted"]}')


if __name__ == '__main__':
    main(sys.argv)
