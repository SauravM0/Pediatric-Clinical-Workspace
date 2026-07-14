"""Validation report generator (Plan 5 WI-7)."""
import json

from backend.ai.evaluate import evaluate_age, evaluate_by_subgroup
from backend.ai.validation import gates as gate_mod
from backend.ai.validation.report import build_validation_report, render_html, write_report


def _pieces():
    preds = [60, 72, 84, 96, 108, 120]
    targets = [63, 70, 90, 92, 111, 118]
    age = evaluate_age(preds, targets)
    recs = [{"pred": p, "target": t, "sex": s}
            for p, t, s in zip(preds, targets, ["boys", "boys", "boys", "girls", "girls", "girls"])]
    sub = evaluate_by_subgroup(recs, by=["sex"])
    gate = gate_mod.evaluate_gates(age, worst_subgroup_mae_months=sub["worst_subgroup"]["mae_months"])
    return age, sub, gate


def test_report_assembles_headline_and_sections():
    age, sub, gate = _pieces()
    rep = build_validation_report(
        model_version="boneage-gp-test", dataset="rsna-internal",
        age_metrics=age, subgroups=sub, gate_report=gate,
        provenance={"scoring_table_version": "v1", "checksum": "abc123"},
    )
    assert rep["headline"]["mae_months"] == age["mae_months"]
    assert rep["headline"]["gates_passed"] == gate["passed"]
    assert rep["external_validation"] is False
    assert "Internal validation only" in rep["disclaimer"]
    assert rep["whole_hand"]["n"] == 6


def test_external_flag_switches_disclaimer():
    age, sub, gate = _pieces()
    rep = build_validation_report(model_version="m", dataset="india-cohort",
                                  age_metrics=age, external=True)
    assert rep["external_validation"] is True
    assert "External validation run" in rep["disclaimer"]


def test_html_contains_key_numbers_and_gate_rows():
    age, sub, gate = _pieces()
    rep = build_validation_report(model_version="boneage-gp-test", dataset="rsna",
                                  age_metrics=age, subgroups=sub, gate_report=gate,
                                  provenance={"checksum": "abc123"})
    html = render_html(rep)
    assert "Bone-age validation report" in html
    assert "boneage-gp-test" in html
    assert str(age["mae_months"]) in html
    assert "whole_hand.mae" in html            # a gate row is rendered
    assert "abc123" in html                    # provenance rendered
    assert "Disclaimer" in html


def test_write_report_emits_json_and_html(tmp_path):
    age, sub, gate = _pieces()
    rep = build_validation_report(model_version="m", dataset="d", age_metrics=age,
                                  subgroups=sub, gate_report=gate)
    jp = tmp_path / "report.json"
    hp = tmp_path / "report.html"
    write_report(rep, jp, hp)
    assert jp.exists() and hp.exists()
    loaded = json.loads(jp.read_text(encoding="utf-8"))
    assert loaded["headline"]["mae_months"] == age["mae_months"]
    assert "<h1>Bone-age validation report</h1>" in hp.read_text(encoding="utf-8")
