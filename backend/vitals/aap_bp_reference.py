"""AAP 2017 blood-pressure tables for children aged 1-12 (step 5).

    Flynn JT, Kaelber DC, Baker-Smith CM, et al. Clinical Practice Guideline for
    Screening and Management of High Blood Pressure in Children and Adolescents.
    Pediatrics 2017;140(3):e20171904. Table 4 (boys) and Table 5 (girls).

Under 13 the guideline classifies blood pressure by CENTILE for age, sex and
height. The tables are not bundled and are never reconstructed from memory: a
clinic transcribes them (twice, independently) and installs them with
``python -m backend.vitals.ingest_aap_bp``. Until then children under 13 get no
category, with the reason -- see blood_pressure.assess.

Indexed by HEIGHT IN CM, not by height percentile
--------------------------------------------------
The tables' columns are height percentiles of the US CDC 2000 charts, and each
column also states the height in cm it corresponds to. An Indian child's IAP or
WHO centile is a different quantity from a CDC centile, so converting through
our own growth engine would pick the wrong column. Interpolating across the
columns by the child's measured height uses exactly what the table says. Below
the 5th-centile height the 5th column is used, above the 95th the 95th -- as the
guideline instructs.

Classification, ages 1 to <13 (AAP 2017 Table 3)
------------------------------------------------
    Normal     < 90th centile
    Elevated   >= 90th centile, or 120/80, whichever is lower   (to < 95th)
    Stage 1    >= 95th centile, or 130/80, whichever is lower   (to < 95th + 12)
    Stage 2    >= 95th + 12 mmHg, or 140/90, whichever is lower
Systolic and diastolic are classified separately and the higher category wins.
"""
from __future__ import annotations

import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Optional

TABLE_PATH = Path(__file__).with_name("data") / "aap2017_bp_tables.json"

HEIGHT_PERCENTILES = (5, 10, 25, 50, 75, 90, 95)
REQUIRED_AGES = tuple(range(1, 13))           # 1..12 inclusive: what the rules need
OPTIONAL_AGES = tuple(range(13, 18))          # present in the paper; not used
LEVELS = ("p50", "p90", "p95", "p95_12")
SEXES = ("boys", "girls")

# Structural bounds, wide enough for any real row. They catch a dropped digit,
# inches entered as cm, or a column shifted by one.
HEIGHT_CM_RANGE = (60.0, 200.0)
SBP_RANGE = (70.0, 165.0)
DBP_RANGE = (30.0, 115.0)

REFERENCE = ("Flynn JT, et al. Clinical Practice Guideline for Screening and "
             "Management of High Blood Pressure in Children and Adolescents. "
             "Pediatrics 2017;140(3):e20171904, Tables 4-5.")


# ── the table's own consistency ──────────────────────────────────────────────

def table_problems(doc: Optional[dict]) -> list[str]:
    """Everything that disqualifies a table. Empty list = usable.

    The strongest single check is arithmetic the paper itself guarantees: every
    "95th + 12 mmHg" cell equals its 95th cell plus 12. A transcriber who slips
    a row or a column breaks that somewhere, and it costs nothing to check.
    """
    if not doc or "rows" not in doc:
        return ["no table"]
    rows = doc["rows"]
    problems: list[str] = []
    for sex in SEXES:
        by_age = rows.get(sex) or {}
        for age in REQUIRED_AGES:
            cols = by_age.get(str(age)) or {}
            missing = [p for p in HEIGHT_PERCENTILES if str(p) not in cols]
            if missing:
                problems.append(f"{sex} age {age}: missing height columns {missing}")
                continue
            prev_h = -math.inf
            for p in HEIGHT_PERCENTILES:
                c = cols[str(p)]
                where = f"{sex} age {age} h{p}"
                h = c.get("height_cm")
                if not isinstance(h, (int, float)) or not (HEIGHT_CM_RANGE[0] <= h <= HEIGHT_CM_RANGE[1]):
                    problems.append(f"{where}: height_cm {h!r} outside {HEIGHT_CM_RANGE}")
                    continue
                if h <= prev_h:
                    problems.append(f"{where}: height_cm {h} not above the previous column ({prev_h})")
                prev_h = h
                for kind, (lo, hi) in (("sbp", SBP_RANGE), ("dbp", DBP_RANGE)):
                    vals = [c.get(f"{kind}_{lv}") for lv in LEVELS]
                    if not all(isinstance(v, (int, float)) for v in vals):
                        problems.append(f"{where}: {kind} values incomplete {vals}")
                        continue
                    if not all(lo <= v <= hi for v in vals):
                        problems.append(f"{where}: {kind} {vals} outside {lo}-{hi}")
                    if not (vals[0] < vals[1] < vals[2] < vals[3]):
                        problems.append(f"{where}: {kind} centiles not increasing {vals}")
                    if abs(vals[3] - (vals[2] + 12)) > 0.5:
                        problems.append(f"{where}: {kind} 95th+12 ({vals[3]}) is not 95th ({vals[2]}) + 12")
                if all(isinstance(c.get(f"{k}_p95"), (int, float)) for k in ("sbp", "dbp")) \
                        and c["dbp_p95"] >= c["sbp_p95"]:
                    problems.append(f"{where}: diastolic 95th not below systolic 95th")
        # Height grows with age at every centile column. A swapped age row or an
        # inches column breaks this where nothing else would.
        for p in HEIGHT_PERCENTILES:
            hs = [((by_age.get(str(a)) or {}).get(str(p)) or {}).get("height_cm") for a in REQUIRED_AGES]
            if all(isinstance(h, (int, float)) for h in hs) and any(b <= a for a, b in zip(hs, hs[1:])):
                problems.append(f"{sex} h{p}: height_cm does not increase with age {hs}")
    prov = doc.get("provenance") or {}
    for key in ("entered_by", "verified_by", "source"):
        if not str(prov.get(key, "")).strip():
            problems.append(f"provenance.{key} is empty: record who transcribed and who checked")
    if prov.get("entered_by") and prov.get("entered_by") == prov.get("verified_by"):
        problems.append("provenance: entered_by and verified_by are the same person")
    if doc.get("checksum") != checksum(rows):
        problems.append("checksum does not match the rows: the table was edited after installation")
    return problems


