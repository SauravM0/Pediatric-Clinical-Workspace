"""The rule set and the engine that runs it (M5).

Pure. Every rule is a function ``(PatientSnapshot) -> Finding | None`` plus a
declaration of what it needs. The engine checks the declaration first, so a rule
whose inputs are missing emits an explicit ``insufficient_data`` finding rather
than silently not firing -- silence would be indistinguishable from "checked and
fine", which is the most dangerous output a decision-support tool can produce.

Two behaviours that are easy to skip and shouldn't be:

* **Suppression.** A child at height SDS -3.2 legitimately trips short stature,
  severe short stature, and below-target-height at once. Three alarms for one
  problem is how clinicians learn to ignore the panel. Each rule declares what
  it makes redundant and the engine applies a precedence pass.
* **Thresholds live in thresholds.json**, each with a source, so changing a
  number is a reviewed diff rather than an edit buried in a conditional.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional

from .snapshot import (
    ATTENTION,
    INSUFFICIENT_DATA,
    SEVERITY_ORDER,
    URGENT,
    Finding,
    PatientSnapshot,
    insufficient,
)

_THRESHOLDS_PATH = Path(__file__).with_name("thresholds.json")


@lru_cache(maxsize=1)
def thresholds() -> dict:
    return json.loads(_THRESHOLDS_PATH.read_text(encoding="utf-8"))


def T(name: str) -> float:
    return float(thresholds()[name]["value"])


def SRC(name: str) -> str:
    return str(thresholds()[name]["source"])


def CONF(name: str) -> str:
    return str(thresholds()[name].get("confidence", "moderate"))


@dataclass(frozen=True)
class Rule:
    rule_id: str
    requires: tuple[str, ...]
    describe: str
    evaluate: Callable[[PatientSnapshot], Optional[Finding]]


_REGISTRY: list[Rule] = []


def rule(rule_id: str, requires: tuple[str, ...], describe: str):
    def wrap(fn: Callable[[PatientSnapshot], Optional[Finding]]):
        _REGISTRY.append(Rule(rule_id, requires, describe, fn))
        return fn
    return wrap


def registry() -> tuple[Rule, ...]:
    return tuple(_REGISTRY)


# ── growth ──────────────────────────────────────────────────────────────────

@rule("SEVERE_SHORT_STATURE", ("height",), "Height below -3 SD")
def _severe_short(s: PatientSnapshot) -> Optional[Finding]:
    z = s.height.sds
    if z is None or z > T("severe_short_stature_sds"):
        return None
    return Finding(
        "SEVERE_SHORT_STATURE", URGENT, "Severe short stature",
        f"Height is {z:+.2f} SD, below the -3 SD threshold. A pathological cause "
        "is likely; paediatric endocrinology referral is indicated.",
        {"height_sds": round(z, 2), "height_cm": s.height.value,
         "age_years": s.height.age_years, "threshold_sds": T("severe_short_stature_sds")},
        SRC("severe_short_stature_sds"), CONF("severe_short_stature_sds"),
        suppresses=("SHORT_STATURE", "BELOW_TARGET_HEIGHT"),
        suggests_specialty=("paediatric endocrinology",),
    )


@rule("SHORT_STATURE", ("height",), "Height below -2 SD")
def _short(s: PatientSnapshot) -> Optional[Finding]:
    z = s.height.sds
    if z is None or z > T("short_stature_sds"):
        return None
    return Finding(
        "SHORT_STATURE", ATTENTION, "Short stature",
        f"Height is {z:+.2f} SD, below the -2 SD threshold (about the 3rd centile).",
        {"height_sds": round(z, 2), "height_cm": s.height.value,
         "age_years": s.height.age_years, "threshold_sds": T("short_stature_sds")},
        SRC("short_stature_sds"), CONF("short_stature_sds"),
        suggests_specialty=("paediatric endocrinology",),
    )


@rule("TALL_STATURE", ("height",), "Height above +3 SD")
def _tall(s: PatientSnapshot) -> Optional[Finding]:
    z = s.height.sds
    if z is None or z < T("tall_stature_sds"):
        return None
    return Finding(
        "TALL_STATURE", ATTENTION, "Tall stature",
        f"Height is {z:+.2f} SD, above the +3 SD threshold; evaluation is warranted.",
        {"height_sds": round(z, 2), "threshold_sds": T("tall_stature_sds")},
        SRC("tall_stature_sds"), CONF("tall_stature_sds"),
        suggests_specialty=("paediatric endocrinology", "clinical genetics"),
    )


@rule("DOWNWARD_CENTILE_CROSSING", ("height_history",),
      "Sustained fall of more than one centile channel after age 3")
def _crossing(s: PatientSnapshot) -> Optional[Finding]:
    scored = [m for m in s.height_history
              if m.sds is not None and m.age_years >= T("velocity_rule_min_age_years")]
    if len(scored) < 2:
        return None
    first, last = scored[0], scored[-1]
    interval = last.age_years - first.age_years
    if interval < T("centile_crossing_min_interval_years"):
        return None
    change = last.sds - first.sds
    if change > T("sds_fall_one_channel"):
        return None
    return Finding(
        "DOWNWARD_CENTILE_CROSSING", URGENT, "Falling across centiles",
        f"Height SDS fell from {first.sds:+.2f} to {last.sds:+.2f} "
        f"({change:+.2f} SD) between ages {first.age_years:.1f} and {last.age_years:.1f}. "
        "A single low measurement can be constitutional; a sustained fall is not, "
        "and is the pattern that most reliably separates a growth disorder from a "
        "normally short child.",
        {"sds_from": round(first.sds, 2), "sds_to": round(last.sds, 2),
         "change_sds": round(change, 2), "interval_years": round(interval, 2),
         "threshold_sds": T("sds_fall_one_channel")},
        SRC("sds_fall_one_channel"), CONF("sds_fall_one_channel"),
        suggests_specialty=("paediatric endocrinology",),
    )


@rule("LOW_HEIGHT_VELOCITY", ("height_velocities",), "Height velocity below the expected range")
def _velocity(s: PatientSnapshot) -> Optional[Finding]:
    """Prefers a real centile; falls back to a coarse floor.

    The correct test is velocity below the 25th centile for age, because the
    same 4.5 cm/year is unremarkable at 7 and alarming mid-puberty. That needs
    the published Indian velocity reference (M1.3). Until it is installed the
    rule uses a flat 4 cm/year floor and says so, at low confidence.
    """
    usable = [v for v in s.height_velocities if v[0] >= T("velocity_rule_min_age_years")]
    if not usable:
        return None
    latest = usable[-1]
    from_age, to_age, rate = latest[0], latest[1], latest[2]
    # This interval's OWN SDS, never the snapshot's "latest scorable" one --
    # see PatientSnapshot.height_velocities. Absent when the reference is not
    # installed or when this interval falls outside the band it can score.
    sds = latest[3] if len(latest) > 3 else None

    if sds is not None:
        # Real centile available. -0.674 SD is the 25th centile.
        if sds > T("low_velocity_sds"):
            return None
        severe = sds <= T("severe_low_velocity_sds")
        return Finding(
            "LOW_HEIGHT_VELOCITY", URGENT if severe else ATTENTION,
            "Low height velocity",
            f"Height velocity was {rate:.1f} cm/year between ages {from_age:.1f} and "
            f"{to_age:.1f} — {sds:+.2f} SD against the Indian velocity reference"
            f"{', below the 3rd centile' if severe else ', below the 25th centile'}.",
            {"velocity_cm_per_year": round(rate, 2),
             "velocity_sds": round(sds, 2),
             "from_age_years": round(from_age, 2), "to_age_years": round(to_age, 2),
             "threshold_sds": T("low_velocity_sds")},
            SRC("low_velocity_sds"), CONF("low_velocity_sds"),
            suggests_specialty=("paediatric endocrinology",),
        )

    if rate >= T("low_height_velocity_cm_per_year"):
        return None
    return Finding(
        "LOW_HEIGHT_VELOCITY", ATTENTION, "Low height velocity",
        f"Height velocity was {rate:.1f} cm/year between ages {from_age:.1f} and "
        f"{to_age:.1f}, below the {T('low_height_velocity_cm_per_year'):.0f} cm/year screen. "
        "This is a coarse floor, not a centile: the correct test is velocity below "
        "the 25th centile for age, which needs a velocity reference this product "
        "does not yet hold.",
        {"velocity_cm_per_year": round(rate, 2), "from_age_years": round(from_age, 2),
         "to_age_years": round(to_age, 2),
         "threshold_cm_per_year": T("low_height_velocity_cm_per_year")},
        SRC("low_height_velocity_cm_per_year"), CONF("low_height_velocity_cm_per_year"),
        suggests_specialty=("paediatric endocrinology",),
    )


@rule("BELOW_TARGET_HEIGHT", ("height", "target_height_sds"),
      "Height well below the mid-parental target")
def _below_target(s: PatientSnapshot) -> Optional[Finding]:
    """Compares SDS with SDS, never centimetres with an adult target.

    The naive form -- current height in cm against the mid-parental target in cm
    -- fires for essentially every child under fifteen, because a 7-year-old IS
    30 cm shorter than their adult target. Both sides must be on the same scale:
    the child's height SDS against the target expressed as an adult height SDS.
    """
    if s.height.sds is None:
        return None
    gap_sds = s.height.sds - s.target_height_sds
    if gap_sds > T("below_target_height_sds"):
        return None
    return Finding(
        "BELOW_TARGET_HEIGHT", ATTENTION, "Height below genetic potential",
        f"Height is {s.height.sds:+.2f} SD while the mid-parental target sits at "
        f"{s.target_height_sds:+.2f} SD — a shortfall of {abs(gap_sds):.2f} SD "
        "against this family's own expectation. A child can be within the normal "
        "range and still be well below where their genetics point.",
        {"height_sds": round(s.height.sds, 2),
         "target_height_sds": round(s.target_height_sds, 2),
         "gap_sds": round(gap_sds, 2),
         "threshold_sds": T("below_target_height_sds"),
         "parental_height_source": s.parental_height_source},
        SRC("below_target_height_sds"),
        "low" if s.parental_height_source != "measured" else CONF("below_target_height_sds"),
        suggests_specialty=("paediatric endocrinology",),
    )


@rule("SGA_WITHOUT_CATCH_UP", ("birth_weight_g", "age_years", "height"),
      "Low birth weight without catch-up by age 2")
def _sga(s: PatientSnapshot) -> Optional[Finding]:
    if s.birth_weight_g >= T("sga_birth_weight_g"):
        return None
    if s.age_years < T("sga_catch_up_age_years"):
        return None
    if s.height.sds is None or s.height.sds >= T("short_stature_sds"):
        return None
    return Finding(
        "SGA_WITHOUT_CATCH_UP", URGENT, "Small for gestational age without catch-up",
        f"Birth weight {s.birth_weight_g:.0f} g with height still {s.height.sds:+.2f} SD "
        f"at age {s.age_years:.1f}. Absence of catch-up growth by age 2 is a referral "
        "criterion in its own right.",
        {"birth_weight_g": s.birth_weight_g, "height_sds": round(s.height.sds, 2),
         "age_years": round(s.age_years, 2)},
        SRC("sga_catch_up_age_years"), CONF("sga_catch_up_age_years"),
        suppresses=("SHORT_STATURE",),
        suggests_specialty=("paediatric endocrinology",),
    )


@rule("DISPROPORTION", ("arm_span_cm", "height"), "Arm span differs markedly from height")
def _disproportion(s: PatientSnapshot) -> Optional[Finding]:
    diff = s.arm_span_cm - s.height.value
    limit = T("arm_span_height_difference_cm")
    if abs(diff) <= limit:
        return None
    direction = ("exceeds height" if diff > 0 else "is below height")
    return Finding(
        "DISPROPORTION", ATTENTION, "Possible disproportionate growth",
        f"Arm span {direction} by {abs(diff):.1f} cm. Disproportion points toward a "
        "skeletal dysplasia rather than an endocrine cause, which is a different "
        "work-up. This is a coarse screen -- the proper test uses age- and "
        "sex-specific segment references that are not yet bundled.",
        {"arm_span_cm": s.arm_span_cm, "height_cm": s.height.value,
         "difference_cm": round(diff, 1), "threshold_cm": limit},
        SRC("arm_span_height_difference_cm"), CONF("arm_span_height_difference_cm"),
        suggests_specialty=("clinical genetics", "paediatric orthopaedics"),
    )


@rule("BONE_AGE_DISCREPANCY", ("bone_age_years", "bone_age_chronological_years"),
      "Bone age more than 2 years from chronological age at the film")
def _bone_age(s: PatientSnapshot) -> Optional[Finding]:
    # Against the age AT THE FILM, not the latest measurement: comparing an old
    # film with today's age manufactures a delay equal to the film's age.
    ca = s.bone_age_chronological_years
    diff = s.bone_age_years - ca
    if abs(diff) <= T("bone_age_discrepancy_years"):
        return None
    word = "advanced" if diff > 0 else "delayed"
    return Finding(
        "BONE_AGE_DISCREPANCY", ATTENTION, f"Skeletal maturity {word}",
        f"Bone age {s.bone_age_years:.1f} y against chronological age "
        f"{ca:.1f} y at the film ({diff:+.1f} y). Interpret with the method's own "
        "uncertainty: the active curve is provisional and digitized, so a "
        "discrepancy near the threshold may be method error rather than biology.",
        {"bone_age_years": s.bone_age_years, "chronological_age_years": round(ca, 2),
         "difference_years": round(diff, 2), "method": s.bone_age_method},
        SRC("bone_age_discrepancy_years"), CONF("bone_age_discrepancy_years"),
        suggests_specialty=("paediatric endocrinology",),
    )


# ── puberty ─────────────────────────────────────────────────────────────────

@rule("DELAYED_PUBERTY", ("age_years",), "No pubertal onset by the expected age")
def _delayed_puberty(s: PatientSnapshot) -> Optional[Finding]:
    if s.sex == "girls":
        if s.breast_stage is None:
            return None
        if s.age_years < T("delayed_puberty_age_girls") or s.breast_stage > 1:
            return None
        detail = f"no breast development (Tanner B{s.breast_stage}) at age {s.age_years:.1f}"
        used = {"breast_stage": s.breast_stage, "age_years": round(s.age_years, 2),
                "threshold_age": T("delayed_puberty_age_girls")}
        src = SRC("delayed_puberty_age_girls")
    else:
        if s.testicular_volume_ml is None:
            return None
        if (s.age_years < T("delayed_puberty_age_boys")
                or s.testicular_volume_ml >= T("testicular_volume_pubertal_ml")):
            return None
        detail = (f"testicular volume {s.testicular_volume_ml:.0f} mL at age "
                  f"{s.age_years:.1f}")
        used = {"testicular_volume_ml": s.testicular_volume_ml,
                "age_years": round(s.age_years, 2),
                "threshold_age": T("delayed_puberty_age_boys")}
        src = SRC("delayed_puberty_age_boys")

    return Finding(
        "DELAYED_PUBERTY", URGENT, "Delayed puberty",
        f"Pubertal onset has not occurred: {detail}. Endocrine referral is indicated.",
        used, src, "high", suggests_specialty=("paediatric endocrinology",),
    )


@rule("PRECOCIOUS_PUBERTY", ("age_years",), "Pubertal onset earlier than expected")
def _precocious(s: PatientSnapshot) -> Optional[Finding]:
    if s.sex == "girls":
        started = (s.breast_stage or 0) >= 2 or bool(s.menarche_reached)
        limit = T("precocious_puberty_age_girls")
        used = {"breast_stage": s.breast_stage, "menarche_reached": s.menarche_reached,
                "age_years": round(s.age_years, 2), "threshold_age": limit}
        src = SRC("precocious_puberty_age_girls")
    else:
        started = (s.testicular_volume_ml or 0) >= T("testicular_volume_pubertal_ml") \
            or (s.genital_stage or 0) >= 2
        limit = T("precocious_puberty_age_boys")
        used = {"testicular_volume_ml": s.testicular_volume_ml,
                "genital_stage": s.genital_stage,
                "age_years": round(s.age_years, 2), "threshold_age": limit}
        src = SRC("precocious_puberty_age_boys")

    if not started or s.age_years >= limit:
        return None
    return Finding(
        "PRECOCIOUS_PUBERTY", URGENT, "Precocious puberty",
        f"Signs of puberty at age {s.age_years:.1f}, before the age-{limit:.0f} "
        "threshold. Endocrine referral is indicated.",
        used, src, "high", suggests_specialty=("paediatric endocrinology",),
    )


@rule("EARLY_MENARCHE", ("age_years", "menarche_reached"), "Menarche before age 8")
def _early_menarche(s: PatientSnapshot) -> Optional[Finding]:
    if s.sex != "girls" or not s.menarche_reached:
        return None
    if s.age_years >= T("early_menarche_age_years"):
        return None
    return Finding(
        "EARLY_MENARCHE", URGENT, "Menarche before age 8",
        f"Menarche recorded at age {s.age_years:.1f}. This requires endocrine evaluation.",
        {"age_years": round(s.age_years, 2), "threshold_age": T("early_menarche_age_years")},
        SRC("early_menarche_age_years"), "high",
        suppresses=("PRECOCIOUS_PUBERTY",),
        suggests_specialty=("paediatric endocrinology",),
    )


# ── engine ──────────────────────────────────────────────────────────────────

def evaluate(snapshot: PatientSnapshot, *,
             include_insufficient: bool = True) -> list[Finding]:
    """Run every rule, then apply suppression.

    Returns findings sorted most-severe first. ``insufficient_data`` entries are
    included by default: a clinician must be able to see that a check did not
    run, rather than reading a clean panel as a clean child.
    """
    fired: list[Finding] = []
    gaps: list[Finding] = []

    for r in registry():
        missing = [f for f in r.requires if not snapshot.has(f)]
        if missing:
            gaps.append(insufficient(r.rule_id, missing, r.describe))
            continue
        try:
            result = r.evaluate(snapshot)
        except Exception as exc:  # a broken rule must not take down the panel
            gaps.append(Finding(
                r.rule_id, INSUFFICIENT_DATA, f"Rule error: {r.describe}",
                f"This check could not be completed ({type(exc).__name__}). "
                "Treat as not assessed.", {"error": str(exc)}, confidence="high"))
            continue
        if result is not None:
            fired.append(result)

    suppressed = {rid for f in fired for rid in f.suppresses}
    kept = [f for f in fired if f.rule_id not in suppressed]

    if include_insufficient:
        # Only report a gap for a check that nothing else already covers.
        covered = {f.rule_id for f in kept} | suppressed
        kept += [g for g in gaps if g.rule_id not in covered]

    return sorted(kept, key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.rule_id))
