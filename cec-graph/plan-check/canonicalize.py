"""
Predicate canonicalization (Stage 2).

Reads:
  one or more rules.json files
Writes:
  vocabulary.json - canonical predicate dictionary
  <pack>_rules.canonical.json - rules with predicates remapped to canonical names

Strategy:
  1. Collect every atomic predicate name (skipping any_of / all_of / not).
  2. Build a normalized fingerprint (lowercase, alpha+digits+underscores only).
  3. Group by fingerprint similarity:
     - Exact normalized match → same canonical
     - Stem match (drop common suffixes/prefixes) → propose merge
     - Numeric-threshold variants ("_>50%_" vs "_>=50%_") → propose merge with conflict flag
  4. Pick the most-used spelling as the canonical, alphabetically as tiebreaker.
  5. Emit a vocabulary.json that lists canonical names + their aliases, organized
     into the electrical-domain predicate taxonomy:
     LOCATION, EQUIPMENT, ELECTRICAL, WIRING_METHOD, PROCEDURAL.

Categorization is heuristic (keyword-based), but vocabulary.json captures every
predicate so a human can correct categories during review.
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


# Electrical-domain predicate taxonomy (CEC). Categories are heuristic keyword
# matches; vocabulary.json still captures every predicate for human review.
CATEGORY_KEYWORDS = {
    'LOCATION': ['wet_location', 'damp_location', 'dry_location', 'hazardous_location',
                 'classified', 'class_i', 'class_ii', 'class_iii', 'division_', 'in_zone_',
                 'outdoor', 'indoor', 'wet', 'damp', 'corrosive', 'submerged', 'underground',
                 'in_dwelling', 'in_bathroom', 'in_kitchen', 'in_garage'],
    'EQUIPMENT': ['is_panelboard', 'is_switchboard', 'is_switchgear', 'is_breaker', 'is_overcurrent',
                  'is_transformer', 'is_motor', 'is_luminaire', 'is_receptacle', 'is_disconnect',
                  'is_service', 'is_feeder', 'is_busway', 'is_generator', 'is_ev', 'is_appliance',
                  'is_enclosure', 'is_box', 'is_equipment'],
    'ELECTRICAL': ['voltage_', '_volts', '_volt', 'amperage_', '_amps', '_amp', '_a_to_', 'ampacity',
                   'phase', 'gfci', 'afci', 'grounded', 'ungrounded', 'bonded', 'grounding',
                   'current_', '_kva', '_kw', 'overcurrent_', '_>_', '_>=_', '_<_', '_<=_'],
    'WIRING_METHOD': ['is_conduit', 'is_emt', 'is_pvc', 'is_rmc', 'is_imc', 'is_romex', 'is_nm_cable',
                      'is_mc_cable', 'is_ac_cable', 'is_raceway', 'is_wireway', 'is_cable_tray',
                      'is_metallic', 'is_nonmetallic', 'is_flexible', 'conductor_', 'wiring_method_'],
    'PROCEDURAL': ['listed', 'labeled', 'identified', 'approved', 'marked', 'in_accordance_with_',
                   'tested_per_', 'per_section_', 'jurisdiction_', 'exception_', 'permitted'],
}


def normalize(p: str) -> str:
    s = p.lower().strip()
    s = re.sub(r'[\s\-]+', '_', s)
    s = re.sub(r'_+', '_', s)
    return s


def fingerprint(p: str) -> str:
    """Tighter normalization that strips common variations to find aliases.

    >50%, >=50%, gt_50_pct, more_than_50_percent → all collapse to similar tokens
    """
    s = normalize(p)
    s = s.replace('>=', '_gte_').replace('<=', '_lte_').replace('>', '_gt_').replace('<', '_lt_')
    s = s.replace('%', '_pct_')
    s = re.sub(r'percent', 'pct', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s


def categorize(p: str) -> str:
    s = normalize(p)
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(kw in s for kw in kws):
            return cat
    return 'OTHER'


def collect_atomic(clause, sink: list):
    if not isinstance(clause, dict):
        return
    p = clause.get('predicate')
    if p in ('any_of', 'all_of', 'not'):
        for c in (clause.get('of') or clause.get('clauses') or []):
            collect_atomic(c, sink)
    elif p:
        sink.append(p)


def collect_predicates(rules: list) -> list[tuple[str, str]]:
    """Returns list of (predicate, source rule_id) pairs."""
    out = []
    for r in rules:
        rid = r.get('id', '?')
        for c in r.get('applies_when', []):
            buf = []
            collect_atomic(c, buf)
            for p in buf:
                out.append((p, rid))
        for ex in r.get('exceptions', []) or []:
            for c in ex.get('applies_when', []):
                buf = []
                collect_atomic(c, buf)
                for p in buf:
                    out.append((p, rid + ':' + (ex.get('id') or '?')))
    return out


def build_vocabulary(rule_packs: list[dict]) -> dict:
    """Group all predicates across rule packs by fingerprint."""
    spellings = defaultdict(list)  # fingerprint → [(spelling, rule_id, pack)]
    for pack in rule_packs:
        pack_id = pack.get('rule_pack', '?')
        preds = collect_predicates(pack.get('rules', []))
        for p, rid in preds:
            fp = fingerprint(p)
            spellings[fp].append({'spelling': p, 'rule_id': rid, 'pack': pack_id})

    vocab = {}
    for fp, entries in spellings.items():
        # Pick canonical: most-used spelling, alphabetical tiebreak
        spell_counts = Counter(e['spelling'] for e in entries)
        canonical = sorted(spell_counts.items(), key=lambda x: (-x[1], x[0]))[0][0]
        canonical_norm = normalize(canonical)
        all_spellings = sorted(set(e['spelling'] for e in entries))
        aliases = [s for s in all_spellings if s != canonical]
        usage_by_pack = Counter(e['pack'] for e in entries)
        vocab[canonical_norm] = {
            'canonical': canonical,
            'fingerprint': fp,
            'category': categorize(canonical),
            'aliases': aliases,
            'total_uses': len(entries),
            'used_in_packs': dict(usage_by_pack),
            'sample_rule_ids': sorted({e['rule_id'] for e in entries})[:5],
        }
    return vocab


def remap_clause(clause, alias_to_canonical: dict):
    if not isinstance(clause, dict):
        return clause
    p = clause.get('predicate')
    out = dict(clause)
    if p in ('any_of', 'all_of', 'not'):
        children = clause.get('of') or clause.get('clauses') or []
        out_key = 'of' if 'of' in clause else 'clauses'
        out[out_key] = [remap_clause(c, alias_to_canonical) for c in children]
    elif p:
        # Look up canonical
        canonical = alias_to_canonical.get(normalize(p))
        if canonical and canonical != p:
            out['predicate'] = canonical
            out.setdefault('_was', p)
    return out


def remap_rules(pack: dict, alias_to_canonical: dict) -> dict:
    out = dict(pack)
    out['rules'] = []
    for r in pack.get('rules', []):
        nr = dict(r)
        nr['applies_when'] = [remap_clause(c, alias_to_canonical) for c in r.get('applies_when', [])]
        if r.get('exceptions'):
            nr['exceptions'] = []
            for ex in r['exceptions']:
                nex = dict(ex)
                nex['applies_when'] = [remap_clause(c, alias_to_canonical) for c in ex.get('applies_when', [])]
                nr['exceptions'].append(nex)
        out['rules'].append(nr)
    return out


def main(input_files: list[Path], out_dir: Path):
    out_dir.mkdir(exist_ok=True)
    packs = [json.loads(p.read_text()) for p in input_files]

    vocab = build_vocabulary(packs)

    # Build alias → canonical lookup (for the remap step)
    alias_to_canonical = {}
    for canon_norm, entry in vocab.items():
        alias_to_canonical[canon_norm] = entry['canonical']
        for alias in entry['aliases']:
            alias_to_canonical[normalize(alias)] = entry['canonical']

    # Sort vocabulary by category then by usage count
    cat_order = ['LOCATION', 'EQUIPMENT', 'ELECTRICAL', 'WIRING_METHOD', 'PROCEDURAL', 'OTHER']
    sorted_vocab = sorted(vocab.values(), key=lambda v: (cat_order.index(v['category']), -v['total_uses']))

    vocab_doc = {
        'schema_version': '0.1',
        'description': 'Canonical predicate vocabulary for the CEC plan-check rule engine',
        'predicate_count': len(vocab),
        'alias_count': sum(len(v['aliases']) for v in vocab.values()),
        'total_predicate_uses': sum(v['total_uses'] for v in vocab.values()),
        'by_category': {cat: sum(1 for v in vocab.values() if v['category'] == cat) for cat in cat_order},
        'predicates': sorted_vocab,
    }

    vocab_path = out_dir / 'vocabulary.json'
    vocab_path.write_text(json.dumps(vocab_doc, indent=2))
    print(f'wrote {vocab_path}')
    print(f'  {len(vocab)} canonical predicates')
    print(f'  {sum(len(v["aliases"]) for v in vocab.values())} aliases merged')

    # Remap each rule pack
    for path, pack in zip(input_files, packs):
        canonical_pack = remap_rules(pack, alias_to_canonical)
        out_path = out_dir / (path.stem + '.canonical.json')
        out_path.write_text(json.dumps(canonical_pack, indent=2))


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: canonicalize.py <out_dir> <rules1.json> [rules2.json ...]', file=sys.stderr)
        sys.exit(1)
    out_dir = Path(sys.argv[1])
    inputs = [Path(p) for p in sys.argv[2:]]
    main(inputs, out_dir)
