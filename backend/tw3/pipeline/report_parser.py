"""
Parse a TW3 radiology report (free text) into a structured label record.

Turns reports like Dr. Rathod's into machine-usable training labels: the 13 RUS
bone stages (A..I), the 7 carpal stages, the RUS grade score, and the reported
bone ages. Pure stdlib — no ML libraries required for the data layer.
"""
from __future__ import annotations
import re
from typing import Dict, Optional

# Canonical RUS bone keys (match backend/tw3/scoring.py) and their report aliases.
RUS_ALIASES = [
    ("radius", [r"radius"]),
    ("ulna",   [r"ulna"]),
    ("mc1",    [r"first metacarpal", r"1st metacarpal", r"metacarpal i\b"]),
    ("mc3",    [r"third metacarpal", r"3rd metacarpal", r"metacarpal iii"]),
    ("mc5",    [r"fifth metacarpal", r"5th metacarpal", r"metacarpal v\b"]),
    ("pp1",    [r"proximal phalanx thumb", r"proximal phalanx i\b", r"1st proximal phalanx"]),
    ("pp3",    [r"proximal phalanx iii"]),
    ("pp5",    [r"proximal phalanx v\b"]),
    ("mp3",    [r"middle phalanx iii"]),
    ("mp5",    [r"middle phalanx v\b"]),
    ("dp1",    [r"distal phalanx thumb", r"distal phalanx i\b", r"1st distal phalanx"]),
    ("dp3",    [r"distal phalanx iii"]),
    ("dp5",    [r"distal phalanx v\b"]),
]
CARPAL_ALIASES = [
    ("capitate", [r"capitate"]), ("hamate", [r"hamate"]), ("triquetral", [r"triquetral"]),
    ("lunate", [r"lunate"]), ("scaphoid", [r"scaphoid"]), ("trapezium", [r"trapezium"]),
    ("trapezoid", [r"trapezoid"]),
]
STAGE_RE = r"[:\-–—\s]+([A-I])\b"   # separator then a single stage letter A..I


def _find_stage(text: str, aliases) -> Optional[str]:
    for alias in aliases:
        m = re.search(alias + STAGE_RE, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return None


def _num(text: str, pattern: str) -> Optional[float]:
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return float(m.group(1)) if m else None


def parse_report(text: str) -> Dict:
    """Free-text TW3 report -> structured record. Missing fields come back as None."""
    t = re.sub(r"[ \t]+", " ", text)

    rus = {key: _find_stage(t, aliases) for key, aliases in RUS_ALIASES}
    carpal = {key: _find_stage(t, aliases) for key, aliases in CARPAL_ALIASES}

    # Sex: prefer an explicit "Age: 10.4 Y / F" style token.
    sex = None
    ms = re.search(r"\b([FM])\b\s*(?:$|\n|WRIST|HAND|/)", t)
    if re.search(r"/\s*F\b|Age[^\n]*\bF\b", t, re.IGNORECASE):
        sex = "girls"
    elif re.search(r"/\s*M\b|Age[^\n]*\bM\b", t, re.IGNORECASE):
        sex = "boys"

    return {
        "sex": sex,
        "chronological_age_years": _num(t, r"Age\s*[:\-]?\s*([\d.]+)\s*Y"),
        "rus_stages": rus,
        "carpal_stages": carpal,
        "reported": {
            "rus_grade_score": _num(t, r"RUS\s*Grade\s*Score\s*[:\-]?\s*(\d+)"),
            "carpal_grade_score": _num(t, r"Carpals?\s*grade\s*score\s*[:\-]?\s*(\d+)"),
            "twiii_rus_bone_age_years": _num(t, r"TWIII\s*['‘’]?\s*RUS\s*['‘’]?\s*bone\s*age\s*[:\-]?\s*([\d.]+)"),
            "twii_rus_bone_age_years":  _num(t, r"TWII\s*['‘’]?\s*RUS\s*['‘’]?\s*bone\s*age\s*[:\-]?\s*([\d.]+)"),
            "twii20_bone_age_years":    _num(t, r"TWII\s*['‘’]?\s*20\s*['‘’]?\s*bone\s*age\s*[:\-]?\s*([\d.]+)"),
        },
    }


if __name__ == "__main__":
    import sys, json
    print(json.dumps(parse_report(sys.stdin.read()), indent=2))
