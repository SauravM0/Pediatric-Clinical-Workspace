"""
TW3-RUS deterministic scoring — the "S / scoring" module of the automatic
bone-age pipeline (PEARLS design, Zhang et al., J Digit Imaging 2023).

Given the 13 RUS bone stages (A..I) it computes:
    stages --(stage_to_score table)--> RUS maturity score --(score_to_age curve)--> bone age

SAFETY: no coefficients are invented. The stage->score table is the copyrighted
TW3 (2001) reference and must be supplied by a licensed clinician in
tw3_tables.json. Until a bone's row is present, scoring reports what is missing
instead of guessing. The score->age curve ships seeded ONLY with anchor points
derived from the centre's own radiologist reports (their data).
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Optional

_TABLES_PATH = Path(__file__).with_name("tw3_tables.json")

RUS_BONES = ["radius", "ulna", "mc1", "mc3", "mc5", "pp1", "pp3", "pp5",
             "mp3", "mp5", "dp1", "dp3", "dp5"]
STAGES = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]


def load_tables(path: Path = _TABLES_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _interp(anchors, x) -> Optional[float]:
    """Linear interpolation over ascending [x, y] anchor points."""
    pts = [p for p in anchors if isinstance(p, list) and len(p) == 2]
    if len(pts) < 2:
        return None
    pts = sorted(pts, key=lambda p: p[0])
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (x - x0) / (x1 - x0) * (y1 - y0)
    return pts[-1][1]


def rus_score(stages: Dict[str, str], sex: str, tables: dict) -> dict:
    """Sum per-bone RUS points. Reports calibration/completeness honestly."""
    tbl = tables.get("stage_to_score", {}).get(sex, {}) or {}
    calibrated = len(tbl) > 0
    score, staged, missing_score, missing_stage = 0.0, 0, [], []
    for bone in RUS_BONES:
        st = stages.get(bone)
        if not st:
            missing_stage.append(bone)
            continue
        staged += 1
        pts = (tbl.get(bone) or {}).get(st)
        if isinstance(pts, (int, float)):
            score += pts
        else:
            missing_score.append(bone)
    return {
        "score": score, "staged": staged, "total": len(RUS_BONES),
        "calibrated": calibrated, "missing_score": missing_score,
        "missing_stage": missing_stage,
        "complete": staged == len(RUS_BONES) and not missing_score,
    }


def score_to_age(score: float, sex: str, tables: dict) -> Optional[float]:
    return _interp(tables.get("score_to_age", {}).get(sex, []), score)


def bone_age_from_stages(stages: Dict[str, str], sex: str,
                         tables: Optional[dict] = None) -> dict:
    """Full TW3-RUS: stages -> score -> bone age, with an honest status."""
    tables = tables or load_tables()
    rs = rus_score(stages, sex, tables)
    age = score_to_age(rs["score"], sex, tables) if rs["complete"] else None
    if not rs["calibrated"]:
        status = "stage_to_score table not supplied (licensed TW3 values required)"
    elif rs["missing_stage"]:
        status = f"bones not staged: {', '.join(rs['missing_stage'])}"
    elif rs["missing_score"]:
        status = f"no licensed score for staged bones: {', '.join(rs['missing_score'])}"
    elif age is None:
        status = "score_to_age curve needs >= 2 anchor points for this sex"
    else:
        status = "ok"
    return {"method": tables.get("method", "TWIII-RUS"),
            "rus_score": rs["score"], "bone_age_years": age,
            "status": status, **rs}


if __name__ == "__main__":
    # Self-test: the score->age anchors from Dr. Rathod's reports must round-trip.
    t = load_tables()
    for sc, expected in [(681, 12.1), (713, 12.4)]:
        got = score_to_age(sc, "girls", t)
        ok = got is not None and abs(got - expected) < 0.05
        print(f"score {sc} -> age {got} (expected {expected}) {'OK' if ok else 'FAIL'}")
    # Interpolation sanity between the two anchors:
    mid = score_to_age(697, "girls", t)
    print(f"score 697 -> age {mid:.2f} (interpolated between anchors)")
