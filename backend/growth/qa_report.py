"""Regenerates the human-readable growth-curve QA report (an interactive HTML
page comparing every fitted percentile value against the actual published
IAP 2015 source table, plus a smoothness check on the WHO<->IAP transition).

This is a *visual* companion to the automated pytest suite in tests/growth/
(which is the real regression gate -- see validation.py's check_source_reproduction
and check_edge_slope_continuity for the pass/fail logic this report's numbers are
drawn from). Run this after touching who_reference.py, iap_reference.py, or
blend.py to eyeball the result, not as a substitute for the tests passing.

Usage:
    python -m backend.growth.qa_report [--out PATH]
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
from pathlib import Path

from . import blend
from . import iap_reference as iap
from . import who_reference as who
from .curve_builder import Z_FOR_CENTILE

_TEMPLATE_PATH = Path(__file__).parent / "qa_report_template.html"
_DEFAULT_OUT = Path(__file__).resolve().parents[2] / "growth_curve_qa.html"

# height/weight publish the full 3/10/25/50/75/90/97 spread; BMI's published
# table only carries the lower-half centiles (see iap_reference.py) plus two
# IOTF adult-equivalent cutoff columns that are NOT z-score percentiles and
# are intentionally excluded here.
_MEASURE_CENTILES = {
    "height": (3, 10, 25, 50, 75, 90, 97),
    "weight": (3, 10, 25, 50, 75, 90, 97),
    "bmi": (3, 5, 10, 25, 50),
}
_MEASURE_FILE_PART = {"height": "height_cm", "weight": "weight_kg", "bmi": "bmi"}

# curve_builder.Z_FOR_CENTILE only covers the standard 3/10/25/50/75/90/97
# spread -- BMI's published table also has a p5 column, whose z only lives in
# iap_reference._Z_BMI (see that module for why height/weight and BMI use
# different centile sets).
_Z_FOR_CENTILE = {**Z_FOR_CENTILE, **iap._Z_BMI}

# A few informative below-5y / mid-transition points, checked against pure WHO
# rather than the (not-yet-existing) IAP table. Not pass/fail checkpoints --
# see the "blend transition, not an error" note logic in the template.
_CONTEXT_AGES_WHO = (0.5, 2.0)


def _load_published_rows(sex_file: str, measure: str) -> list[dict]:
    fname = f"{sex_file}_{_MEASURE_FILE_PART[measure]}_IAP_5_18.csv"
    path = iap._DATA_DIR / fname
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def build_checkpoints() -> list[dict]:
    out = []
    for sex, sex_file in (("boys", "boy"), ("girls", "girl")):
        for measure, centiles in _MEASURE_CENTILES.items():
            rows = _load_published_rows(sex_file, measure)
            for row in rows:
                age = float(row["age_years"])
                for c in centiles:
                    col = f"p{c}"
                    if col not in row:
                        continue
                    z = _Z_FOR_CENTILE[c]
                    published = float(row[col])
                    fitted = blend.unified_value_at_z(measure, sex, age, z)
                    if fitted is None:
                        continue
                    pct = (fitted - published) / published * 100 if published else 0.0
                    out.append({
                        "sex": sex, "measure": measure, "age": round(age, 2), "centile": c,
                        "fitted": round(fitted, 3), "ref": round(published, 3),
                        "src": "IAP", "pct": round(pct, 3),
                    })
            # Context points below IAP's coverage -- pure WHO, not a published-
            # table check, but useful to see the curve is sane down to birth.
            for age in _CONTEXT_AGES_WHO:
                for c in (3, 50, 97):
                    if c not in centiles:
                        continue
                    z = _Z_FOR_CENTILE[c]
                    fitted = blend.unified_value_at_z(measure, sex, age, z)
                    ref = who.who_value_at_z(measure, sex, age, z)
                    if fitted is None or ref is None:
                        continue
                    pct = (fitted - ref) / ref * 100 if ref else 0.0
                    out.append({
                        "sex": sex, "measure": measure, "age": age, "centile": c,
                        "fitted": round(fitted, 3), "ref": round(ref, 3),
                        "src": "WHO", "pct": round(pct, 3),
                    })
            # The exact midpoint of the WHO<->IAP blend window, P50 only --
            # flagged in the report as an intentional transition value, not
            # an error (see blend.py for why it must differ from pure WHO).
            mid = (blend.BLEND_LO + blend.BLEND_HI) / 2
            z50 = _Z_FOR_CENTILE[50]
            fitted = blend.unified_value_at_z(measure, sex, mid, z50)
            ref = who.who_value_at_z(measure, sex, mid, z50)
            if fitted is not None and ref is not None:
                pct = (fitted - ref) / ref * 100 if ref else 0.0
                out.append({
                    "sex": sex, "measure": measure, "age": round(mid, 2), "centile": 50,
                    "fitted": round(fitted, 3), "ref": round(ref, 3),
                    "src": "WHO", "pct": round(pct, 3),
                })
    return out


def build_velocity(measure: str = "weight", centile: int = 50, n: int = 61) -> dict:
    """Dense value + central-difference velocity sample across the WHO<->IAP
    blend window, for each sex -- the smoothness evidence for the transition."""
    z = Z_FOR_CENTILE[centile]
    lo, hi = blend.BLEND_LO, blend.BLEND_HI
    out = {}
    for sex in ("boys", "girls"):
        ages = [lo + i * (hi - lo) / (n - 1) for i in range(n)]
        values = [blend.unified_value_at_z(measure, sex, a, z) for a in ages]
        vel_ages = ages[1:-1]
        step = ages[1] - ages[0]
        velocity = [(values[i + 1] - values[i - 1]) / (2 * step) for i in range(1, len(ages) - 1)]
        out[sex] = {
            "ages": [round(a, 4) for a in ages],
            "values": [round(v, 4) for v in values],
            "vel_ages": [round(a, 4) for a in vel_ages],
            "velocity": [round(v, 4) for v in velocity],
            "window_lo": lo, "window_hi": hi, "join_age": hi,
        }
    return out


def render(out_path: Path = _DEFAULT_OUT) -> Path:
    checkpoints = build_checkpoints()
    velocity = build_velocity()
    html = _TEMPLATE_PATH.read_text(encoding="utf-8")
    html = html.replace("__CHECKPOINTS__", json.dumps(checkpoints))
    html = html.replace("__VELOCITY__", json.dumps(velocity))
    html = html.replace("__GENERATED_AT__", json.dumps(datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
    out_path.write_text(html, encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT, help="Output HTML path")
    args = parser.parse_args()
    path = render(args.out)
    checkpoints = build_checkpoints()
    published = [c for c in checkpoints if c["src"] == "IAP"]
    worst = max((abs(c["pct"]) for c in published), default=0.0)
    print(f"Wrote {path} ({len(checkpoints)} checkpoints, {len(published)} against published data, worst deviation {worst:.2f}%)")


if __name__ == "__main__":
    main()
