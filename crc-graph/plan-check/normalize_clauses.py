"""
Normalize all applies_when / exception clauses to canonical Form A.

Forms encountered across the corpus:
  Form A: {"predicate": "x"}                                  (canonical, 310 clauses)
  Form B: {"any_of": [...]} / {"all_of": [...]} / {"not": x}  (138)
  Form C: {"name": true} or {"name": false}                   (108)
  Form D: {"key": "string_value"}                              (8)
  Bare:   "predicate_name"  (string, not dict)                 (6)

This script normalizes everything to Form A or B (both engine-supported):

  Form C true  → {"predicate": "name"}
  Form C false → {"predicate": "not", "of": [{"predicate": "name"}]}
  Form D       → {"predicate": "key_eq_value"}     (e.g. "structure_type_eq_strawbale")
  Bare string  → {"predicate": "name"}
  Form B       → {"predicate": "any_of", "of": [...]} (canonical)
                 (engine already supports both forms; we standardize for tooling)

Backups: every rule pack saved to .normalize/<pack>.pre-normalize.json
"""

import json
import glob
import re
import shutil
from pathlib import Path


PLAN_DIR = Path(__file__).parent
BACKUP_DIR = PLAN_DIR / '.normalize'


def normalize_clause(clause):
    """Recursively normalize one clause."""
    # Bare string → atomic predicate
    if isinstance(clause, str):
        return {'predicate': clause}
    if not isinstance(clause, dict):
        return clause

    # Form A — already canonical, but recurse into composite children
    if 'predicate' in clause:
        out = dict(clause)
        p = clause.get('predicate')
        if p in ('any_of', 'all_of', 'not'):
            children_key = 'of' if 'of' in clause else 'clauses' if 'clauses' in clause else None
            if children_key:
                out[children_key] = [normalize_clause(c) for c in clause[children_key]]
        return out

    # Form B — top-level any_of/all_of/not
    for key in ('any_of', 'all_of', 'not'):
        if key in clause:
            children = clause[key]
            if not isinstance(children, list):
                children = [children]
            return {
                'predicate': key,
                'of': [normalize_clause(c) for c in children],
            }

    # Form C — single bool-valued key
    bool_keys = [k for k, v in clause.items() if isinstance(v, bool)]
    if bool_keys and len(bool_keys) == len(clause):
        # All values are booleans
        if len(bool_keys) == 1:
            k = bool_keys[0]
            v = clause[k]
            if v:
                return {'predicate': k}
            else:
                return {'predicate': 'not', 'of': [{'predicate': k}]}
        # Multi-key bool dict — treat as conjunction of (k==v)
        sub_clauses = []
        for k, v in clause.items():
            if v:
                sub_clauses.append({'predicate': k})
            else:
                sub_clauses.append({'predicate': 'not', 'of': [{'predicate': k}]})
        return {'predicate': 'all_of', 'of': sub_clauses}

    # Form D — typed value: {"key": "value"} → predicate = key_eq_value
    if len(clause) == 1:
        k, v = next(iter(clause.items()))
        if isinstance(v, str):
            sanitized = re.sub(r'[^a-z0-9]+', '_', v.lower()).strip('_')
            return {'predicate': f'{k}_eq_{sanitized}'}
        if isinstance(v, (int, float)):
            return {'predicate': f'{k}_eq_{v}'}

    # Multi-key non-bool dict — try to interpret each key+value pair as a constraint
    # e.g. {"thickness": ">_4_in"} or {"slope": ">= 4:12"} (rare; just preserve)
    if len(clause) >= 1 and 'predicate' not in clause:
        sub_clauses = []
        for k, v in clause.items():
            if isinstance(v, bool):
                if v:
                    sub_clauses.append({'predicate': k})
                else:
                    sub_clauses.append({'predicate': 'not', 'of': [{'predicate': k}]})
            elif isinstance(v, str):
                sanitized = re.sub(r'[^a-z0-9]+', '_', v.lower()).strip('_')
                sub_clauses.append({'predicate': f'{k}_eq_{sanitized}'})
            elif isinstance(v, (int, float)):
                sub_clauses.append({'predicate': f'{k}_eq_{v}'})
        if len(sub_clauses) == 1:
            return sub_clauses[0]
        if sub_clauses:
            return {'predicate': 'all_of', 'of': sub_clauses}

    # Unknown shape — leave it alone, engine will treat as no-op
    return clause


def normalize_rule(rule):
    out = dict(rule)
    out['applies_when'] = [normalize_clause(c) for c in (rule.get('applies_when') or [])]
    if rule.get('exceptions'):
        out['exceptions'] = []
        for ex in rule['exceptions']:
            nex = dict(ex)
            nex['applies_when'] = [normalize_clause(c) for c in (ex.get('applies_when') or [])]
            out['exceptions'].append(nex)
    return out


def main():
    BACKUP_DIR.mkdir(exist_ok=True)
    paths = sorted(p for p in (list(PLAN_DIR.glob('c*_rules.json')) + [PLAN_DIR / 'wui_rules.json'])
                   if p.exists() and p.name != 'all_rules.json')

    total_clauses = 0
    transformed = 0
    by_shape_before = {}
    by_shape_after = {}

    def shape_label(c):
        if isinstance(c, str):
            return 'bare_string'
        if not isinstance(c, dict):
            return f'non_dict:{type(c).__name__}'
        if 'predicate' in c:
            return f'A_{c.get("predicate")}' if c.get("predicate") in ('any_of','all_of','not') else 'A'
        for k in ('any_of', 'all_of', 'not'):
            if k in c:
                return f'B_{k}'
        if all(isinstance(v, bool) for v in c.values()):
            return 'C'
        return 'D'

    for path in paths:
        # Backup
        backup = BACKUP_DIR / f'{path.stem}.pre-normalize.json'
        shutil.copy(path, backup)

        pack = json.loads(path.read_text())
        new_rules = []
        for r in pack['rules']:
            for c in (r.get('applies_when') or []):
                s = shape_label(c)
                by_shape_before[s] = by_shape_before.get(s, 0) + 1
                total_clauses += 1
                if s != 'A' and s.startswith(('B_','C','D','bare')) is False:
                    pass  # placeholder
            new_r = normalize_rule(r)
            new_rules.append(new_r)
            for c in (new_r.get('applies_when') or []):
                s = shape_label(c)
                by_shape_after[s] = by_shape_after.get(s, 0) + 1
                if s != shape_label((r.get('applies_when') or [None])[0] if r.get('applies_when') else None):
                    transformed += 1
        pack['rules'] = new_rules
        path.write_text(json.dumps(pack, indent=2))

    print(f'Normalized {len(paths)} rule packs')
    print(f'Total clauses: {total_clauses}')
    print(f'\nShape distribution BEFORE:')
    for s, n in sorted(by_shape_before.items(), key=lambda x: -x[1]):
        print(f'  {s:>20}  {n}')
    print(f'\nShape distribution AFTER:')
    for s, n in sorted(by_shape_after.items(), key=lambda x: -x[1]):
        print(f'  {s:>20}  {n}')


if __name__ == '__main__':
    main()
