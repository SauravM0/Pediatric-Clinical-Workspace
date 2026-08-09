"""M4.3: adopting digiBONE, and the two things that had to change first.

digiBONE (https://github.com/goellab/digiBONE, MIT) is Indian-trained segmental
Greulich-Pyle, reported at 4.7/4.9 months MAD against the incumbent's 8.99 on
the locked RSNA set. The weights are not held here and the model is not
committed; what is committed is the path that makes installing it mean
something, and the boundary that stops it being mistaken for TW3.

Two defects the integration exposed:

1. ``boneage.py`` hardcoded ``models/boneage_gp.onnx`` and ``load_spec()``'s
   default id, so a second model could be converted, registered and calibrated
   and the incumbent would still answer every request. Third occurrence of that
   pattern in this project, hence a test rather than a habit.
2. The response's ``method`` and ``population_note`` were constants. They would
   have survived a switch unchanged, describing an Indian-trained segmental
   model as a US-trained whole-image one -- and the note telling a clinician how
   far to trust the number would have been about a different model.
"""
from __future__ import annotations

import json

import pytest

from backend.ai import active_model, boneage, convert_digibone, registry


@pytest.fixture
def registered(tmp_path, monkeypatch):
    """Register fake models in a temp dir. No ONNX is run -- selection, labelling
    and fallback are decided before any tensor is touched."""
    monkeypatch.setattr(registry, "_MODELS_DIR", tmp_path)

    def _make(model_id, *, method, population, with_onnx=True, **extra):
        (tmp_path / f"{model_id}.json").write_text(json.dumps({
            "model_version": f"{model_id}-v1", "kind": "screening",
            "method_key": method, "population": population,
            "input_size": 224, "preprocessing_version": "prep-1.0-minmax",
            **extra,
        }), encoding="utf-8")
        if with_onnx:
            (tmp_path / f"{model_id}.onnx").write_bytes(b"not-a-real-model")
    return _make


# ── selection ───────────────────────────────────────────────────────────────

def test_incumbent_serves_when_nothing_is_requested(registered, monkeypatch):
    monkeypatch.delenv(active_model.ENV_VAR, raising=False)
    registered("boneage_gp", method="greulich-pyle", population="RSNA-US")
    r = active_model.resolve()
    assert r["model_id"] == "boneage_gp"
    assert r["fell_back"] is False


def test_requesting_digibone_actually_switches(registered, monkeypatch):
    """The defect this milestone fixed: before it, this had no effect at all."""
    registered("boneage_gp", method="greulich-pyle", population="RSNA-US")
    registered("boneage_digibone", method="segmental-greulich-pyle",
               population="Indian-HCJMRI + RSNA")
    monkeypatch.setenv(active_model.ENV_VAR, "boneage_digibone")

    r = active_model.resolve()
    assert r["model_id"] == "boneage_digibone"
    assert r["fell_back"] is False
    assert r["spec"].method == "segmental-greulich-pyle"


def test_an_unregistered_id_falls_back_and_says_so(registered, monkeypatch):
    """A typo in a deployment variable must not silently disable screening, and
    must never silently promote something nobody validated."""
    registered("boneage_gp", method="greulich-pyle", population="RSNA-US")
    monkeypatch.setenv(active_model.ENV_VAR, "boneage_digibne")   # typo

    r = active_model.resolve()
    assert r["model_id"] == "boneage_gp"
    assert r["fell_back"] is True
    assert "not registered" in r["reason"]


def test_a_registered_model_with_no_weights_falls_back(registered, monkeypatch):
    """Metadata committed but the ONNX absent is the normal state of this repo
    for digiBONE -- it must degrade, not crash."""
    registered("boneage_gp", method="greulich-pyle", population="RSNA-US")
    registered("boneage_digibone", method="segmental-greulich-pyle",
               population="Indian-HCJMRI + RSNA", with_onnx=False)
    monkeypatch.setenv(active_model.ENV_VAR, "boneage_digibone")

    r = active_model.resolve()
    assert r["model_id"] == "boneage_gp"
    assert r["fell_back"] is True
    assert "ONNX file is missing" in r["reason"]


def test_selection_never_raises_on_a_broken_deployment(registered, monkeypatch):
    """Nothing registered at all, and a variable pointing at nonsense."""
    monkeypatch.setenv(active_model.ENV_VAR, "does_not_exist")
    r = active_model.resolve()
    assert r["model_id"] == "boneage_gp"
    assert r["spec"] is None
    assert active_model.describe()["available"] is False


# ── labelling follows the model ─────────────────────────────────────────────

