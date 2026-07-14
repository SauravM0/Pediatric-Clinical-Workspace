"""Label-quality activation gate for AI suggestions (Plan 2 WI-8)."""
from backend.ai.suggestion_gate import activation_map, suggestions_allowed


def test_all_gates_pass_allows_suggestion():
    d = suggestions_allowed(
        "radius", "girls",
        support_per_stage={"F": 60, "G": 55, "H": 80},
        consensus_agreement=0.82, calibration_ok=True)
    assert d["allowed"] is True


def test_low_support_blocks():
    d = suggestions_allowed(
        "radius", "girls",
        support_per_stage={"F": 60, "G": 12},   # one stage under 50
        consensus_agreement=0.9, calibration_ok=True)
    assert d["allowed"] is False
    assert any("FAIL support" in r for r in d["reasons"])


def test_low_agreement_blocks():
    d = suggestions_allowed(
        "ulna", "boys",
        support_per_stage={"F": 60, "G": 60},
        consensus_agreement=0.55, calibration_ok=True)
    assert d["allowed"] is False
    assert any("FAIL consensus" in r for r in d["reasons"])


def test_uncalibrated_blocks():
    d = suggestions_allowed(
        "ulna", "boys",
        support_per_stage={"F": 60, "G": 60},
        consensus_agreement=0.9, calibration_ok=False)
    assert d["allowed"] is False
    assert any("FAIL calibration" in r for r in d["reasons"])


def test_no_data_blocks():
    d = suggestions_allowed("mc1", "girls", support_per_stage={},
                            consensus_agreement=None, calibration_ok=True)
    assert d["allowed"] is False


def test_activation_map_over_coverage_report():
    coverage = {"cells": [
        {"bone_code": "radius", "stage": "G", "unique_total": 60},
        {"bone_code": "radius", "stage": "H", "unique_total": 55},
        {"bone_code": "ulna", "stage": "G", "unique_total": 20},   # under support
    ]}
    out = activation_map(
        coverage,
        agreements={"radius": 0.85, "ulna": 0.85},
        calibrated_bones={"radius": True, "ulna": True})
    assert out["decisions"]["radius"]["allowed"] is True
    assert out["decisions"]["ulna"]["allowed"] is False
    assert out["n_allowed"] == 1 and out["n_bones"] == 2
