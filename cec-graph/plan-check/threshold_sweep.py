"""
Sweep the min_graph_confidence threshold and report chain compression metrics.

For each threshold in {0.0, 0.6, 0.7, 0.8, 0.9, 1.0}:
  - run chain_violations
  - record: chain count, compression ratio, largest chain size, cross-pack chains,
    edge_stats breakdown
"""

import json
from pathlib import Path

import chain


PLAN_DIR = Path(__file__).parent
RULES_PATH = PLAN_DIR / 'all_rules.json'
VIOS_PATH = PLAN_DIR / 'sample-facts' / 'full-violations.json'


def main():
    rules_doc = json.loads(RULES_PATH.read_text())
    vios_doc = json.loads(VIOS_PATH.read_text())

    thresholds = [0.0, 0.6, 0.7, 0.8, 0.9, 1.0]
    results = []
    for thr in thresholds:
        out = chain.chain_violations(rules_doc, vios_doc, min_graph_confidence=thr)
        s = out['summary']
        sizes = sorted([len(c['rules']) for c in out['chains']], reverse=True)
        results.append({
            'threshold': thr,
            'chains': s['chains'],
            'compression': s['compression_ratio'],
            'cross_pack': s['cross_pack_chains'],
            'multi_rule': s['multi_rule_chains'],
            'singletons': s['singleton_chains'],
            'top5_sizes': sizes[:5],
            'edge_stats': s.get('edge_stats', {}),
        })

    # Pretty table
    print(f'{"thr":>4}  {"chains":>6}  {"compr":>5}  {"xpack":>5}  {"multi":>5}  {"single":>6}  '
          f'{"top1":>4}  {"top2":>4}  {"top3":>4}  {"graph_edges":>11}  {"fuzzy":>5}  {"exact":>5}')
    print('-' * 95)
    for r in results:
        e = r['edge_stats']
        sizes = r['top5_sizes'] + [0, 0, 0]
        print(f'{r["threshold"]:>4}  {r["chains"]:>6}  {r["compression"]:>5.2f}  '
              f'{r["cross_pack"]:>5}  {r["multi_rule"]:>5}  {r["singletons"]:>6}  '
              f'{sizes[0]:>4}  {sizes[1]:>4}  {sizes[2]:>4}  '
              f'{e.get("graph", 0):>11}  {e.get("fuzzy", 0):>5}  {e.get("exact", 0):>5}')

    # Export full results
    Path(PLAN_DIR / 'sample-facts' / 'threshold_sweep.json').write_text(json.dumps(results, indent=2))
    print(f'\nWrote sample-facts/threshold_sweep.json')


if __name__ == '__main__':
    main()