def test_the_method_label_follows_the_model(registered, monkeypatch):
    registered("boneage_digibone", method="segmental-greulich-pyle",
               population="Indian-HCJMRI + RSNA")
    monkeypatch.setenv(active_model.ENV_VAR, "boneage_digibone")
    label = active_model.describe_method(active_model.active_spec())
    assert "Segmental" in label and "short bones" in label
    assert "whole-image" not in label
    assert "not TW3" in label, "every screening label must disclaim TW3"


def test_the_population_note_follows_the_model(registered, monkeypatch):
    """The incumbent's note says 'not India-calibrated' and quotes the 0.5-0.7yr
    GP offset. Serving that verbatim for an Indian-trained model would tell a
    clinician to discount a number that does not need discounting -- and the
    reverse mistake, on a different model, would be worse."""
    registered("boneage_gp", method="greulich-pyle", population="RSNA-US")
    registered("boneage_digibone", method="segmental-greulich-pyle",
               population="Indian-HCJMRI + RSNA")

    monkeypatch.setenv(active_model.ENV_VAR, "boneage_gp")
    incumbent = active_model.population_note(active_model.active_spec())
    assert "not India-calibrated" in incumbent

    monkeypatch.setenv(active_model.ENV_VAR, "boneage_digibone")
    digibone = active_model.population_note(active_model.active_spec())
    assert "not India-calibrated" not in digibone
    assert "Indian children in its development set" in digibone
    assert "NOT a TW3 bone age" in digibone
    assert "local validation cohort" in digibone, (
        "an Indian-trained model still needs this clinic's own cohort; the note "
        "must not read as blanket reassurance"
    )


def test_an_unknown_population_gets_no_reassurance(registered, monkeypatch):
    registered("mystery", method="greulich-pyle", population="")
    monkeypatch.setenv(active_model.ENV_VAR, "mystery")
    note = active_model.population_note(active_model.active_spec())
    assert "not declared" in note and "unvalidated" in note


def test_an_unknown_method_is_reported_verbatim_not_guessed(registered, monkeypatch):
    registered("odd", method="brand-new-method", population="RSNA-US")
    monkeypatch.setenv(active_model.ENV_VAR, "odd")
    label = active_model.describe_method(active_model.active_spec())
    assert "brand-new-method" in label and "unrecognised" in label
    assert "not TW3" in label


# ── the method boundary ─────────────────────────────────────────────────────

def test_no_screening_model_is_on_the_tw3_scale(registered, monkeypatch):
    """digiBONE is Greulich-Pyle. GP and TW3-RUS are different standards against
    different reference populations; the estimate may sit beside a TW3 bone age
    and must never be stored as one or averaged with one."""
    registered("boneage_digibone", method="segmental-greulich-pyle",
               population="Indian-HCJMRI + RSNA")
    monkeypatch.setenv(active_model.ENV_VAR, "boneage_digibone")
    assert active_model.is_tw3(active_model.active_spec()) is False
    assert active_model.describe()["is_tw3_scale"] is False


def test_the_shipped_incumbent_is_not_on_the_tw3_scale():
    """Against the real registry, not a fixture."""
    spec = registry.load_spec("boneage_gp")
    if spec is None:
        pytest.skip("no incumbent registered in this checkout")
    assert active_model.is_tw3(spec) is False


def test_the_ai_estimate_is_never_written_as_the_assessment_bone_age():
    """Structural guard. assessment_service must set bone_age_months only from
    TW3 scoring; the screening number lives under its own key in the report."""
    import inspect

    from backend import assessment_service
    from backend.tw3 import report

    src = inspect.getsource(assessment_service)
    for forbidden in ("boneage.predict_months", "ai_screening", "predict_months("):
        assert forbidden not in src, (
            f"assessment_service references {forbidden!r} — a Greulich-Pyle "
            "screening estimate must never become the stored TW3 bone age"
        )
    assert "ai_screening_estimate_years" in inspect.getsource(report), (
        "the screening estimate lost its own separately-named key"
    )


# ── the converter ───────────────────────────────────────────────────────────

def test_parity_tolerance_is_an_equivalence_check_not_an_agreement_one():
    """1e-3 months is ~43 minutes. This is checking that the conversion did not
    change the arithmetic, not that two models agree clinically."""
    assert convert_digibone.PARITY_TOL_MONTHS <= 1e-3


def test_parity_requires_real_radiographs(monkeypatch, tmp_path):
    """Synthetic noise exercises a different part of the input distribution than
    hands do; a bug in an interpolation or padding op can be invisible on noise
    and material on radiographs."""
    assert convert_digibone.MIN_PARITY_IMAGES >= 100
    with pytest.raises(convert_digibone.ConversionError, match="real radiographs"):
        convert_digibone.check_parity(None, tmp_path / "m.onnx", [tmp_path / "a.png"],
                                      224)


