"""The local Indian dual-read cohort: freezing it, and getting a number out.

Existing coverage exercised the EMPTY case only -- survey reports nothing, freeze
refuses. That left two things untested and both were broken:

1. ``freeze`` wrote to the shared default registry path, so freezing this cohort
   OVERWROTE the RSNA locked test: 1,425 held-out images replaced by a few
   hundred, and every later leak check passing vacuously against the wrong set.
2. Nothing could evaluate against what was frozen. ``baseline_report`` reads
   RSNA label files from disk; this cohort lives in the database. So the carve
   was inert -- the fifth prepared-but-unconsumed asset in this project.

The films below are fabricated rows in a temp database. They are a harness for
the machinery, not clinical data, and no image is ever inferred on: the model
call is stubbed so these tests exercise selection, exclusion, strata and the
inter-reader floor rather than ONNX.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta

# Set before backend.db is imported, matching the convention in the other
# bone-age suites. Deliberately NOT importlib.reload(backend.db): reloading
# swaps the process-wide engine, which broke twelve unrelated tests the last
# time it was done in this project.
os.environ.setdefault("TW3_DB_PATH",
                      os.path.join(tempfile.mkdtemp(), "local_cohort_test.db"))

import pytest  # noqa: E402

from backend.ai.validation import carve_local_cohort as carve  # noqa: E402
from backend.ai.validation import leak_guard  # noqa: E402
from backend.ai.validation import local_cohort_report as report_mod  # noqa: E402


@pytest.fixture
def db():
    """A session on an empty database.

    One engine for the whole module, so the tables are cleared between tests
    rather than the engine rebuilt. patient_code is UNIQUE, so leftover rows
    from a previous test surface as an integrity error rather than as a wrong
    answer -- which is how this fixture's first version was caught.
    """
    from backend.db import init_db, session_scope
    from backend.models import (
        Patient, PubertyAssessment, Radiograph, TW3Assessment,
    )

    init_db()
    with session_scope() as session:
        for model in (TW3Assessment, PubertyAssessment, Radiograph, Patient):
            session.query(model).delete()
        session.commit()
        yield session


@pytest.fixture
def registry_dir(tmp_path, monkeypatch):
    """Point the registry at a temp dir so no test can touch the real one."""
    monkeypatch.setattr(leak_guard, "_REGISTRY_PATH", tmp_path / "locked_test.json")
    return tmp_path


_SEQ = iter(range(1, 100_000))


def _film(db, *, sex, pubertal, reads, image_path, patient_seq=None):
    """One patient + radiograph + N independent reads."""
    from backend.models import (
        Patient, PubertyAssessment, Radiograph, TW3Assessment,
    )

    patient_seq = next(_SEQ) if patient_seq is None else patient_seq
    p = Patient(sex_at_birth=sex, name=f"P{patient_seq}",
                patient_code=f"C{patient_seq}")
    db.add(p)
    db.flush()

    if pubertal is not None:
        db.add(PubertyAssessment(
            patient_id=p.id, assessed_at=datetime.utcnow(),
            breast_stage=3 if pubertal else 1,
            genital_stage=3 if pubertal else 1))

    rg = Radiograph(patient_id=p.id, image_hash=f"hash-{patient_seq}",
                    internal_file_path=str(image_path))
    db.add(rg)
    db.flush()

    for i, months in enumerate(reads):
        db.add(TW3Assessment(
            patient_id=p.id, radiograph_id=rg.id, reader_id=f"reader-{i}",
            sex_at_birth=sex, bone_age_months=months, read_round=i + 1,
            updated_at=datetime.utcnow() + timedelta(seconds=i)))
    db.flush()
    return rg


@pytest.fixture
def populated(db, tmp_path):
    """A small cohort spanning all four strata, with a real file on disk."""
    image = tmp_path / "film.png"
    image.write_bytes(b"fake-image-bytes")

    seq = 0
    made = []
    for sex in ("boys", "girls"):
        for pubertal in (True, False):
            for _ in range(3):
                seq += 1
                made.append(_film(db, sex=sex, pubertal=pubertal,
                                  reads=[120 + seq, 126 + seq],   # 6mo apart
                                  image_path=image, patient_seq=seq))
    db.commit()
    return made


@pytest.fixture
def stub_model(monkeypatch):
    """No ONNX. The model always answers 123 months, on the GP scale."""
    from backend.ai import active_model, boneage, registry

    spec = registry.ModelSpec(
        model_id="stub-gp", kind="screening", method="greulich-pyle",
        onnx_path=type("P", (), {"exists": lambda self: True})(),
        input_size=224, preprocessing_version="prep-1.0-minmax",
        population="RSNA-US")
    monkeypatch.setattr(active_model, "active_spec", lambda: spec)
    monkeypatch.setattr(boneage, "predict_months",
                        lambda blob, is_male: {"bone_age_months": 123,
                                               "uncertainty_months": 8.0,
                                               "is_tw3_scale": False})
    return spec


# â”€â”€ the registry-clobbering defect â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_freezing_the_cohort_does_not_overwrite_the_rsna_locked_test(registry_dir):
    """The defect: both carves called save_registry with no path, so the local
    freeze replaced the RSNA registry -- destroying the record of what is
    off-limits to training, and leaving later leak checks to pass vacuously."""
    rsna_path = leak_guard._REGISTRY_PATH
    leak_guard.save_registry(
        [f"p{i}" for i in range(1425)], [f"h{i}" for i in range(1425)],
        dataset="rsna-bone-age-validation-2017", source="internal-rsna",
        path=rsna_path)

    local_path = leak_guard.registry_path(carve.DATASET)
    assert local_path != rsna_path, "the two frozen sets share a filename"

    leak_guard.save_registry(["1", "2"], ["ha", "hb"],
                             dataset=carve.DATASET, source=carve.SOURCE,
                             path=local_path)

    survivor = leak_guard.load_registry(rsna_path)
    assert survivor.dataset == "rsna-bone-age-validation-2017"
    assert len(survivor.patient_ids) == 1425, "the RSNA locked test was clobbered"


def test_carve_freeze_leaves_the_rsna_registry_intact(db, populated, registry_dir):
    """The defect end to end, through the real entry point.

    The test above drives save_registry directly, so it passes even against the
    original code -- which is how it was caught being weak. This one calls
    carve.freeze, which is what actually destroyed the RSNA registry.
    """
    rsna_path = leak_guard._REGISTRY_PATH
    leak_guard.save_registry(
        [f"p{i}" for i in range(1425)], [f"h{i}" for i in range(1425)],
        dataset="rsna-bone-age-validation-2017", source="internal-rsna",
        path=rsna_path)
    before = rsna_path.read_bytes()

    result = carve.freeze(db, force=True)

    assert rsna_path.read_bytes() == before, (
        "carve.freeze rewrote the RSNA locked-test registry — 1,425 held-out "
        "images replaced, and every later leak check passing against the wrong set"
    )
    assert leak_guard.load_registry(rsna_path).dataset == "rsna-bone-age-validation-2017"

    local = leak_guard.load_registry(leak_guard.registry_path(carve.DATASET))
    assert local.dataset == carve.DATASET
    assert len(local.patient_ids) == 12
    assert result["registry_path"].endswith(
        leak_guard.registry_path(carve.DATASET).name)


def test_writing_a_different_dataset_over_a_registry_is_refused(registry_dir):
    """Belt as well as braces: even with an explicit path, replacing one frozen
    set with another must be deliberate. The checksum lock stops edits; nothing
    stopped a wholesale overwrite."""
    path = registry_dir / "locked_test.json"
    leak_guard.save_registry(["a"], ["h"], dataset="rsna-x", source="internal-rsna",
                             path=path)
    with pytest.raises(leak_guard.RegistryError, match="Refusing to overwrite"):
        leak_guard.save_registry(["b"], ["h2"], dataset=carve.DATASET,
                                 source=carve.SOURCE, path=path)

    # A deliberate re-carve is still possible.
    reg = leak_guard.save_registry(["b"], ["h2"], dataset=carve.DATASET,
                                   source=carve.SOURCE, path=path,
                                   allow_replace=True)
    assert reg.dataset == carve.DATASET


def test_rewriting_the_same_dataset_is_allowed(registry_dir):
    path = leak_guard.registry_path(carve.DATASET)
    leak_guard.save_registry(["a"], ["h"], dataset=carve.DATASET,
                             source=carve.SOURCE, path=path)
    reg = leak_guard.save_registry(["a", "b"], ["h", "h2"], dataset=carve.DATASET,
                                   source=carve.SOURCE, path=path)
    assert len(reg.patient_ids) == 2


def test_the_rsna_dataset_keeps_the_unsuffixed_filename():
    """It was frozen first and is referenced by that name; changing it would
    orphan the committed registry."""
    assert leak_guard.registry_path("rsna-bone-age-validation-2017").name == "locked_test.json"
    assert leak_guard.registry_path(carve.DATASET).name != "locked_test.json"


# â”€â”€ the carve, on a populated database â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_survey_finds_eligible_films_and_strata(db, populated):
    """Previously only the empty case was covered."""
    r = carve.survey(db)
    assert len(r.eligible) == 12
    assert set(r.strata) == {"boys:pubertal", "boys:prepubertal",
                             "girls:pubertal", "girls:prepubertal"}
    assert all(v == 3 for v in r.strata.values())
    assert r.ready_to_freeze is False, "12 films is far below the target"


def test_a_single_reader_film_is_excluded(db, populated, tmp_path):
    """A cohort labelled by one reader measures agreement with that reader, not
    accuracy â€” bone age has no ground truth beyond expert reading."""
    image = tmp_path / "film.png"
    _film(db, sex="boys", pubertal=True, reads=[130], image_path=image,
          patient_seq=99)
    db.commit()

    r = carve.survey(db)
    assert len(r.eligible) == 12, "a single-read film entered the cohort"
    assert r.rejected["too_few_readers"], "the exclusion was not recorded"


def test_a_film_with_unknown_pubertal_status_is_excluded(db, populated, tmp_path):
    """Excluded rather than guessed into a stratum: pubertal status is the whole
    reason for stratifying, so assuming it defeats the purpose."""
    image = tmp_path / "film.png"
    _film(db, sex="boys", pubertal=None, reads=[130, 136], image_path=image,
          patient_seq=98)
    db.commit()

    r = carve.survey(db)
    assert len(r.eligible) == 12
    assert r.rejected["pubertal_status_unknown"]


# â”€â”€ evaluation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_report_refuses_before_the_cohort_is_frozen(db, registry_dir, stub_model):
    with pytest.raises(report_mod.CohortReportError, match="carve_local_cohort"):
        report_mod.run(db)


def test_report_produces_a_number_from_the_frozen_cohort(db, populated, registry_dir,
                                                         stub_model):
    """The gap this module closed: the carve could freeze and nothing could then
    evaluate against what it froze."""
    carve.freeze(db, force=True)
    report = report_mod.run(db)

    assert report["provenance"]["n_evaluated"] == 12
    assert report["provenance"]["cohort_source"] == "external-india"
    assert report["headline"]["mae_months"] is not None
    strata = {c["group"]["stratum"] for c in report["subgroups"]["by_stratum"]["subgroups"]}
    assert "boys:pubertal" in strata


def test_the_inter_reader_floor_is_reported_beside_the_model_error(db, populated,
                                                                  registry_dir,
                                                                  stub_model):
    """Bone age has no ground truth. A model MAE quoted alone invites the reader
    to treat the consensus as truth; the readers' own spread is the floor."""
    carve.freeze(db, force=True)
    report = report_mod.run(db)

    readers = report["reader_disagreement"]
    assert readers["available"] is True
    assert readers["n_films"] == 12
    assert readers["mean_spread_months"] == pytest.approx(6.0), (
        "each fixture film has two reads 6 months apart"
    )
    assert "noise floor" in readers["note"]
    assert any("inter-reader spread" in line for line in report["interpretation"])


