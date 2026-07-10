"""Original-TW3 (letters A-I) 20-bone deterministic scoring engine.

Separate from the TW3-C grades engine (``scoring.py``): this scores the doctor's
letter staging over 13 RUS + 7 carpal bones, producing an INDEPENDENT RUS bone
age and carpal bone age. The two are never averaged (directive §15, §18).

Like the RUS engine it is pure and never guesses: values come only from the
clinic's own licensed tables in ``letters_tables.json``. Every component
(RUS points, carpal points, each score→age curve) is calibration-gated on its
own, so a partially-entered table still yields whatever it legitimately can and
withholds the rest.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

from .constants import CARPAL_BONES, LETTER_STAGES, RUS_BONES, SEXES
from .scoring import _interp_months  # reuse the exact interpolation used for RUS

# Overridable (like the DB path) so tests / alternate deployments never write the
# shipped template.
_TABLES_PATH = Path(os.environ.get(
    "TW3_LETTERS_TABLES_PATH", str(Path(__file__).with_name("letters_tables.json"))))
LETTER_CALCULATION_VERSION = "tw3-letters-scoring-1.0"
_CURVES = ("twii", "twiii")
_ALL20 = RUS_BONES + CARPAL_BONES  # TWII'20 uses all 20 bones with its own points


class LetterTablesError(ValueError):
    """Raised when letters_tables.json is structurally malformed."""


# ── table model ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LetterTables:
    method: str
    version: str
    source_reference: str
    rus_pts: dict            # [sex][bone][letter] -> points
    carpal_pts: dict         # [sex][carpal][letter] -> points
    rus_age: dict            # [curve][sex] -> ascending [score, years]
    carpal_age: dict         # [curve][sex] -> ascending [score, years]
    reference_cases: list
    # TWII'20 = the TW2 20-bone method: its OWN point table over all 20 bones and
    # a single score→age curve (all 20 bones sum toward one bone age).
    tw20_pts: dict = field(default_factory=dict)   # [sex][bone(any of 20)][letter] -> points
    tw20_age: dict = field(default_factory=dict)   # [sex] -> ascending [score, years]
    raw: dict = field(repr=False, default_factory=dict)

    def _pts_calibrated(self, table: dict, bones: tuple[str, ...], sex: str) -> bool:
        by_bone = table.get(sex, {})
        return all(bool(by_bone.get(b)) for b in bones)

    def rus_points_calibrated(self, sex: str) -> bool:
        return self._pts_calibrated(self.rus_pts, RUS_BONES, sex)

    def carpal_points_calibrated(self, sex: str) -> bool:
        return self._pts_calibrated(self.carpal_pts, CARPAL_BONES, sex)

    def tw20_points_calibrated(self, sex: str) -> bool:
        return self._pts_calibrated(self.tw20_pts, _ALL20, sex)

    def rus_curve_calibrated(self, curve: str, sex: str) -> bool:
        return len(self.rus_age.get(curve, {}).get(sex, [])) >= 2

    def carpal_curve_calibrated(self, curve: str, sex: str) -> bool:
        return len(self.carpal_age.get(curve, {}).get(sex, [])) >= 2

    def tw20_curve_calibrated(self, sex: str) -> bool:
        return len(self.tw20_age.get(sex, [])) >= 2

    def any_calibrated(self) -> bool:
        return any(self.rus_points_calibrated(s) or self.carpal_points_calibrated(s)
                   or self.tw20_points_calibrated(s) for s in SEXES)


def _strip_meta(d: Any) -> dict:
    """Drop leading-underscore metadata keys from a table object."""
    return {k: v for k, v in (d or {}).items() if not str(k).startswith("_")}


def _validate_pts(table: dict, bones: tuple[str, ...], name: str) -> dict:
    out: dict = {}
    for sex, by_bone in _strip_meta(table).items():
        if sex not in SEXES:
            raise LetterTablesError(f"{name}: unknown sex {sex!r}")
        clean: dict = {}
        for bone, rows in (by_bone or {}).items():
            if bone not in bones:
                raise LetterTablesError(f"{name}: unknown bone {bone!r}")
            row: dict = {}
            for letter, pts in (rows or {}).items():
                if letter not in LETTER_STAGES:
                    raise LetterTablesError(f"{name}: invalid letter {letter!r} for {bone}")
                if not isinstance(pts, (int, float)) or isinstance(pts, bool):
                    raise LetterTablesError(f"{name}: non-numeric points for {bone}/{letter}")
                row[letter] = float(pts)
            if row:
                clean[bone] = row
        out[sex] = clean
    return out


def _validate_curves(table: dict, name: str) -> dict:
    out: dict = {c: {} for c in _CURVES}
    for curve, by_sex in _strip_meta(table).items():
        if curve not in _CURVES:
            raise LetterTablesError(f"{name}: unknown curve {curve!r}")
        if not isinstance(by_sex, dict):
            continue
        for sex, anchors in _strip_meta(by_sex).items():
            if sex not in SEXES:
                raise LetterTablesError(f"{name}: unknown sex {sex!r}")
            if not isinstance(anchors, list):
                raise LetterTablesError(f"{name}: {curve}/{sex} must be a list")
            for pair in anchors:
                if (not isinstance(pair, list) or len(pair) != 2
                        or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in pair)):
                    raise LetterTablesError(f"{name}: {curve}/{sex} malformed anchor {pair!r}")
            out[curve][sex] = anchors
    return out


def _validate_sex_curve(table: dict, name: str) -> dict:
    """A single [sex] -> anchors curve (no twii/twiii split), e.g. TWII'20."""
    out: dict = {}
    for sex, anchors in _strip_meta(table).items():
        if sex not in SEXES:
            raise LetterTablesError(f"{name}: unknown sex {sex!r}")
        if not isinstance(anchors, list):
            raise LetterTablesError(f"{name}: {sex} must be a list")
        for pair in anchors:
            if (not isinstance(pair, list) or len(pair) != 2
                    or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in pair)):
                raise LetterTablesError(f"{name}: {sex} malformed anchor {pair!r}")
        out[sex] = anchors
    return out