def test_missing_weights_fail_before_anything_is_written(tmp_path):
    with pytest.raises(convert_digibone.ConversionError, match="weights not found"):
        convert_digibone.load_checkpoint(tmp_path / "absent.pth")


def test_an_unreadable_checkpoint_reports_clearly_instead_of_a_traceback(tmp_path, capsys):
    """A corrupt or wrong file is the ordinary operator mistake here. It must
    produce an explanation and exit 2, not a torch stack trace."""
    weights = tmp_path / "w.pth"
    weights.write_bytes(b"not a checkpoint")
    rc = convert_digibone.main([
        "--weights", str(weights), "--out", str(tmp_path / "m.onnx")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "cannot convert" in err
    assert "Traceback" not in err


def test_the_unsafe_pickle_loader_is_opt_in(tmp_path):
    """Torch checkpoints are pickles, and unpickling executes what they contain
    -- on a file from a third-party release page, on a machine holding patient
    data. Torch made weights_only the default in 2.6; this tool must not quietly
    undo it."""
    weights = tmp_path / "w.pth"
    weights.write_bytes(b"not a checkpoint")

    with pytest.raises(convert_digibone.ConversionError) as exc:
        convert_digibone.load_checkpoint(weights)
    assert "arbitrary code" in str(exc.value)
    assert "--allow-arbitrary-pickle" in str(exc.value)

    # And with the flag it still fails on this junk -- but by the other path.
    with pytest.raises(convert_digibone.ConversionError, match="unsafe loader"):
        convert_digibone.load_checkpoint(weights, allow_arbitrary_pickle=True)


def test_a_real_run_refuses_without_parity_images(tmp_path, capsys, monkeypatch):
    """--arch and --input-size are guesses this file is not entitled to make,
    and parity against the source implementation is not optional."""
    monkeypatch.setattr(convert_digibone, "load_checkpoint",
                        lambda *a, **k: {"state_dict": {}, "n_tensors": 0,
                                         "keys_head": [], "extra_keys": []})
    rc = convert_digibone.main([
        "--weights", str(tmp_path / "w.pth"), "--out", str(tmp_path / "m.onnx")])
    assert rc == 2
    assert "--parity-images" in capsys.readouterr().err


def test_metadata_declares_the_method_and_withholds_calibration(tmp_path):
    """Quantiles do not transfer between models, so a freshly converted model
    must arrive UNcalibrated -- registry.resolve_interval_policy then withholds
    intervals until calibrate_conformal has been run against it."""
    out = tmp_path / "boneage_digibone.onnx"
    meta_path = convert_digibone.write_metadata(
        out, model_version="digibone-sgp-test", input_size=224,
        preprocessing_version="prep-1.0-minmax",
        parity={"n_images": 100, "worst_abs_diff_months": 1e-9},
        population="Indian-HCJMRI + RSNA", method_key="segmental-greulich-pyle")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["method_key"] == "segmental-greulich-pyle"
    assert meta["licence"] == "MIT", "MIT attribution must travel with the artefact"
    assert "digiBONE" in meta["source"]
    assert "conformal" not in meta, (
        "a freshly converted model must not claim calibration it does not have"
    )
    assert "NOT TW3" in meta["note"]

    spec = registry._spec_from_metadata(meta, out, "boneage_digibone")
    assert registry.resolve_interval_policy(spec).conformal_allowed is False


def test_converted_metadata_records_the_published_figures(tmp_path):
    """So a later reader can tell the claimed accuracy from the measured one."""
    meta_path = convert_digibone.write_metadata(
        tmp_path / "m.onnx", model_version="v", input_size=224,
        preprocessing_version="prep-1.0-minmax", parity={},
        population="Indian-HCJMRI + RSNA", method_key="segmental-greulich-pyle")
    published = json.loads(meta_path.read_text(encoding="utf-8"))["published_mad_months"]
    assert published["sgp_male"] == 4.7 and published["sgp_female"] == 4.9
    assert published["full_hand_male"] == 5.7


# ── the repository ships no weights ─────────────────────────────────────────

def test_digibone_weights_are_not_committed():
    """MIT permits redistribution, but the weights are a large binary this repo
    deliberately does not carry -- and a committed model would bypass the
    conversion parity check entirely."""
    import subprocess

    tracked = subprocess.run(["git", "ls-files", "backend/ai/models/"],
                             capture_output=True, text=True).stdout.split()
    assert not any("digibone" in t.lower() for t in tracked), (
        f"digiBONE artefacts are committed: {[t for t in tracked if 'digibone' in t.lower()]}"
    )