def test_two_reader_consensus_is_a_true_median_not_the_higher_read(db, tmp_path,
                                                                   registry_dir,
                                                                   stub_model):
    """`sorted(ages)[len//2]` returns the UPPER of two values.

    Two readers is the mandated minimum and the expected case, so that rule made
    every dual-read label the higher read -- biasing the reference standard up by
    half the reader disagreement and charging that bias to the model as error.
    With reads 6 months apart the label must be the midpoint, not the top.
    """
    image = tmp_path / "film.png"
    image.write_bytes(b"fake")
    for _ in range(4):
        _film(db, sex="boys", pubertal=True, reads=[120, 126], image_path=image)
    db.commit()

    r = carve.survey(db)
    assert all(f.consensus_bone_age_months == 123 for f in r.eligible), (
        "consensus is not the midpoint of the two reads: "
        f"{[f.consensus_bone_age_months for f in r.eligible]}"
    )


def test_an_odd_number_of_readers_still_picks_the_middle_value(db, tmp_path,
                                                               registry_dir):
    """The fix must not disturb the three-reader case."""
    image = tmp_path / "film.png"
    image.write_bytes(b"fake")
    _film(db, sex="girls", pubertal=False, reads=[100, 104, 140], image_path=image)
    db.commit()

    r = carve.survey(db)
    assert r.eligible[0].consensus_bone_age_months == 104, (
        "an outlying third read moved the median"
    )


