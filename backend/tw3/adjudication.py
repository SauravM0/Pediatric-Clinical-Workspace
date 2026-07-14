"""Adjudication queue service (Plan 2 WI-4).

Turns the pure multi-rater consensus (consensus.py) into a persisted, actionable
senior-review loop. When several independent reads of one film disagree on a bone,
that bone is queued here (never silently averaged); a qualified reviewer resolves
it, and the resolved label takes precedence when the dataset is exported.

DB logic kept out of the HTTP layer. ``film_key`` groups reads of the same film
(a radiograph id or image hash as a string).
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable, Mapping, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import APP_VERSION
from backend.models import AdjudicationItem, AuditEvent
from backend.tw3.consensus import consensus
from backend.tw3.constants import LETTER_STAGES, STAGES, StageSystem, bones_for_system


class AdjudicationError(ValueError):
    """Invalid adjudication operation (maps to HTTP 422)."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _allowed_stages(stage_system: str) -> tuple[str, ...]:
    return LETTER_STAGES if stage_system == StageSystem.TW3_LETTERS.value else STAGES


def refresh_from_consensus(db: Session, films: Iterable[Mapping]) -> dict:
    """Open adjudication items for disputed bones across multi-reader films.

    ``films``: iterable of ``{"film_key", "stage_system", "stages": {bone: stage}}``,
    one per independent read. Only films with >= 2 reads in the same stage system are
    considered. For each bone with no clear majority, an OPEN item is created (or its
    votes refreshed if one already exists) — never a duplicate open item. Returns a
    summary ``{groups, opened, refreshed}``.
    """
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for f in films:
        key = f.get("film_key")
        if key in (None, ""):
            continue
        groups[(str(key), str(f.get("stage_system")))].append(dict(f.get("stages") or {}))

    opened = refreshed = n_groups = 0
    for (film_key, system), stagings in groups.items():
        if len(stagings) < 2:
            continue
        n_groups += 1
        res = consensus(stagings, bones_for_system(system))
        for bone in res.adjudication_bones:
            votes = json.dumps(res.per_bone[bone].votes)
            existing = db.execute(
                select(AdjudicationItem).where(
                    AdjudicationItem.film_key == film_key,
                    AdjudicationItem.stage_system == system,
                    AdjudicationItem.bone_code == bone,
                    AdjudicationItem.status == "open",
                )
            ).scalar_one_or_none()
            if existing is not None:
                existing.votes_json = votes
                existing.n_readers = res.n_raters
                refreshed += 1
                continue
            db.add(AdjudicationItem(
                film_key=film_key, stage_system=system, bone_code=bone,
                votes_json=votes, n_readers=res.n_raters, status="open",
            ))
            opened += 1
    db.flush()
    return {"groups": n_groups, "opened": opened, "refreshed": refreshed}


def list_items(db: Session, *, status: Optional[str] = None) -> list[AdjudicationItem]:
    q = select(AdjudicationItem)
    if status:
        q = q.where(AdjudicationItem.status == status)
    return list(db.execute(q.order_by(AdjudicationItem.created_at)).scalars())


def resolve(db: Session, item_id: int, *, resolved_stage: str, resolved_by: str,
            reason: Optional[str] = None) -> AdjudicationItem:
    """A reviewer resolves a disputed bone to a single stage. Audited; idempotent-safe
    (a second resolve on the same item raises rather than silently overwriting)."""
    item = db.get(AdjudicationItem, item_id)
    if item is None:
        raise AdjudicationError(f"adjudication item {item_id} not found")
    if item.status == "resolved":
        raise AdjudicationError(f"item {item_id} is already resolved")
    if not resolved_by:
        raise AdjudicationError("resolved_by (the reviewer) is required")
    if resolved_stage not in _allowed_stages(item.stage_system):
        raise AdjudicationError(
            f"invalid stage {resolved_stage!r} for {item.stage_system}")

    item.status = "resolved"
    item.resolved_stage = resolved_stage
    item.resolved_by = resolved_by
    item.resolved_at = _utcnow()
    item.reason = reason
    db.add(AuditEvent(
        event_type="adjudication_resolve", actor=resolved_by, reason=reason,
        new_value=json.dumps({"film_key": item.film_key, "bone": item.bone_code,
                              "stage": resolved_stage}),
        application_version=APP_VERSION,
    ))
    db.flush()
    return item


def consensus_labels(db: Session, film_key: str, stage_system: str) -> dict:
    """Resolved adjudication labels for a film — these take precedence on export."""
    items = db.execute(
        select(AdjudicationItem).where(
            AdjudicationItem.film_key == str(film_key),
            AdjudicationItem.stage_system == stage_system,
            AdjudicationItem.status == "resolved",
        )
    ).scalars()
    return {i.bone_code: i.resolved_stage for i in items if i.resolved_stage}


def to_dict(item: AdjudicationItem) -> dict:
    return {
        "id": item.id,
        "film_key": item.film_key,
        "stage_system": item.stage_system,
        "bone_code": item.bone_code,
        "votes": json.loads(item.votes_json) if item.votes_json else {},
        "n_readers": item.n_readers,
        "status": item.status,
        "resolved_stage": item.resolved_stage,
        "resolved_by": item.resolved_by,
        "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
        "reason": item.reason,
    }
