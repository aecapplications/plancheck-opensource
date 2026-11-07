"""
Plan-check engine.

Reads:
  facts.json     - declared facts about the project
  rules.json     - extracted rules (from one community pack or merged)
  graph.json     - the knowledge graph (for label/cite resolution)

Writes:
  violations.json - rules that fire with their cite chain and required evidence

Predicate evaluation:
  - Atomic predicate matches a fact by name (case-insensitive, normalized)
  - any_of  (at least one child true)
  - all_of  (all children true)
  - not     (one child, inverted)
  - default for applies_when array: all_of (every clause must be true)

Severity:
  - "required" rules whose conditions match → emit a violation entry with cite
  - "advisory" rules → emit but mark advisory
  - exceptions whose conditions match → suppress the rule (effect: rule_does_not_apply)
"""

import json
import re
import sys
from pathlib import Path
from typing import Any


def normalize(p: str) -> str:
    """Normalize a predicate name for fuzzy matching across spelling variants."""
    s = p.lower().strip()
    s = re.sub(r'[\s\-]+', '_', s)
    s = re.sub(r'_+', '_', s)
    return s


def fact_set(facts: dict) -> set[str]:
    """Convert facts dict into a normalized set of asserted predicate names.

    Supports two input shapes:
      {"predicate_name": true, ...}              flat dict of booleans
      {"predicates": ["a", "b", ...]}            list of asserted names
    Plus a `false_predicates` list to negate without listing every false fact.
    """
    asserted = set()
    if 'predicates' in facts:
        for p in facts['predicates']:
            asserted.add(normalize(p))
    for k, v in facts.items():
        if k in ('predicates', 'false_predicates', 'project'):
            continue
        if v is True:
            asserted.add(normalize(k))
    return asserted


def evaluate(clause: Any, facts: set[str]) -> bool:
    """Recursively evaluate one clause against the asserted-fact set.

    Accepts two interchangeable JSON shapes for composites (subagents emit both):
      Form A: {"predicate": "any_of", "of": [...]}
      Form B: {"any_of": [...]}                       (no predicate key)
    """
    if not isinstance(clause, dict):
        return False
    # Form B: top-level any_of/all_of/not key without 'predicate' field
    if 'predicate' not in clause:
        if 'any_of' in clause:
            return any(evaluate(c, facts) for c in (clause.get('any_of') or []))
        if 'all_of' in clause:
            return all(evaluate(c, facts) for c in (clause.get('all_of') or []))
        if 'not' in clause:
            nested = clause['not']
            if isinstance(nested, list):
                return not all(evaluate(c, facts) for c in nested) if nested else True
            return not evaluate(nested, facts)
        return False
    # Form A
    p = clause.get('predicate')
    if p == 'any_of':
        return any(evaluate(c, facts) for c in (clause.get('of') or clause.get('clauses') or []))
    if p == 'all_of':
        return all(evaluate(c, facts) for c in (clause.get('of') or clause.get('clauses') or []))
    if p == 'not':
        children = clause.get('of') or clause.get('clauses') or []
        return not all(evaluate(c, facts) for c in children) if children else True
    # Atomic predicate — match by normalized name
    if p:
        return normalize(p) in facts
    return False


def evaluate_clauses(clauses: list, facts: set[str]) -> bool:
    """Top-level applies_when array: all clauses must be true (AND).

    Truly empty clauses (`{}`) are no-ops. Composite clauses in either form
    (predicate-keyed or top-level any_of/all_of/not) are real constraints.
    """
    def is_meaningful(c):
        if not isinstance(c, dict):
            return False
        if c.get('predicate'):
            return True
        return any(k in c for k in ('any_of', 'all_of', 'not'))

    meaningful = [c for c in (clauses or []) if is_meaningful(c)]
    if not meaningful:
        return True
    return all(evaluate(c, facts) for c in meaningful)


def check_rule(rule: dict, facts: set[str]) -> dict | None:
    """Evaluate a single rule. Return a violation entry if it fires, else None."""
    applies_when = rule.get('applies_when', [])
    if not evaluate_clauses(applies_when, facts):
        return None

    # Check exceptions — if any exception's conditions are met, suppress
    suppressed_by = []
    for ex in rule.get('exceptions', []) or []:
        if evaluate_clauses(ex.get('applies_when', []), facts):
            suppressed_by.append({
                'exception_id': ex.get('id'),
                'effect': ex.get('effect', 'rule_does_not_apply'),
            })
    if any(e.get('effect') == 'rule_does_not_apply' for e in suppressed_by):
        return None  # rule suppressed by exception

    return {
        'rule_id': rule['id'],
        'cite': rule.get('cite'),
        'section_node': rule.get('section_node'),
        'title': rule.get('title'),
        'severity': rule.get('severity', 'required'),
        'jurisdiction': rule.get('jurisdiction'),
        'verbatim': rule.get('verbatim'),
        'requires': rule.get('requires'),
        'evidence_required': rule.get('evidence_required', []),
        'depends_on': rule.get('depends_on', []),
        'matched_conditions': [c.get('predicate') for c in applies_when if isinstance(c, dict)],
        'partially_suppressed_by': [e for e in suppressed_by if e.get('effect') != 'rule_does_not_apply'],
    }


def run(facts_path: Path, rules_path: Path) -> dict:
    """Run the engine and return a violations report."""
    facts = json.loads(facts_path.read_text())
    rules_doc = json.loads(rules_path.read_text())

    asserted = fact_set(facts)
    rules = rules_doc.get('rules', [])

    violations = []
    skipped = []
    for r in rules:
        v = check_rule(r, asserted)
        if v:
            violations.append(v)
        else:
            skipped.append({'rule_id': r['id'], 'cite': r.get('cite')})

    return {
        'project': facts.get('project', {}),
        'rule_pack': rules_doc.get('rule_pack'),
        'community_id': rules_doc.get('community_id'),
        'asserted_facts': sorted(asserted),
        'fires': violations,
        'does_not_apply': skipped,
        'summary': {
            'rules_evaluated': len(rules),
            'rules_fired': len(violations),
            'rules_skipped': len(skipped),
            'evidence_items_required': sum(len(v.get('evidence_required', [])) for v in violations),
        },
    }


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: engine.py <facts.json> <rules.json> [<output.json>]', file=sys.stderr)
        sys.exit(1)
    facts_path = Path(sys.argv[1])
    rules_path = Path(sys.argv[2])
    out_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None

    report = run(facts_path, rules_path)

    if out_path:
        out_path.write_text(json.dumps(report, indent=2))
        print(f'wrote {out_path}', file=sys.stderr)

    # Always print summary to stderr
    s = report['summary']
    print(f'Rule pack: {report["rule_pack"]}', file=sys.stderr)
    print(f'  evaluated: {s["rules_evaluated"]}', file=sys.stderr)
    print(f'  fired:     {s["rules_fired"]}', file=sys.stderr)
    print(f'  skipped:   {s["rules_skipped"]}', file=sys.stderr)
    print(f'  evidence items: {s["evidence_items_required"]}', file=sys.stderr)

    # Pipe-friendly summary to stdout
    for v in report['fires']:
        print(f'{v["severity"].upper():>9}  {v["cite"]:>10}  {v["title"]}')