def test_a_model_inside_the_reader_spread_is_not_called_better(db, tmp_path,
                                                              registry_dir,
                                                              monkeypatch):
    """The claim that must never be made: there is no ground truth to beat."""
    from backend.ai import active_model, boneage, registry

    spec = registry.ModelSpec(
        model_id="stub", kind="screening", method="greulich-pyle",
        onnx_path=type("P", (), {"exists": lambda self: True})(),
        input_size=224, preprocessing_version="prep-1.0-minmax",
        population="RSNA-US")
    monkeypatch.setattr(active_model, "active_spec", lambda: spec)
    # Every film here has the SAME two reads, so one fixed prediction can sit
    # close to every consensus. (The first version of this test used the varied
    # `populated` cohort with a fixed prediction, which produced an MAE of 8.5
    # and tested the opposite branch.)
    image = tmp_path / "film.png"
    image.write_bytes(b"fake")
    for _ in range(6):
        _film(db, sex="boys", pubertal=True, reads=[120, 126], image_path=image)
    db.commit()
    monkeypatch.setattr(boneage, "predict_months",
                        lambda blob, is_male: {"bone_age_months": 124,
                                               "uncertainty_months": 2.0,
                                               "is_tw3_scale": False})
    carve.freeze(db, force=True)
    report = report_mod.run(db)
    assert report["headline"]["mae_months"] < 6.0, "fixture no longer sits under the floor"

    text = " ".join(report["interpretation"])
    assert "at or below the inter-reader spread" in text
    assert "NOT evidence that it beats the readers" in text
    for line in report["interpretation"]:
        assert "outperform" not in line.lower()