def checksum(rows: dict) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def _load() -> Optional[dict]:
    if not TABLE_PATH.exists():
        return None
    try:
        return json.loads(TABLE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def reset_cache() -> None:
    _load.cache_clear()


def status() -> dict:
    doc = _load()
    if doc is None:
        return {"active": False, "reason": "AAP 2017 tables not installed "
                "(python -m backend.vitals.ingest_aap_bp; see backend/vitals/AAP-BP-TABLES.md)"}
    problems = table_problems(doc)
    return {"active": not problems, "reason": "ok" if not problems else problems[0],
            "problems": problems, "provenance": doc.get("provenance")}


def available() -> bool:
    return status()["active"]


# ── classification ───────────────────────────────────────────────────────────

def thresholds(sex: str, age_years: float, height_cm: float) -> Optional[dict]:
    """Centile thresholds for this child, interpolated by height in cm.

    Age is COMPLETED years, as the tables are laid out (a child of 7.9 uses the
    age-7 row). Returns None outside ages 1-12 or when the table is unusable.
    """
    if not available() or sex not in SEXES:
        return None
    age = int(math.floor(age_years))
    if age not in REQUIRED_AGES:
        return None
    cols = _load()["rows"][sex][str(age)]
    ordered = [cols[str(p)] for p in HEIGHT_PERCENTILES]
    heights = [c["height_cm"] for c in ordered]

    if height_cm <= heights[0]:
        lo = hi = 0; w = 0.0
    elif height_cm >= heights[-1]:
        lo = hi = len(heights) - 1; w = 0.0
    else:
        hi = next(i for i, h in enumerate(heights) if h >= height_cm)
        lo = hi - 1
        w = (height_cm - heights[lo]) / (heights[hi] - heights[lo])
    out = {"age_row": age, "height_columns": [HEIGHT_PERCENTILES[lo], HEIGHT_PERCENTILES[hi]]}
    for kind in ("sbp", "dbp"):
        for lv in LEVELS:
            key = f"{kind}_{lv}"
            out[key] = round(ordered[lo][key] + w * (ordered[hi][key] - ordered[lo][key]), 1)
    return out


_ORDER = {"normal": 0, "elevated": 1, "stage1": 2, "stage2": 3}
_LABEL = {"normal": "Normal (< 90th centile)",
          "elevated": "Elevated (≥ 90th centile)",
          "stage1": "Stage 1 hypertension range (≥ 95th centile)",
          "stage2": "Stage 2 hypertension range (≥ 95th + 12 mmHg)"}


def _one(value: float, p90: float, p95: float, p95_12: float, caps: tuple[float, float, float]) -> str:
    elevated, stage1, stage2 = (min(p90, caps[0]), min(p95, caps[1]), min(p95_12, caps[2]))
    if value >= stage2:
        return "stage2"
    if value >= stage1:
        return "stage1"
    if value >= elevated:
        return "elevated"
    return "normal"


def classify(sex: str, age_years: float, height_cm: float, sbp: float, dbp: float) -> Optional[dict]:
    t = thresholds(sex, age_years, height_cm)
    if t is None:
        return None
    s = _one(sbp, t["sbp_p90"], t["sbp_p95"], t["sbp_p95_12"], (120.0, 130.0, 140.0))
    d = _one(dbp, t["dbp_p90"], t["dbp_p95"], t["dbp_p95_12"], (80.0, 80.0, 90.0))
    code = s if _ORDER[s] >= _ORDER[d] else d
    return {"category": code, "category_label": _LABEL[code], "systolic_category": s,
            "diastolic_category": d, "thresholds": t}
