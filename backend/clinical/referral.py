"""Triage and specialty routing (M5).

This is the highest-risk feature in the product and it is deliberately the most
constrained. The design rules below are enforced by tests, not just documented.

**Three levels, and none of them is reassuring.** The enum contains
``routine_monitoring``, ``discuss_with_paediatrician`` and ``specialist_soon``.
There is deliberately no "minor", "benign", "normal" or "no action" state, and
``test_referral.py`` fails if one is ever added. Anthropometry can tell you that
something needs looking at; it can almost never tell you that something is fine.
A tool that once said "this looks minor" about a child whose growth failure was
caused by a brain tumour would be finished, and rightly.

**It escalates, never de-escalates.** The absence of findings produces
``routine_monitoring`` -- keep watching -- not an all-clear.

**It routes toward a clinician, never away from one.** Every level names a next
conversation.
"""
from __future__ import annotations

from dataclasses import dataclass

from .snapshot import ATTENTION, INSUFFICIENT_DATA, URGENT, Finding

# The complete set. Nothing here tells anyone they are fine.
ROUTINE_MONITORING = "routine_monitoring"
DISCUSS_WITH_PAEDIATRICIAN = "discuss_with_paediatrician"
SPECIALIST_SOON = "specialist_soon"

TRIAGE_LEVELS: tuple[str, ...] = (
    ROUTINE_MONITORING, DISCUSS_WITH_PAEDIATRICIAN, SPECIALIST_SOON,
)

_LEVEL_RANK = {ROUTINE_MONITORING: 0, DISCUSS_WITH_PAEDIATRICIAN: 1, SPECIALIST_SOON: 2}

_GUIDANCE = {
    ROUTINE_MONITORING: (
        "Nothing here requires urgent action. Keep measuring at the usual "
        "interval — growth is judged over time, not from one visit."
    ),
    DISCUSS_WITH_PAEDIATRICIAN: (
        "One or more findings are worth raising at the next paediatric "
        "appointment. Bring the growth record."
    ),
    SPECIALIST_SOON: (
        "One or more findings warrant specialist assessment without waiting for "
        "a routine appointment."
    ),
}


@dataclass(frozen=True)
class Triage:
    level: str
    reason: str
    guidance: str
    specialties: tuple[str, ...]
    driving_findings: tuple[str, ...]
    not_assessed: tuple[str, ...]


def triage(findings: list[Finding]) -> Triage:
    """Map findings onto a level. Escalates only."""
    level = ROUTINE_MONITORING
    driving: list[str] = []
    specialties: list[str] = []

    for f in findings:
        if f.severity == URGENT:
            candidate = SPECIALIST_SOON
        elif f.severity == ATTENTION:
            candidate = DISCUSS_WITH_PAEDIATRICIAN
        else:
            continue
        if _LEVEL_RANK[candidate] >= _LEVEL_RANK[level]:
            if _LEVEL_RANK[candidate] > _LEVEL_RANK[level]:
                driving = []
                level = candidate
            driving.append(f.rule_id)
        specialties.extend(f.suggests_specialty)

    not_assessed = tuple(f.rule_id for f in findings if f.severity == INSUFFICIENT_DATA)

    if level == ROUTINE_MONITORING:
        reason = "No finding in this assessment reached the attention threshold."
        if not_assessed:
            reason += (
                f" Note that {len(not_assessed)} check(s) could not run because "
                "the required measurements were not recorded — that is not the "
                "same as those checks passing."
            )
    else:
        reason = f"Driven by: {', '.join(driving)}."

    return Triage(level, reason, _GUIDANCE[level],
                  tuple(dict.fromkeys(specialties)), tuple(driving), not_assessed)


def parent_summary(findings: list[Finding], t: Triage) -> dict:
    """Plain-language output for a parent.

    Reports OBSERVATIONS and a suggested conversation — never a diagnosis, never
    a probability, never reassurance. Gated behind clinician release at the API
    layer; this function only shapes the words.
    """
    lines = [
        f.title for f in findings
        if f.severity in (URGENT, ATTENTION)
    ]
    return {
        "what_was_looked_at": "Your child's height, weight and growth over time.",
        "what_was_noticed": lines or ["Nothing that needed flagging at this visit."],
        "what_to_do": t.guidance,
        "questions_to_ask": _questions(findings),
        "important": (
            "This is a summary of measurements, not a diagnosis. Growth is only "
            "one signal and it cannot rule anything out. Any concern about your "
            "child should be discussed with a doctor."
        ),
    }


def _questions(findings: list[Finding]) -> list[str]:
    """Questions generated from what actually fired, so a parent walks in able to
    ask about the specific thing rather than a generic list.

    Only rules that FIRED count. A rule that could not run still produces an
    ``insufficient_data`` finding under its own rule_id, and counting those told
    a parent to ask "what does the bone age result mean" about a child who has
    never had a bone-age film."""
    ids = {f.rule_id for f in findings if f.severity != INSUFFICIENT_DATA}
    questions: list[str] = []
    if {"SHORT_STATURE", "SEVERE_SHORT_STATURE"} & ids:
        questions.append("Is my child's height outside the normal range for their age?")
    if "DOWNWARD_CENTILE_CROSSING" in ids or "LOW_HEIGHT_VELOCITY" in ids:
        questions.append("Has my child's growth rate slowed, and do we know why?")
    if "BELOW_TARGET_HEIGHT" in ids:
        questions.append("How does my child's growth compare with our family's heights?")
    if "BONE_AGE_DISCREPANCY" in ids:
        questions.append("What does the bone age result mean for my child's growth ahead?")
    if {"DELAYED_PUBERTY", "PRECOCIOUS_PUBERTY", "EARLY_MENARCHE"} & ids:
        questions.append("Is my child's pubertal development happening at the usual time?")
    if "DISPROPORTION" in ids:
        questions.append("Should my child's body proportions be looked at more closely?")
    if any(f.severity == INSUFFICIENT_DATA for f in findings):
        questions.append("Are there measurements we should be taking that we are not?")
    return questions or ["Is there anything about my child's growth I should watch for?"]
