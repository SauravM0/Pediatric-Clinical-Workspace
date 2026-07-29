"""Concise English TW3-C RUS report (directive §20).

Server-side HTML generation from a finished assessment. Print-friendly, fully
local. Honest by construction: it states doctor-review status, never claims
"fully automated", and does not produce an adult-height prediction in this
phase. No adult-height, no AI-model line unless a model was actually used.
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Optional

from backend.config import APP_VERSION, REPORT_TEMPLATE_VERSION
from backend.models import Radiograph, TW3Assessment
from backend.tw3 import (
    BONE_LABELS,
    METHOD_DISPLAY_NAME,
    METHOD_QUALIFIER,
    METHOD_SOURCE_NOTE,
    RUS_BONES,
)

CLINIC_NAME = "Local clinic (configure name)"


def _months_to_ym(months: Optional[int]) -> str:
    if months is None:
        return "—"
    y, m = divmod(int(months), 12)
    return f"{y} y {m} m"


def _e(v) -> str:
    return html.escape("" if v is None else str(v))


def _diff_text(months: Optional[int]) -> str:
    if months is None:
        return "—"
    sign = "+" if months >= 0 else "−"
    y, m = divmod(abs(int(months)), 12)
    trend = "advanced" if months > 12 else "delayed" if months < -12 else "concordant"
    return f"{sign}{y} y {m} m vs chronological age ({trend})"


def render_report_html(a: TW3Assessment, data: dict,
                       radiograph: Optional[Radiograph] = None) -> str:
    """Render an assessment (already-serialized ``data`` dict) to an HTML report."""
    approved = a.assessment_status == "approved"
    review_line = (
        f"Reviewed and approved by {_e(a.approved_by)}"
        + (f" on {_e(a.approved_at.date().isoformat())}" if a.approved_at else "")
        + "."
        if approved else
        "DRAFT — calculated but not yet reviewed and approved by the treating clinician."
    )
    bone_by_code = {b["bone_code"]: b for b in data.get("bones", [])}
    rows = "".join(
        f"<tr><td>{_e(BONE_LABELS[c])}</td><td class='c'>{_e(bone_by_code.get(c, {}).get('confirmed_stage') or '—')}</td>"
        f"<td class='c'>{_e(_fmt_num(bone_by_code.get(c, {}).get('sex_specific_score')))}</td></tr>"
        for c in RUS_BONES
    )
    quality = data.get("quality_status") or "not assessed"
    flags = ""
    if radiograph and radiograph.quality_flags and radiograph.quality_flags not in ("[]", None):
        flags = f"<p class='warn'>Image flags: {_e(radiograph.quality_flags)}</p>"
    study_date = radiograph.study_date.date().isoformat() if (radiograph and radiograph.study_date) else "—"

    ba_years = data.get("bone_age_years")
    # This document goes into a patient file, so the qualifier travels with the
    # number (M3.2). Without it "TW3-C RUS bone age" reads to most clinicians as
    # the Tanner-Whitehouse standard, which this is not -- see METHOD_QUALIFIER.
    conclusion = (
        f"TW3-C RUS bone age: {_e(_fmt_num(ba_years))} years "
        f"({_months_to_ym(data.get('bone_age_months'))}).<br>"
        "The assessment was calculated from the confirmed maturity grades of the 13 "
        "TW3-C RUS bones and reviewed by the treating clinician.<br>"
        f"<b>{_e(METHOD_QUALIFIER)}</b> {_e(METHOD_SOURCE_NOTE)}"
    ) if ba_years is not None else (
        "<b>No bone age was derived.</b> "
        f"{_e(data.get('status') or 'The scoring engine withheld a result.')}<br>"
        f"{_e(METHOD_QUALIFIER)}"
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>TW3-C RUS Bone Age Report · {_e(data.get('patient_code'))}</title>
<style>
  body {{ font-family: Arial, Helvetica, sans-serif; color:#111; max-width:760px; margin:24px auto; padding:0 16px; }}
  h1 {{ font-size:18px; margin:0 0 2px; }} h2 {{ font-size:13px; color:#334155; margin:18px 0 6px; text-transform:uppercase; letter-spacing:.04em; }}
  .clinic {{ color:#475569; font-size:12px; margin-bottom:14px; }}
  table {{ border-collapse:collapse; width:100%; font-size:13px; }}
  th,td {{ border:1px solid #cbd5e1; padding:5px 8px; text-align:left; }} td.c {{ text-align:center; }}
  th {{ background:#f1f5f9; }}
  .kv {{ font-size:13px; }} .kv div {{ margin:2px 0; }} .kv b {{ display:inline-block; min-width:190px; color:#334155; }}
  .concl {{ margin-top:14px; padding:12px 14px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; font-size:14px; }}
  .status {{ font-weight:700; }} .warn {{ color:#b45309; font-size:12px; }}
  .draft {{ color:#b91c1c; }} .foot {{ margin-top:18px; color:#64748b; font-size:11px; }}
  @media print {{ body {{ margin:0; }} button {{ display:none; }} }}
</style></head><body>
<button onclick="window.print()" style="float:right;padding:6px 12px;">Print</button>
<h1>Bone Age Assessment — Tanner–Whitehouse 3 (TW3-C RUS)</h1>
<div class="clinic">{_e(CLINIC_NAME)}</div>

<h2>Patient</h2>
<div class="kv">
  <div><b>Patient identifier</b>{_e(data.get('patient_code'))}</div>
  <div><b>Sex at birth</b>{_e(data.get('sex_at_birth'))}</div>
  <div><b>Chronological age</b>{_months_to_ym(data.get('chronological_age_months'))}</div>
  <div><b>Radiograph date</b>{_e(study_date)}</div>
  <div><b>Image quality</b>{_e(quality)}</div>
</div>
{flags}

<h2>TW3-C RUS grades &amp; scores</h2>
<table><thead><tr><th>Bone</th><th class="c">Grade</th><th class="c">Score</th></tr></thead>
<tbody>{rows}
<tr><th>Total RUS maturity score</th><th class="c"></th><th class="c">{_e(_fmt_num(data.get('total_rus_score')))}</th></tr>
</tbody></table>

<h2>Result</h2>
<div class="kv">
  <div><b>Method</b>{_e(METHOD_DISPLAY_NAME)} <span style="color:#b45309">({_e(METHOD_QUALIFIER)})</span></div>
  <div><b>Estimated bone age</b>{(_e(_fmt_num(ba_years)) + " years (" + _months_to_ym(data.get('bone_age_months')) + ")") if ba_years is not None else "— not derived"}</div>
  <div><b>Bone age − chronological</b>{_diff_text(data.get('bone_age_difference_months'))}</div>
</div>

<div class="concl">{conclusion}</div>

<h2>Review</h2>
<p class="status {'draft' if not approved else ''}">{review_line}</p>

<div class="foot">
  Application v{_e(APP_VERSION)} · TW3 table {_e(data.get('scoring_table_version') or '—')} ·
  report template v{_e(REPORT_TEMPLATE_VERSION)} · assessment #{_e(data.get('id'))} rev {_e(data.get('revision'))} ·
  generated {datetime.now().strftime('%Y-%m-%d %H:%M')}.
  Score→age curve is provisional (approximate). Doctor-supervised; not a substitute for clinical judgement.
</div>
</body></html>"""


def _fmt_num(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)
