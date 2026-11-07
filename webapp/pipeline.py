"""Orchestrates extraction -> decompose -> engine -> chain -> report, then maps
fired rules back to PDF pages via fact provenance.

The four pipeline scripts are loaded per code book via the registry in
books.py (each book ships its own copies). Every intermediate artifact is
written into the job directory for auditability.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from . import books, config
from .jobs import store

# Only one job runs the rule engine / LLM at a time (rate-limit friendliness).
_run_lock = asyncio.Semaphore(1)


# --------------------------------------------------------------------------- #
# Plan-check (pure, no LLM) — usable standalone for verification
# --------------------------------------------------------------------------- #
def run_plan_check(book: books.Book, job_dir: Path, facts: dict) -> dict:
    """Run the book's decompose -> engine -> chain -> render on a facts dict.

    Writes facts.json, expanded.json, violations.json, chains.json, report.md,
    result.json into job_dir. Returns the result.json contents.
    """
    mods = books.load_modules(book.id)
    engine, decompose = mods.engine, mods.decompose
    chain, render_report = mods.chain, mods.render_report

    rules_doc = json.loads(book.all_rules_path.read_text())

    facts_path = job_dir / "facts.json"
    facts_path.write_text(json.dumps(facts, indent=2))

    # 1. Decompose (replicates decompose.main body; keeps derivation trace).
    table = json.loads(decompose.DECOMP_PATH.read_text())
    declared = {decompose.normalize(p) for p in facts.get("predicates", [])}
    rule_preds = decompose.collect_referenced_predicates(rules_doc.get("rules", []))
    expanded_set, trace = decompose.expand_facts(declared, rule_preds, table)

    expanded = dict(facts)
    expanded["predicates"] = sorted(expanded_set)
    expanded["_decomposition"] = {
        "declared": trace["initial_facts"],
        "derived": trace["derived"],
        "final": trace["final_facts"],
        "iterations": trace["iterations"],
        "derivations": trace["derivations"],
    }
    expanded_path = job_dir / "expanded.json"
    expanded_path.write_text(json.dumps(expanded, indent=2))

    # 2. Engine.
    violations = engine.run(expanded_path, book.all_rules_path)
    (job_dir / "violations.json").write_text(json.dumps(violations, indent=2))

    # 3. Chain.
    chains = chain.chain_violations(rules_doc, violations)
    (job_dir / "chains.json").write_text(json.dumps(chains, indent=2))

    # 4. Report.
    report_md = render_report.render_report(expanded, rules_doc, violations, chains)
    (job_dir / "report.md").write_text(report_md)

    # 5. Map violations to pages.
    result = map_violations_to_pages(mods, expanded, rules_doc, violations, chains, trace)
    (job_dir / "result.json").write_text(json.dumps(result, indent=2))
    return result


# --------------------------------------------------------------------------- #
# Provenance resolution: matched predicate -> source pages
# --------------------------------------------------------------------------- #
def _decomp_leaf_predicates(decomp) -> list[str]:
    """Collect leaf predicate names referenced by a decomposition spec."""
    out: list[str] = []
    if isinstance(decomp, str):
        return [decomp]
    if not isinstance(decomp, dict):
        return out
    for key in ("all_of", "any_of"):
        for child in decomp.get(key, []) or []:
            out.extend(_decomp_leaf_predicates(child))
    if "not" in decomp:
        out.extend(_decomp_leaf_predicates(decomp["not"]))
    if "predicate" in decomp:
        out.append(decomp["predicate"])
    return out


class ProvenanceResolver:
    """Resolves any (possibly derived) predicate to its source provenance
    entries by walking alias groups and the decomposition derivation trace
    back to declared atoms that carry direct provenance."""

    def __init__(self, provenance: dict, trace: dict, table: dict):
        self.prov = provenance or {}
        # predicate -> decomp spec (from derivations that recorded one)
        self.derivation_decomp: dict[str, object] = {}
        for d in trace.get("derivations", []):
            if "decomp" in d:
                self.derivation_decomp[d["asserted"]] = d["decomp"]
        # alias groups for sideways resolution
        self.alias_groups = table.get("aliases", {}).get("groups", [])
        self._alias_index: dict[str, list[str]] = {}
        for group in self.alias_groups:
            for member in group:
                self._alias_index[member] = group

    def resolve(self, predicate: str, _seen: set[str] | None = None) -> list[dict]:
        if _seen is None:
            _seen = set()
        if predicate in _seen:
            return []
        _seen.add(predicate)

        if predicate in self.prov:
            return list(self.prov[predicate])

        entries: list[dict] = []
        # alias siblings
        for sibling in self._alias_index.get(predicate, []):
            if sibling != predicate and sibling in self.prov:
                entries.extend(self.prov[sibling])
        # decomposition sources
        decomp = self.derivation_decomp.get(predicate)
        if decomp:
            for leaf in _decomp_leaf_predicates(decomp):
                entries.extend(self.resolve(leaf, _seen))
        # dedupe by (page, predicate-evidence)
        seen_keys = set()
        deduped = []
        for e in entries:
            k = (e.get("page"), e.get("evidence"))
            if k not in seen_keys:
                seen_keys.add(k)
                deduped.append(e)
        return deduped


def map_violations_to_pages(mods: books.BookModules, expanded: dict,
                            rules_doc: dict, violations: dict,
                            chains: dict, trace: dict) -> dict:
    """Build result.json: per-page flags plus chains and review items."""
    facts_set = mods.engine.fact_set(expanded)
    provenance = expanded.get("_provenance", {})
    table = json.loads(mods.decompose.DECOMP_PATH.read_text())
    resolver = ProvenanceResolver(provenance, trace, table)

    rules_by_id = {r["id"]: r for r in rules_doc.get("rules", [])}

    pages: dict[int, dict] = {}
    unmapped: list[dict] = []

    for v in violations.get("fires", []):
        rule = rules_by_id.get(v["rule_id"], {})
        matched = mods.render_report.matched_predicates(rule.get("applies_when", []), facts_set)

        # Gather provenance entries for the predicates that triggered this rule.
        flag_locations: dict[int, dict] = {}   # page -> best entry for this rule
        triggering: list[str] = []
        for pred in matched:
            entries = resolver.resolve(pred)
            if entries:
                triggering.append(pred)
            for e in entries:
                pg = e.get("page")
                if pg is None:
                    continue
                cur = flag_locations.get(pg)
                if cur is None or e.get("confidence", 0) > cur.get("confidence", 0):
                    flag_locations[pg] = {**e, "via_predicate": pred}

        flag_base = {
            "rule_id": v["rule_id"],
            "cite": v.get("cite"),
            "title": v.get("title"),
            "severity": v.get("severity", "required"),
            "evidence_required": v.get("evidence_required", []),
            "matched_predicates": matched,
        }

        if not flag_locations:
            unmapped.append({**flag_base, "reason": "triggered by project metadata "
                                                     "or facts without page provenance"})
            continue

        for pg, loc in flag_locations.items():
            page = pages.setdefault(pg, {
                "page": pg,
                "sheet_id": loc.get("sheet_id"),
                "sheet_type": loc.get("sheet_type"),
                "flags": [],
            })
            page["flags"].append({
                **flag_base,
                "via_predicate": loc.get("via_predicate"),
                "evidence": loc.get("evidence"),
                "confidence": loc.get("confidence"),
                "source": loc.get("source"),
            })

    page_list = sorted(pages.values(), key=lambda p: p["page"])
    for p in page_list:
        sev_rank = {"required": 3, "recommended": 2, "informational": 1}
        p["max_severity"] = max(
            (f.get("severity", "required") for f in p["flags"]),
            key=lambda s: sev_rank.get(s, 0), default="required")
        p["flag_count"] = len(p["flags"])

    chain_summaries = []
    for c in chains.get("chains", []):
        head = c.get("head", {})
        chain_summaries.append({
            "head_cite": head.get("cite"),
            "head_title": head.get("title"),
            "rule_count": len(c.get("rules", [])),
            "cross_pack": c.get("cross_pack", False),
            "rule_ids": [r.get("id") if isinstance(r, dict) else r for r in c.get("rules", [])],
        })

    return {
        "project": expanded.get("project", {}),
        "summary": {
            "pages_flagged": len(page_list),
            "rules_fired": violations.get("summary", {}).get("rules_fired", 0),
            "chains": chains.get("summary", {}).get("chains", 0),
            "evidence_items": violations.get("summary", {}).get("evidence_items_required", 0),
            "unmapped_rules": len(unmapped),
            "needs_review": len(expanded.get("_needs_review", [])),
        },
        "pages": page_list,
        "unmapped_rules": unmapped,
        "chains": chain_summaries,
        "needs_review": expanded.get("_needs_review", []),
        "usage": {},  # populated by run_job via _run_plan_check_with_usage
    }


def _read_usage_total(job_dir: Path) -> dict:
    path = job_dir / "usage.jsonl" if job_dir else None
    if not path or not path.exists():
        return {}
    totals = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        u = json.loads(line)
        totals["input"] += u.get("input_tokens", 0)
        totals["output"] += u.get("output_tokens", 0)
        totals["cache_read"] += u.get("cache_read_input_tokens", 0)
        totals["cache_write"] += u.get("cache_creation_input_tokens", 0)
    cost = (totals["input"] * config.PRICE_INPUT_PER_MTOK
            + totals["output"] * config.PRICE_OUTPUT_PER_MTOK
            + totals["cache_read"] * config.PRICE_CACHE_READ_PER_MTOK
            + totals["cache_write"] * config.PRICE_CACHE_WRITE_PER_MTOK) / 1_000_000
    totals["estimated_cost_usd"] = round(cost, 2)
    return totals


# --------------------------------------------------------------------------- #
# Background job entrypoint
# --------------------------------------------------------------------------- #
async def run_job(job_id: str) -> None:
    """Full async job: validate -> classify (shared) -> per-book checks.

    Books run concurrently; a single failed book is marked errored in
    book_status while the others still deliver. The job errors only if every
    selected book fails.
    """
    from . import extractor  # local import to avoid cycle

    job_dir = store.job_dir(job_id)
    pdf_path = job_dir / "upload.pdf"
    async with _run_lock:
        try:
            status = store.get(job_id)
            book_list = [books.get(b) for b in (status.books if status else ["crc"])]

            store.set_phase(job_id, "validating", "Validating PDF")
            from .extractor.pdf_io import validate_pdf, render_all_pages
            page_count, errors = validate_pdf(pdf_path)
            if errors:
                raise ValueError("; ".join(errors))

            # Render page PNGs up front (used by extraction and the result UI).
            render_all_pages(pdf_path, job_dir / "pages")

            # Classification is shared across books (skipped in FAKE mode,
            # which synthesizes per-book facts directly).
            index = None
            if not config.FAKE_EXTRACTOR:
                from .extractor import warmup
                await warmup.wait_ready()
                index = await extractor.classify_pass(job_id, job_dir,
                                                      pdf_path, page_count)

            label = ", ".join(b.short for b in book_list)
            store.set_phase(job_id, "per_book", f"Checking {label}")
            results = await asyncio.gather(
                *[_run_book(job_id, b, job_dir, pdf_path, index, page_count)
                  for b in book_list],
                return_exceptions=True)

            ok = [(b, r) for b, r in zip(book_list, results)
                  if not isinstance(r, BaseException)]
            failed = [b.short for b, r in zip(book_list, results)
                      if isinstance(r, BaseException)]
            if not ok:
                raise RuntimeError(f"all book checks failed: {', '.join(failed)}")

            message = "; ".join(
                f"{b.short}: {r['summary']['rules_fired']} rules on "
                f"{r['summary']['pages_flagged']} sheets" for b, r in ok)
            if failed:
                message += f"; {', '.join(failed)} failed"
            status = store.get(job_id)
            if status and status.warnings:
                message += f"; {len(status.warnings)} warning(s)"
            store.update(job_id, state="done", phase="done", message=message,
                         progress_done=0, progress_total=0)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            status = store.get(job_id)
            phase = status.phase if status else "unknown"
            store.update(job_id, state="error", phase="error",
                         error=f"Failed during '{phase}': {exc}")


async def _run_book(job_id: str, book: books.Book, job_dir: Path,
                    pdf_path: Path, index, page_count: int) -> dict:
    """One book's extraction + plan check, into books/<book_id>/."""
    from . import extractor
    from .extractor import context

    book_dir = job_dir / "books" / book.id
    book_dir.mkdir(parents=True, exist_ok=True)
    try:
        if config.FAKE_EXTRACTOR:
            store.set_book(job_id, book.id, state="running", phase="extracting",
                           message="Loading sample facts")
            facts = extractor.fake_facts(book, page_count)
        else:
            store.set_book(job_id, book.id, state="running", phase="text_pass",
                           message="Extracting facts")
            ctx = context.make(book, job_dir, book_dir)
            facts = await extractor.extract_book_facts(job_id, ctx, pdf_path,
                                                       index)

        store.set_book(job_id, book.id, phase="plan_check",
                       message="Running rule engine")
        status = store.get(job_id)
        # Book-tagged warnings plus shared-stage ones (classify, validation).
        warnings = [w for w in (status.warnings if status else [])
                    if w.get("phase", "").startswith(f"{book.id}:")
                    or ":" not in w.get("phase", "")]
        result = await asyncio.to_thread(_run_plan_check_with_usage,
                                         book, book_dir, facts, warnings)
        store.set_book(job_id, book.id, state="done", phase="done",
                       message=f"{result['summary']['rules_fired']} rules fired",
                       progress_done=0, progress_total=0)
        return result
    except Exception as exc:
        store.set_book(job_id, book.id, state="error", phase="error",
                       error=str(exc))
        raise


def _run_plan_check_with_usage(book: books.Book, job_dir: Path, facts: dict,
                               warnings: list | None = None) -> dict:
    """Wrapper that injects the usage total (which needs job_dir) into result."""
    result = run_plan_check(book, job_dir, facts)
    result["usage"] = _read_usage_total(job_dir)
    result["warnings"] = warnings or []
    result["summary"]["warnings"] = len(result["warnings"])
    (job_dir / "result.json").write_text(json.dumps(result, indent=2))
    return result
