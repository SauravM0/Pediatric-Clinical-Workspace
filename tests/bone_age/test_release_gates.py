"""Validation & release-gate infrastructure (Plan 5 WI-1/WI-5/WI-6).

Proves the safety-critical behaviours:
  * a leaked test set REFUSES evaluation (by patient and by image hash);
  * the frozen registry is checksum-locked (tamper detected);
  * engineering gates map thresholds -> pass/fail with the measured value;
  * the release engine PASSES a clear win and FAILS a subgroup regression, a
    gate breach, and a bad-calibration candidate.

Pure math + JSON; no DB, no model, no server.
"""
import pytest

from backend.ai.validation import gates as gate_mod
from backend.ai.validation import leak_guard as lg
from backend.ai.validation.release_gate import evaluate_candidate


# ── WI-1: registry + leak guard ──────────────────────────────────────────────

def test_registry_freeze_and_checksum_roundtrip(tmp_path):
    p = tmp_path / "locked_test.json"
    reg = lg.save_registry([1, 2, 3], ["h1", "h2"], dataset="rsna", source="internal-rsna", path=p)
    assert reg.checksum_verified is True
    assert reg.patient_ids == frozenset({"1", "2", "3"})
    reloaded = lg.load_registry(p)
    assert reloaded.checksum_verified is True and not reloaded.is_empty


def test_registry_tamper_is_detected(tmp_path):
    import json
    p = tmp_path / "locked_test.json"
    lg.save_registry([1, 2], ["h1"], dataset="rsna", source="internal-rsna", path=p)
    doc = json.loads(p.read_text())
    doc["patient_ids"].append("999")            # add a patient, keep old checksum
    p.write_text(json.dumps(doc))
    with pytest.raises(lg.RegistryError, match="checksum mismatch"):
        lg.load_registry(p)


def test_patient_leak_is_refused():
    reg = lg.build_from_dict({"patient_ids": [1, 2, 3], "image_hashes": ["a"]})
    with pytest.raises(lg.LeakError, match="train"):
        lg.assert_disjoint(reg, {"train": {"patient_ids": [3, 4], "image_hashes": []}})


def test_image_hash_leak_is_refused():
    reg = lg.build_from_dict({"patient_ids": [1], "image_hashes": ["a", "b"]})
    with pytest.raises(lg.LeakError, match="feedback"):
        lg.assert_disjoint(reg, {"feedback": {"patient_ids": [9], "image_hashes": ["b"]}})


def test_clean_split_passes():
    reg = lg.build_from_dict({"patient_ids": [1, 2], "image_hashes": ["a"]})
    lg.assert_disjoint(reg, {"train": {"patient_ids": [3, 4], "image_hashes": ["z"]}})  # no raise


def test_shipped_registry_is_the_carved_rsna_locked_test():
    # Phase C1 carved the real locked test (RSNA validation, 1,425 held-out
    # images) into locked_test.json — it is no longer the empty template.
    reg = lg.load_registry()
    assert not reg.is_empty
    assert reg.source == "internal-rsna" and reg.checksum_verified is True


# ── WI-5: engineering gates ──────────────────────────────────────────────────

_GOOD_AGE = {"mae_months": 5.0, "pct_within_months": {"12": 92.0}}
_BAD_AGE = {"mae_months": 8.0, "pct_within_months": {"12": 80.0}}


def test_gates_pass_when_within_thresholds():
    r = gate_mod.evaluate_gates(_GOOD_AGE, worst_subgroup_mae_months=7.0)
    assert r["passed"] is True and r["n_fail"] == 0


def test_gates_fail_on_mae_and_subgroup_and_within():
    r = gate_mod.evaluate_gates(_BAD_AGE, worst_subgroup_mae_months=10.0)
    assert r["passed"] is False
    failed = {g["gate"] for g in r["gates"] if g["status"] == "fail"}
    assert {"whole_hand.mae", "whole_hand.subgroup_mae", "whole_hand.pct_within_12mo"} <= failed


def test_staging_gates_not_measured_without_staging_input():
    r = gate_mod.evaluate_gates(_GOOD_AGE, worst_subgroup_mae_months=7.0)
    nm = {g["gate"] for g in r["gates"] if g["status"] == "not_measured"}
    assert "staging.overall_weighted_kappa" in nm


# ── WI-6: release-gate engine ────────────────────────────────────────────────

def _targets():
    return [60, 72, 84, 96, 108, 120]


def test_clear_win_passes():
    targets = _targets()
    incumbent = [t + 8 for t in targets]     # 8 mo error each
    candidate = [t + 2 for t in targets]     # 2 mo error each -> clearly better + gates pass
    v = evaluate_candidate(targets, candidate, incumbent, min_improvement_months=0.3)
    assert v.passed is True
    assert any("PASS beat-incumbent" in r for r in v.reasons)


def test_subgroup_regression_fails_even_if_overall_better():
    targets = _targets()
    groups = ["boys", "boys", "boys", "girls", "girls", "girls"]
    # Candidate better for boys, much worse for girls -> overall may win, subgroup regresses.
    incumbent = [t + 3 for t in targets]
    candidate = [targets[0], targets[1], targets[2],   # perfect boys
                 targets[3] + 15, targets[4] + 15, targets[5] + 15]  # awful girls
    v = evaluate_candidate(targets, candidate, incumbent, groups=groups)
    assert v.passed is False
    assert any("FAIL no-subgroup-regression" in r for r in v.reasons)


def test_gate_breach_fails_even_if_beats_incumbent():
    targets = _targets()
    incumbent = [t + 30 for t in targets]    # terrible incumbent
    candidate = [t + 10 for t in targets]    # beats it, but MAE 10 > 6mo gate
    v = evaluate_candidate(targets, candidate, incumbent)
    assert v.passed is False
    assert any("FAIL engineering-gates" in r for r in v.reasons)


def test_leak_refusal_short_circuits_release():
    targets = _targets()
    reg = lg.build_from_dict({"patient_ids": [1, 2], "image_hashes": []})
    with pytest.raises(lg.LeakError):
        evaluate_candidate(
            targets, [t + 1 for t in targets], [t + 2 for t in targets],
            test_registry=reg, other_sets={"train": {"patient_ids": [2], "image_hashes": []}},
        )
