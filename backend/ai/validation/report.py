"""Validation report generator (Plan 5 WI-7).

Assembles the pieces the evaluator/gates already produce into a self-describing
report -- machine-readable JSON + a human HTML page -- with full provenance. This
is the auditable artifact validation_protocol.md §5 and the master audit §7
describe: the backbone of any future regulatory submission.

Pure assembly + string rendering (no model, no I/O beyond optional file writes),
so it is unit-testable. Consumes results from backend.ai.evaluate and
backend.ai.validation.gates -- it does not recompute metrics.
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPORT_VERSION = "bone-age-validation-report-1.0"

_INTERNAL_DISCLAIMER = (
    "Internal validation only. A passing internal test is NOT a clinical accuracy "
    "claim; external, expert-consensus, subgroup-stratified validation on the target "
    "population is required before any patient-facing accuracy statement."
)
_EXTERNAL_NOTE = (
    "External validation run on the stated cohort. Confirm the cohort, readers, and "
    "acceptance criteria were pre-registered (see PROTOCOL.md)."
)


def build_validation_report(
    *,
    model_version: str,
    dataset: str,
    age_metrics: dict,
    subgroups: Optional[dict] = None,
    staging: Optional[dict] = None,
    gate_report: Optional[dict] = None,
    provenance: Optional[dict] = None,
    protocol_version: str = "validation-protocol-1.0",
    external: bool = False,
) -> dict:
    """Assemble a ValidationReport dict from already-computed evaluator/gate results."""
    passed = gate_report.get("passed") if isinstance(gate_report, dict) else None
    return {
        "report_type": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "protocol_version": protocol_version,
        "model_version": model_version,
        "dataset": dataset,
        "external_validation": bool(external),
        "provenance": provenance or {},
        "headline": {
            "mae_months": (age_metrics or {}).get("mae_months"),
            "pct_within_12mo": ((age_metrics or {}).get("pct_within_months") or {}).get("12"),
            "gates_passed": passed,
        },
        "whole_hand": age_metrics or {},
        "subgroups": subgroups,
        "staging": staging,
        "gates": gate_report,
        "disclaimer": _EXTERNAL_NOTE if external else _INTERNAL_DISCLAIMER,
    }


# ── HTML rendering ────────────────────────────────────────────────────────────

def _esc(v) -> str:
    return html.escape("" if v is None else str(v))


def _badge(status: str) -> str:
    color = {"pass": "#1a7f37", "fail": "#cf222e", "not_measured": "#9a6700"}.get(status, "#57606a")
    return f'<span style="color:#fff;background:{color};padding:1px 7px;border-radius:10px;font-size:12px">{_esc(status)}</span>'


def _kv_table(d: dict, keys: list[tuple[str, str]]) -> str:
    rows = "".join(
        f"<tr><td>{_esc(label)}</td><td style='text-align:right'>{_esc(d.get(k))}</td></tr>"
        for k, label in keys if k in (d or {})
    )
    return f"<table>{rows}</table>"


def render_html(report: dict) -> str:
    ah = report.get("whole_hand") or {}
    ba = ah.get("bland_altman") or {}
    within = ah.get("pct_within_months") or {}
    gates = report.get("gates") or {}
    subs = report.get("subgroups") or {}

    metrics_html = _kv_table(ah, [
        ("n", "N"), ("mae_months", "MAE (months)"), ("median_ae_months", "Median AE"),
        ("rmse_months", "RMSE"), ("signed_bias_months", "Signed bias"),
    ])
    within_html = "".join(
        f"<tr><td>±{_esc(k)} mo</td><td style='text-align:right'>{_esc(v)}%</td></tr>"
        for k, v in within.items())
    ba_html = _kv_table(ba, [
        ("mean_diff_months", "Mean diff"), ("sd_diff_months", "SD diff"),
        ("loa_lower_months", "LoA lower"), ("loa_upper_months", "LoA upper"),
    ])

    gate_rows = "".join(
        f"<tr><td>{_esc(g.get('gate'))}</td><td style='text-align:right'>{_esc(g.get('measured'))}</td>"
        f"<td style='text-align:right'>{_esc(g.get('comparator'))} {_esc(g.get('threshold'))}</td>"
        f"<td>{_badge(g.get('status',''))}</td></tr>"
        for g in gates.get("gates", []))

    sub_rows = ""
    for cell in (subs.get("subgroups") or []):
        grp = ", ".join(f"{k}={v}" for k, v in (cell.get("group") or {}).items())
        if cell.get("insufficient"):
            sub_rows += f"<tr><td>{_esc(grp)}</td><td>{_esc(cell.get('n'))}</td><td colspan='2'>insufficient n</td></tr>"
        else:
            sub_rows += (f"<tr><td>{_esc(grp)}</td><td>{_esc(cell.get('n'))}</td>"
                         f"<td style='text-align:right'>{_esc(cell.get('mae_months'))}</td>"
                         f"<td style='text-align:right'>{_esc((cell.get('pct_within_months') or {}).get('12'))}%</td></tr>")
    worst = subs.get("worst_subgroup")

    prov = report.get("provenance") or {}
    prov_rows = "".join(f"<tr><td>{_esc(k)}</td><td>{_esc(v)}</td></tr>" for k, v in prov.items())

    headline = report.get("headline") or {}
    passed = headline.get("gates_passed")
    verdict = ("PASS" if passed else "FAIL") if passed is not None else "N/A"
    verdict_color = "#1a7f37" if passed else ("#cf222e" if passed is not None else "#57606a")

    return f"""<!-- validation report (Plan 5 WI-7) -->
