"""Load and validate the TW3-RUS conversion tables (directive §10).

One canonical data source: ``tw3_tables.json``. This module loads it, checks
structural integrity and (optional) checksum, and reports whether the tables are
*calibrated* — i.e. whether the sex-specific stage→score points and the
score→age curve are actually present. The deterministic engine refuses to output
a bone age unless the relevant part of the table is calibrated; nothing is ever
guessed.

Fail-fast (raises ``TablesError`` at load): malformed JSON, missing method or
version, unknown bone codes, duplicated stages, non-numeric scores, or a
checksum that does not match. Missing *values* (empty tables) do NOT crash the
app — they leave the tables ``uncalibrated`` so the manual workflow still runs.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .constants import RUS_BONES, SEXES, STAGES

_TABLES_PATH = Path(__file__).with_name("tw3_tables.json")


class TablesError(ValueError):
    """Raised when the TW3 tables file is malformed or fails integrity checks."""


def _canonical_bytes(data: dict[str, Any]) -> bytes:
    """Deterministic serialization of the table content, excluding the checksum
    field itself, so a checksum can be computed and verified reproducibly."""
    payload = {k: v for k, v in data.items() if k != "checksum"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_checksum(data: dict[str, Any]) -> str:
    """SHA-256 of the canonical table content (excluding the checksum field)."""
    return hashlib.sha256(_canonical_bytes(data)).hexdigest()


@dataclass(frozen=True)
class ScoringTables:
    """Validated, in-memory view of the TW3-RUS tables."""

    method: str
    version: str
    source_reference: str
    stage_to_score: dict[str, dict[str, dict[str, float]]]  # [sex][bone][stage] -> pts
    score_to_age: dict[str, list[list[float]]]  # [sex] -> ascending [score, ageYears]
    allowed_stages: dict[str, tuple[str, ...]]  # [bone] -> stages valid for that bone
    min_age_years: float
    max_age_years: float
    checksum_verified: bool
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    def is_calibrated(self, sex: str) -> bool:
        """True only if every RUS bone has a score row and the age curve exists."""
        tbl = self.stage_to_score.get(sex, {})
        if not tbl or sex not in self.score_to_age or len(self.score_to_age[sex]) < 2:
            return False
        return all(tbl.get(bone) for bone in RUS_BONES)

    def stages_for(self, bone: str) -> tuple[str, ...]:
        return self.allowed_stages.get(bone, STAGES)


def _validate_structure(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise TablesError("tables file must be a JSON object")
    if not data.get("method"):
        raise TablesError("tables file is missing 'method'")
    if not data.get("version"):
        raise TablesError("tables file is missing 'version' (directive §10, §24)")

    sts = data.get("stage_to_score", {})
    if not isinstance(sts, dict):
        raise TablesError("'stage_to_score' must be an object")
    for sex, bones in sts.items():
        if sex.startswith("_"):
            continue
        if sex not in SEXES:
            raise TablesError(f"unknown sex '{sex}' in stage_to_score")
        if not isinstance(bones, dict):
            raise TablesError(f"stage_to_score['{sex}'] must be an object")
        for bone, rows in bones.items():
            if bone not in RUS_BONES:
                raise TablesError(f"unknown bone code '{bone}' in stage_to_score['{sex}']")
            if not isinstance(rows, dict):
                raise TablesError(f"stage_to_score['{sex}']['{bone}'] must be an object")
            seen: set[str] = set()
            for stage, pts in rows.items():
                if stage in seen:
                    raise TablesError(f"duplicate stage '{stage}' for {sex}/{bone}")
                seen.add(stage)
                if stage not in STAGES:
                    raise TablesError(f"invalid stage '{stage}' for {sex}/{bone}")
                if not isinstance(pts, (int, float)) or isinstance(pts, bool):
                    raise TablesError(f"non-numeric score for {sex}/{bone}/{stage}: {pts!r}")

    s2a = data.get("score_to_age", {})
    if not isinstance(s2a, dict):
        raise TablesError("'score_to_age' must be an object")
    for sex, anchors in s2a.items():
        if sex.startswith("_"):
            continue
        if sex not in SEXES:
            raise TablesError(f"unknown sex '{sex}' in score_to_age")
        if not isinstance(anchors, list):
            raise TablesError(f"score_to_age['{sex}'] must be a list of [score, age] pairs")
        for pair in anchors:
            if (not isinstance(pair, list) or len(pair) != 2
                    or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in pair)):
                raise TablesError(f"score_to_age['{sex}'] has a malformed anchor: {pair!r}")


def _derive_allowed_stages(sts: dict[str, dict[str, dict[str, float]]]) -> dict[str, tuple[str, ...]]:
    """Allowed stages per bone = union of stages present across both sexes,
    ordered by the canonical stage vocabulary. Falls back to the full A–I set
    for bones with no rows yet (so the UI can still offer stages pre-calibration)."""
    allowed: dict[str, tuple[str, ...]] = {}
    for bone in RUS_BONES:
        present: set[str] = set()
        for sex in SEXES:
            present.update((sts.get(sex, {}).get(bone) or {}).keys())
        allowed[bone] = tuple(s for s in STAGES if s in present) if present else STAGES
    return allowed


def load_tables(path: Path = _TABLES_PATH) -> ScoringTables:
    """Load, validate and return the tables. Raises TablesError on integrity failure."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TablesError(f"TW3 tables file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TablesError(f"TW3 tables file is not valid JSON: {exc}") from exc

    _validate_structure(data)

    checksum_verified = False
    stored = data.get("checksum")
    if stored:
        actual = compute_checksum(data)
        if actual != stored:
            raise TablesError(
                "TW3 tables checksum mismatch — the scoring table has been altered "
                "since it was verified. Calculation is disabled until it is re-verified. "
                f"(expected {stored[:12]}…, got {actual[:12]}…)"
            )
        checksum_verified = True

    sts = {s: b for s, b in data.get("stage_to_score", {}).items() if not s.startswith("_")}
    s2a = {s: a for s, a in data.get("score_to_age", {}).items() if not s.startswith("_")}

    return ScoringTables(
        method=data["method"],
        version=data["version"],
        source_reference=data.get("source_reference", ""),
        stage_to_score=sts,
        score_to_age=s2a,
        allowed_stages=_derive_allowed_stages(sts),
        min_age_years=float(data.get("min_age_years", 0.0)),
        max_age_years=float(data.get("max_age_years", 19.0)),
        checksum_verified=checksum_verified,
        raw=data,
    )