def build_from_dict(data: dict) -> LetterTables:
    """Validate a tables dict and build the in-memory model. Raises LetterTablesError
    on any structural problem. Shared by the file loader and the save endpoint."""
    if not isinstance(data, dict):
        raise LetterTablesError("tables payload must be a JSON object")
    cases = [c for c in data.get("reference_cases", [])
             if isinstance(c, dict) and not str(c.get("id", "")).startswith(("example", "_"))
             and "_fill" not in c]
    return LetterTables(
        method=data.get("method", "TW3-letters"),
        version=data.get("version", "letters-0-uncalibrated"),
        source_reference=data.get("source_reference", ""),
        rus_pts=_validate_pts(data.get("rus_stage_to_score", {}), RUS_BONES, "rus_stage_to_score"),
        carpal_pts=_validate_pts(data.get("carpal_stage_to_score", {}), CARPAL_BONES, "carpal_stage_to_score"),
        rus_age=_validate_curves(data.get("rus_score_to_age", {}), "rus_score_to_age"),
        carpal_age=_validate_curves(data.get("carpal_score_to_age", {}), "carpal_score_to_age"),
        reference_cases=cases,
        tw20_pts=_validate_pts(data.get("tw20_stage_to_score", {}), _ALL20, "tw20_stage_to_score"),
        tw20_age=_validate_sex_curve(data.get("tw20_score_to_age", {}), "tw20_score_to_age"),
        raw=data,
    )


