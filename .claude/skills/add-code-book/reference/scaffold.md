# Step 3: scaffold `plan-check/`

Copy from `cec-graph/plan-check/`, the canonical donor.

| File | Treatment |
|---|---|
| `engine.py`, `integrate.py`, `normalize_clauses.py`, `render_report.py` | Copy **unchanged**. They must stay byte-identical across books. The webapp loads each book's copy via importlib (`webapp/books.py`), and the shared contract keeps behavior uniform. Never parameterize them. |
| `decompose.py` | Copy unchanged. It has cec's generalized `any_of_capture` pattern; crc's older `any_of_capture_sdcs` variant is CRC-only. |
| `chain.py` | Copy, then adapt exactly the three pieces below. Everything else stays identical to cec's. |
| `fixup_ids.py`, `canonicalize.py` | Copy and adapt as described below. |

`plan-check/` may already exist if step 4 ran first; `mkdir -p` is
harmless.

```bash
mkdir -p <book>-graph/plan-check
cp cec-graph/plan-check/{engine,integrate,normalize_clauses,render_report,decompose,chain,fixup_ids,canonicalize}.py <book>-graph/plan-check/
```

## The three `chain.py` adaptations

1. `_section_core()` reduces a node id to its bare section-number token.
2. `keep_relations` is the set of graphify relation types worth chaining
   across.
3. `is_terminal()` decides what counts as a leaf citation (tables, figures,
   referenced standards) in this book's id scheme.

Derive all three from real ids in the book's `graph.json`. For example:

```bash
python -c "import json; [print(n['id']) for n in json.load(open('<book>-graph/graphify-out/graph.json'))['nodes'][:60]]"
```

## Adapting `fixup_ids.py` and `canonicalize.py`

- **`fixup_ids.py`.** Only Pass 2 (fuzzy-matching ids that don't resolve
  against `graph.json`) is book-specific. In cec's copy, adapt
  `section_core()` (the same token logic as `chain.py`'s
  `_section_core()`), `STD_TOKEN_RE` (the standards bodies this book cites,
  e.g. `nfpa|ul|astm`), and the per-kind match order in its docstring
  (direct, table/figure, standard, section). Diff the crc and cec copies to
  see what differs between books.
- **`canonicalize.py`.** Only the predicate-category keyword table is
  book-specific: cec has LOCATION, EQUIPMENT, ELECTRICAL, WIRING_METHOD,
  and PROCEDURAL; crc has a building taxonomy. It only affects how
  `vocabulary.json` groups predicates for human review, not which rules
  fire, so a rough first pass is fine.

## Determinism

Keep every set iteration sorted in `chain.py` and `decompose.py`; there must
be no bare `for x in some_set`. Output must be byte-identical across
processes, and the parity gate depends on it.

## Validate

```bash
python .claude/skills/add-code-book/scripts/book_status.py <book>
```

Row 3 must be checked. It reports any shared file that differs from cec's.