def test_a_tw3_scale_model_is_excluded_not_compared(db, populated, registry_dir,
                                                    monkeypatch):
    """Greulich-Pyle and TW3 are different standards. Scoring one against the
    other's consensus is a category error, so such films are excluded and
    counted rather than silently compared."""
    from backend.ai import active_model, boneage, registry

    spec = registry.ModelSpec(
        model_id="stub-tw3", kind="screening", method="tw3-rus",
        onnx_path=type("P", (), {"exists": lambda self: True})(),
        input_size=224, preprocessing_version="prep-1.0-minmax",
        population="Indian-HCJMRI")
    monkeypatch.setattr(active_model, "active_spec", lambda: spec)
    monkeypatch.setattr(boneage, "predict_months",
                        lambda blob, is_male: {"bone_age_months": 123,
                                               "uncertainty_months": 8.0,
                                               "is_tw3_scale": True})
    carve.freeze(db, force=True)
    with pytest.raises(report_mod.CohortReportError, match="method_mismatch"):
        report_mod.run(db)


def test_a_leaked_cohort_is_refused(db, populated, registry_dir, stub_model):
    """A cohort that fed training, tuning, feedback or calibration measures
    nothing."""
    carve.freeze(db, force=True)
    leaked = {"train": {"image_hashes": ["hash-1"]}}
    with pytest.raises(leak_guard.LeakError, match="leaks into 'train'"):
        report_mod.run(db, training_sets=leaked)


def test_a_missing_image_file_is_counted_not_ignored(db, populated, registry_dir,
                                                     stub_model, tmp_path):
    """A film whose bytes are gone must reduce n_evaluated visibly -- silently
    dropping it would inflate the apparent cohort size."""
    (tmp_path / "film.png").unlink()
    carve.freeze(db, force=True)
    with pytest.raises(report_mod.CohortReportError, match="no_image"):
        report_mod.run(db)


def test_the_critical_subgroup_is_called_out_when_absent(db, registry_dir,
                                                         stub_model, tmp_path):
    """Published Indian data show TW3 is worst of three methods in pubertal boys.
    A cohort missing that stratum must say so rather than let a headline average
    imply coverage it does not have."""
    image = tmp_path / "film.png"
    image.write_bytes(b"fake")
    for i in range(4):
        _film(db, sex="girls", pubertal=False, reads=[120 + i, 126 + i],
              image_path=image, patient_seq=200 + i)
    db.commit()

    carve.freeze(db, force=True)
    report = report_mod.run(db)
    assert any("boys:pubertal" in line and "unmeasured" in line
               for line in report["interpretation"])


def test_the_report_never_calls_the_consensus_ground_truth(db, populated,
                                                           registry_dir, stub_model):
    carve.freeze(db, force=True)
    report = report_mod.run(db)
    standard = report["provenance"]["reference_standard"]
    assert "NOT ground truth" in standard
    assert report["provenance"]["min_readers"] >= 2
    assert json.dumps(report).count("ground truth") == 1, (
        "the phrase should appear only where it is being denied"
    )