def load_letter_tables(path: Path = _TABLES_PATH) -> LetterTables:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LetterTablesError(f"letters tables file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LetterTablesError(f"letters tables file is not valid JSON: {exc}") from exc
    return build_from_dict(data)


def load_raw_tables(path: Path = _TABLES_PATH) -> dict:
    """Raw JSON for editing in the UI (keeps _fill hints and example cases)."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_letter_tables(data: dict, path: Path = _TABLES_PATH) -> LetterTables:
    """Validate then atomically write the tables file. Never writes an invalid file."""
    tables = build_from_dict(data)          # raises LetterTablesError if malformed
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    return tables


# ── scoring ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GroupResult:
    """One bone group (RUS or carpal) scored independently."""
    group: str
    total_score: float
    staged_count: int
    total_bones: int
    complete: bool
    points_calibrated: bool
    twii_age_months: Optional[int]
    twiii_age_months: Optional[int]
    missing_stage: tuple[str, ...]
    missing_score: tuple[str, ...]

    def _years(self, m: Optional[int]) -> Optional[float]:
        return None if m is None else round(m / 12, 2)

    @property
    def twii_age_years(self) -> Optional[float]:
        return self._years(self.twii_age_months)

    @property
    def twiii_age_years(self) -> Optional[float]:
        return self._years(self.twiii_age_months)


@dataclass(frozen=True)
class Tw20Result:
    """TWII'20 = the TW2 20-bone method: one score over all 20 bones, one bone age."""
    total_score: float
    staged_count: int
    total_bones: int
    complete: bool
    points_calibrated: bool
    age_months: Optional[int]
    missing_stage: tuple[str, ...]
    missing_score: tuple[str, ...]

    @property
    def age_years(self) -> Optional[float]:
        return None if self.age_months is None else round(self.age_months / 12, 2)


@dataclass(frozen=True)
class LetterResult:
    method: str
    table_version: str
    calculation_version: str
    sex: str
    rus: GroupResult
    carpal: GroupResult
    tw20: Tw20Result


def _score_group(stages: Mapping[str, str], bones: tuple[str, ...], sex: str,
                 pts_table: dict, age_curves: dict, group: str) -> GroupResult:
    by_bone = pts_table.get(sex, {})
    total = 0.0
    staged = 0
    missing_stage: list[str] = []
    missing_score: list[str] = []
    for bone in bones:
        letter = stages.get(bone)
        if not letter:
            missing_stage.append(bone)
            continue
        if letter not in LETTER_STAGES:
            raise ValueError(f"invalid letter {letter!r} for {bone}")
        staged += 1
        pts = (by_bone.get(bone) or {}).get(letter)
        if isinstance(pts, (int, float)) and not isinstance(pts, bool):
            total += float(pts)
        else:
            missing_score.append(bone)

    points_calibrated = all(bool(by_bone.get(b)) for b in bones)
    complete = staged == len(bones) and not missing_score
    twii = (_interp_months(age_curves.get("twii", {}).get(sex, []), total)
            if complete else None)
    twiii = (_interp_months(age_curves.get("twiii", {}).get(sex, []), total)
             if complete else None)
    return GroupResult(
        group=group, total_score=total, staged_count=staged, total_bones=len(bones),
        complete=complete, points_calibrated=points_calibrated,
        twii_age_months=twii, twiii_age_months=twiii,
        missing_stage=tuple(missing_stage), missing_score=tuple(missing_score),
    )


def _score_tw20(rus_stages: Mapping[str, str], carpal_stages: Mapping[str, str],
                sex: str, tables: LetterTables) -> Tw20Result:
    """TWII'20: sum the TW2 20-bone points over all 20 bones → one bone age."""
    by_bone = tables.tw20_pts.get(sex, {})
    combined = {**{b: rus_stages.get(b) for b in RUS_BONES},
                **{c: carpal_stages.get(c) for c in CARPAL_BONES}}
    total = 0.0
    staged = 0
    missing_stage: list[str] = []
    missing_score: list[str] = []
    for bone in _ALL20:
        letter = combined.get(bone)
        if not letter:
            missing_stage.append(bone)
            continue
        if letter not in LETTER_STAGES:
            raise ValueError(f"invalid letter {letter!r} for {bone}")
        staged += 1
        pts = (by_bone.get(bone) or {}).get(letter)
        if isinstance(pts, (int, float)) and not isinstance(pts, bool):
            total += float(pts)
        else:
            missing_score.append(bone)
    complete = staged == len(_ALL20) and not missing_score
    age = _interp_months(tables.tw20_age.get(sex, []), total) if complete else None
    return Tw20Result(
        total_score=total, staged_count=staged, total_bones=len(_ALL20),
        complete=complete, points_calibrated=all(bool(by_bone.get(b)) for b in _ALL20),
        age_months=age, missing_stage=tuple(missing_stage), missing_score=tuple(missing_score),
    )


def compute_letters(rus_stages: Mapping[str, str], carpal_stages: Mapping[str, str],
                    sex: str, tables: Optional[LetterTables] = None) -> LetterResult:
    """Score the 13 RUS + 7 carpal letters into INDEPENDENT RUS, carpal and TWII'20 ages."""
    if sex not in SEXES:
        raise ValueError(f"unsupported sex {sex!r}")
    tables = tables or load_letter_tables()
    return LetterResult(
        method=tables.method,
        table_version=tables.version,
        calculation_version=LETTER_CALCULATION_VERSION,
        sex=sex,
        rus=_score_group(rus_stages, RUS_BONES, sex, tables.rus_pts, tables.rus_age, "rus"),
        carpal=_score_group(carpal_stages, CARPAL_BONES, sex, tables.carpal_pts,
                            tables.carpal_age, "carpal"),
        tw20=_score_tw20(rus_stages, carpal_stages, sex, tables),
    )


# ── accuracy gate: reproduce the clinic's known cases ────────────────────────

def validate_reference_cases(tables: Optional[LetterTables] = None) -> dict:
    """Re-score the clinic's own historically-reported films with the entered
    tables and compare to their reported scores/ages. Scoring must not be trusted
    (or enabled) unless every reference case reproduces within tolerance — this is
    the transcription/accuracy guard (directive: accuracy is paramount)."""
    tables = tables or load_letter_tables()
    results: list[dict] = []
    for case in tables.reference_cases:
        sex = case.get("sex")
        exp = case.get("expected", {}) or {}
        tol = float(case.get("tolerance_years", 0.3))
        if sex not in SEXES:
            results.append({"id": case.get("id"), "ok": False, "reason": "bad sex"})
            continue
        r = compute_letters(case.get("rus_stages", {}) or {},
                            case.get("carpal_stages", {}) or {}, sex, tables)
        checks: list[dict] = []

        def _num(v):
            return isinstance(v, (int, float)) and not isinstance(v, bool)

        def check(label, got, want, is_age):
            if not _num(want):
                return  # nothing to compare against
            if got is None:
                checks.append({"field": label, "ok": False, "got": None, "want": want})
                return
            ok = abs(got - want) <= (tol if is_age else 0.5)
            checks.append({"field": label, "ok": ok, "got": got, "want": want})

        check("rus_score", r.rus.total_score, exp.get("rus_score"), False)
        check("twii_rus_age_years", r.rus.twii_age_years, exp.get("twii_rus_age_years"), True)
        check("twiii_rus_age_years", r.rus.twiii_age_years, exp.get("twiii_rus_age_years"), True)
        check("carpal_score", r.carpal.total_score, exp.get("carpal_score"), False)
        check("twiii_carpal_age_years", r.carpal.twiii_age_years, exp.get("twiii_carpal_age_years"), True)
        check("tw20_score", r.tw20.total_score, exp.get("tw20_score"), False)
        check("twii20_age_years", r.tw20.age_years, exp.get("twii20_age_years"), True)

        ok = bool(checks) and all(c["ok"] for c in checks)
        results.append({"id": case.get("id"), "ok": ok, "sex": sex, "checks": checks})

    return {
        "n_cases": len(results),
        "all_passed": bool(results) and all(c["ok"] for c in results),
        "cases": results,
    }


def letters_status() -> dict:
    """Machine-readable calibration status for the UI (what is / isn't enterable)."""
    t = load_letter_tables()
    per_sex = {
        sex: {
            "rus_points": t.rus_points_calibrated(sex),
            "carpal_points": t.carpal_points_calibrated(sex),
            "rus_twii_curve": t.rus_curve_calibrated("twii", sex),
            "rus_twiii_curve": t.rus_curve_calibrated("twiii", sex),
            "carpal_twii_curve": t.carpal_curve_calibrated("twii", sex),
            "carpal_twiii_curve": t.carpal_curve_calibrated("twiii", sex),
            "tw20_points": t.tw20_points_calibrated(sex),
            "tw20_curve": t.tw20_curve_calibrated(sex),
        }
        for sex in SEXES
    }
    validation = validate_reference_cases(t)
    return {
        "method": t.method,
        "version": t.version,
        "source_reference": t.source_reference,
        "any_calibrated": t.any_calibrated(),
        "per_sex": per_sex,
        "reference_validation": validation,
        "scoring_ready": t.any_calibrated() and validation["all_passed"],
    }
