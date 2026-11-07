"""Pass D — vocab enforcement, merge, conflict resolution, provenance assembly."""
from __future__ import annotations

import json
from datetime import date

from .. import config
from . import llm
from .context import ExtractionContext
from .schemas import CandidateFact, ProjectMeta, ReconciledFacts, SheetIndex
from .vocab import canonicalize


def _prov_entry(c: CandidateFact, by_page: dict) -> dict:
    sheet = by_page.get(c.page)
    return {
        "page": c.page,
        "sheet_id": c.sheet_id or (sheet.sheet_id if sheet else None),
        "sheet_type": sheet.sheet_type if sheet else None,
        "source": c.source,
        "evidence": c.evidence,
        "confidence": c.confidence,
        "value": c.value,
    }


async def reconcile_async(ctx: ExtractionContext, index: SheetIndex,
                          text_candidates: list[CandidateFact],
                          vision_candidates: list[CandidateFact],
                          text_project: ProjectMeta, warn=None) -> dict:
    raw = text_candidates + vision_candidates
    (ctx.book_dir / "candidates.json").write_text(
        json.dumps([c.model_dump() for c in raw], indent=2))

    # 1. Deterministic vocabulary enforcement (hard backstop).
    valid: list[CandidateFact] = []
    rejected: list[dict] = []
    for c in raw:
        canon = canonicalize(c.predicate, ctx.book.id)
        if canon is None:
            rejected.append({**c.model_dump(), "reason": "not in vocabulary"})
            continue
        c.predicate = canon
        valid.append(c)
    if rejected:
        (ctx.book_dir / "rejected.json").write_text(json.dumps(rejected, indent=2))

    # 2. Group + merge by predicate.
    groups: dict[str, list[CandidateFact]] = {}
    for c in valid:
        groups.setdefault(c.predicate, []).append(c)

    asserted: dict[str, list[CandidateFact]] = {}
    denied: dict[str, list[CandidateFact]] = {}
    conflicts: dict[str, list[CandidateFact]] = {}
    needs_review: list[CandidateFact] = []

    for pred, cands in groups.items():
        trues = [c for c in cands if c.value]
        falses = [c for c in cands if not c.value]
        if trues and falses:
            conflicts[pred] = cands
        elif trues:
            if max(c.confidence for c in trues) >= config.CONFIDENCE_THRESHOLD:
                asserted[pred] = trues
            else:
                needs_review.extend(trues)
        else:
            if max(c.confidence for c in falses) >= config.CONFIDENCE_THRESHOLD:
                denied[pred] = falses
            else:
                needs_review.extend(falses)

    project = text_project.merge(index.project)

    # 3. LLM reconciliation for conflicts + low-confidence (best effort).
    if conflicts or needs_review:
        resolved = await _llm_reconcile(ctx, conflicts, needs_review,
                                        project, warn)
        if resolved is not None:
            project = resolved.project.merge(project)
            for pred in resolved.predicates:
                canon = canonicalize(pred, ctx.book.id)
                if canon and canon not in denied:
                    asserted.setdefault(canon, groups.get(canon, []))
            for pred in resolved.false_predicates:
                canon = canonicalize(pred, ctx.book.id)
                if canon:
                    asserted.pop(canon, None)
                    denied.setdefault(canon, groups.get(canon, []))
        else:
            # Unresolved conflicts stay visible as needs-review instead of
            # silently disappearing from the result.
            for cands in conflicts.values():
                needs_review.extend(cands)

    # 4. Assemble facts.json with provenance.
    by_page = {s.page: s for s in index.sheets}
    provenance: dict[str, list[dict]] = {}
    for pred, cands in {**asserted, **denied}.items():
        if cands:
            provenance[pred] = [_prov_entry(c, by_page) for c in cands]

    return {
        "project": {k: v for k, v in project.model_dump().items() if v is not None},
        "predicates": sorted(asserted),
        "false_predicates": sorted(denied),
        "_notes": f"Extracted from {ctx.job_dir.name} on {date.today().isoformat()} "
                  f"by PlanCheck webapp ({ctx.book.short}).",
        "_provenance": provenance,
        "_needs_review": [c.model_dump() for c in needs_review],
    }


async def _llm_reconcile(ctx: ExtractionContext, conflicts: dict, needs_review: list,
                         project: ProjectMeta, warn=None) -> ReconciledFacts | None:
    payload = {
        "conflicts": {p: [c.model_dump() for c in cs] for p, cs in conflicts.items()},
        "low_confidence": [c.model_dump() for c in needs_review],
        "project_so_far": {k: v for k, v in project.model_dump().items() if v is not None},
    }
    content = [{"type": "text",
                "text": ctx.prompts.RECONCILE_PROMPT + "\n\n" + json.dumps(payload, indent=2)}]
    try:
        return await llm.parse_call([{"role": "user", "content": content}],
                                    ReconciledFacts, job_dir=ctx.usage_dir,
                                    book_id=ctx.book.id,
                                    context="reconcile")
    except Exception as exc:  # noqa: BLE001 - reconciliation is best effort
        if warn:
            warn("reconcile", "LLM reconciliation failed; conflicting and "
                 "low-confidence facts left as needs-review", detail=str(exc))
        return None
