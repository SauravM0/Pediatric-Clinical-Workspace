"""Rater identity (Plan 2 WI-1) + consent gate on export (Plan 2 WI-9)."""
import os
import tempfile

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "rater_consent_test.db"))

from pathlib import Path

import pytest

from backend import assessment_service as svc
from backend.db import init_db, session_scope
from backend.models import Radiograph
from backend.tw3.pipeline.export_dataset import _consent_ok, export_dataset


@pytest.fixture(scope="module", autouse=True)
def _db():
    init_db()


# ── WI-1: rater identity ─────────────────────────────────────────────────────

def test_reader_and_rater_identity_persist():
    with session_scope() as db:
        a = svc.create_assessment(db, patient_code="P-rater-1", sex="girls",
                                  reader_id="DR_A", read_round=1)
        svc.set_bone_stage(db, a.id, "radius", "4", rater_id="DR_A")
        aid = a.id
    with session_scope() as db:
        a = svc.get_assessment(db, aid)
        assert a.reader_id == "DR_A" and a.read_round == 1
        radius = next(b for b in a.bones if b.bone_code == "radius")
        assert radius.rater_id == "DR_A"


def test_two_independent_reads_store_distinct_readers():
    with session_scope() as db:
        a1 = svc.create_assessment(db, patient_code="P-rater-2", sex="boys",
                                   reader_id="DR_A", read_round=1)
        a2 = svc.create_assessment(db, patient_code="P-rater-2", sex="boys",
                                   reader_id="DR_B", read_round=2)
        ids = (a1.id, a2.id)
    with session_scope() as db:
        r1, r2 = svc.get_assessment(db, ids[0]), svc.get_assessment(db, ids[1])
        assert {r1.reader_id, r2.reader_id} == {"DR_A", "DR_B"}
        assert r1.read_round != r2.read_round


# ── WI-9: consent gate ───────────────────────────────────────────────────────

def test_consent_ok_rules():
    class RG:
        def __init__(self, s): self.consent_status = s
    # 'withheld' is always excluded
    assert _consent_ok(RG("withheld"), require_consent=False) is False
    assert _consent_ok(RG("withheld"), require_consent=True) is False
    # unknown allowed only when not requiring positive consent
    assert _consent_ok(RG(None), require_consent=False) is True
    assert _consent_ok(RG(None), require_consent=True) is False
    # positively consented always ok
    assert _consent_ok(RG("consented"), require_consent=True) is True
    assert _consent_ok(RG("research_ok"), require_consent=True) is True


def _make_case(db, code, consent):
    a = svc.create_assessment(db, patient_code=code, sex="girls")
    rg = Radiograph(patient_id=a.patient_id, consent_status=consent)
    db.add(rg)
    db.flush()
    a.radiograph_id = rg.id
    svc.set_bone_stage(db, a.id, "radius", "4")
    return a


def test_export_excludes_withheld_films(tmp_path):
    with session_scope() as db:
        _make_case(db, "P-consent-ok", "consented")
        _make_case(db, "P-consent-no", "withheld")
    with session_scope() as db:
        manifest = export_dataset(db, tmp_path / "ds", require_consent=False)
    # the withheld film is excluded regardless of require_consent
    assert manifest["counts"]["excluded_by_consent"] >= 1
    codes = _exported_codes(tmp_path / "ds")
    assert "P-consent-no" not in codes
    assert "P-consent-ok" in codes


def _exported_codes(out_dir: Path) -> set:
    import csv
    with (out_dir / "patients.csv").open(encoding="utf-8") as fh:
        return {row["patient_code"] for row in csv.DictReader(fh)}