<style>
  .vr {{ font-family: system-ui, sans-serif; max-width: 860px; }}
  .vr table {{ border-collapse: collapse; width: 100%; margin: 6px 0 18px; }}
  .vr td, .vr th {{ border: 1px solid #d0d7de; padding: 4px 8px; font-size: 14px; }}
  .vr h2 {{ font-size: 16px; margin: 18px 0 4px; }}
  .vr .muted {{ color: #57606a; font-size: 13px; }}
</style>
<div class="vr">
  <h1>Bone-age validation report</h1>
  <p class="muted">{_esc(report.get('report_type'))} · model {_esc(report.get('model_version'))} ·
     dataset {_esc(report.get('dataset'))} · {_esc(report.get('generated_at'))}</p>
  <p><strong>Gate verdict:</strong>
     <span style="color:#fff;background:{verdict_color};padding:2px 10px;border-radius:12px">{verdict}</span>
     &nbsp; MAE {_esc(headline.get('mae_months'))} mo &nbsp;·&nbsp; ±12mo {_esc(headline.get('pct_within_12mo'))}%
     &nbsp;·&nbsp; {'EXTERNAL' if report.get('external_validation') else 'INTERNAL'}</p>

  <h2>Whole-hand metrics</h2>{metrics_html}
  <h2>Agreement (% within)</h2><table>{within_html}</table>
  <h2>Bland–Altman</h2>{ba_html}
  <h2>Subgroups</h2>
  <table><tr><th>Group</th><th>N</th><th>MAE (mo)</th><th>±12mo</th></tr>{sub_rows or '<tr><td colspan=4>none</td></tr>'}</table>
  <p class="muted">Worst subgroup: {_esc(worst)}</p>
  <h2>Engineering gates</h2>
  <table><tr><th>Gate</th><th>Measured</th><th>Threshold</th><th>Status</th></tr>{gate_rows or '<tr><td colspan=4>none</td></tr>'}</table>
  <h2>Provenance</h2><table>{prov_rows or '<tr><td colspan=2>none</td></tr>'}</table>
  <p class="muted"><strong>Disclaimer.</strong> {_esc(report.get('disclaimer'))}</p>
</div>"""


def write_report(report: dict, json_path: Path, html_path: Optional[Path] = None) -> None:
    """Write the machine-readable JSON and (optionally) the human HTML."""
    Path(json_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    if html_path is not None:
        Path(html_path).write_text(render_html(report), encoding="utf-8")
