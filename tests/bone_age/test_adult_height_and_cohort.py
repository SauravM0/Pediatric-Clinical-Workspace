"""M2C: adult-height prediction from bone age, and the local cohort carve.

Both are gated on inputs the project does not hold — the licensed TW3 tables and
a dual-read Indian cohort. The tests that need those skip; the rest verify that
the gates hold and that the machinery is correct when fed a fixture.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from backend.tw3 import adult_height as ah
from backend.tw3 import tables as tw3_tables


class _FakeTables:
    """Stands in for ScoringTables with a chosen pct_adult_height block.

    A fixture, not a reference: the percentages are illustrative, which is why
    they live in a test and never in letters_tables.json.

    Presents as fully licensed by default -- documented provenance and a verified
    checksum -- because these tests are about the arithmetic and the refusals.
    The licensing gate itself is exercised in test_adult_height_ingestion.py,
    which drives this same class's inputs the other way.
    """

    _PROVENANCE_OK = {f: "test" for f in (
        "book_title", "edition", "licensed_owner", "entered_by", "verified_by",
        "verification_date")}

    def __init__(self, boys=None, girls=None, *, licensed=True):
        self.raw = {"pct_adult_height": {"boys": boys or [], "girls": girls or []}}
        self.checksum_verified = licensed
        self._provenance = self._PROVENANCE_OK if licensed else {}

    def missing_provenance(self):
        return [f for f in self._PROVENANCE_OK if not self._provenance.get(f)]


# A plausible monotone %-attained curve, for exercising the arithmetic only.
_FIXTURE = [[8.0, 70.0], [10.0, 78.0], [12.0, 86.0], [14.0, 94.0], [16.0, 99.0]]


# ── gating ──────────────────────────────────────────────────────────────────

def test_prediction_is_disabled_without_the_licensed_table():
    from backend.tw3.letters_scoring import load_letter_tables

    r = ah.predict("boys", 140.0, 11.0, load_letter_tables())
    assert r.available is False
    assert "copyrighted" in r.status and "Tanner" in r.status
    assert r.predicted_cm is None


def test_the_percentage_table_lives_with_the_LICENSED_tables():
    """It belongs in letters_tables.json, not tw3_tables.json.

    tw3_tables.json holds the TW3-C values transcribed from a published paper --
    freely usable. letters_tables.json holds copyrighted original-TW3 content
    that a clinic must enter from its own licensed copy, behind the four
    provenance gates. The percentage-of-adult-height table is the latter, and
    putting it in the wrong file would route copyrighted values around those
    gates entirely.
    """
    from backend.tw3.letters_scoring import load_letter_tables

    assert "pct_adult_height" not in tw3_tables.load_tables().raw
    assert "pct_adult_height" in load_letter_tables().raw


def test_the_shipped_table_slot_is_empty():
    """It must stay empty. A plausible-looking fabricated table is exactly what
    the licensing gate exists to prevent, and shipping one invites it."""
    from backend.tw3.letters_scoring import load_letter_tables

    raw = load_letter_tables().raw.get("pct_adult_height", {})
    assert raw.get("boys") == [] and raw.get("girls") == []
    assert "Bayley-Pinneau" in raw["_fill"], (
        "the slot must warn against substituting BP percentages -- a different "
        "method on a different bone age, removed from this product deliberately"
    )


def test_is_calibrated_requires_at_least_two_anchors():
    assert ah.is_calibrated("boys", _FakeTables(boys=_FIXTURE)) is True
    assert ah.is_calibrated("boys", _FakeTables(boys=[[10.0, 78.0]])) is False
    assert ah.is_calibrated("girls", _FakeTables(boys=_FIXTURE)) is False


# ── arithmetic ──────────────────────────────────────────────────────────────

def test_prediction_divides_current_height_by_percent_attained():
    r = ah.predict("boys", 140.0, 12.0, _FakeTables(boys=_FIXTURE))
    assert r.available is True
    assert r.percent_attained == pytest.approx(86.0)
    assert r.predicted_cm == pytest.approx(140.0 / 0.86, abs=0.1)


def test_percent_is_read_against_bone_age_not_chronological_age():
    """The entire point of the method: two children of identical height with
    different skeletal maturity have different adult heights ahead of them."""
    tables = _FakeTables(boys=_FIXTURE)
    delayed = ah.predict("boys", 140.0, 10.0, tables)     # 2y skeletally delayed
    advanced = ah.predict("boys", 140.0, 14.0, tables)    # 2y advanced
    assert delayed.predicted_cm > advanced.predicted_cm, (
        "a skeletally delayed child must be predicted TALLER for the same current "
        "height -- they have more growth remaining"
    )


def test_interpolates_between_anchors():
    r = ah.predict("boys", 140.0, 11.0, _FakeTables(boys=_FIXTURE))
    assert r.percent_attained == pytest.approx(82.0)      # midway 78 -> 86


def test_uncertainty_range_is_the_right_way_round():
    """A HIGHER bone age means more growth already achieved, so a LOWER predicted
    adult height. The mapping inverts, which is easy to get backwards and would
    report the interval upside down."""
    r = ah.predict("boys", 140.0, 12.0, _FakeTables(boys=_FIXTURE),
                   bone_age_uncertainty_years=0.5)
    assert r.range_cm is not None
    lo, hi = r.range_cm
    assert lo < r.predicted_cm < hi
    at_older = ah.predict("boys", 140.0, 12.5, _FakeTables(boys=_FIXTURE)).predicted_cm
    assert at_older == pytest.approx(lo, abs=0.15), "older bone age is not the LOW bound"


def test_caveat_names_the_bone_age_dependency():
    r = ah.predict("boys", 140.0, 12.0, _FakeTables(boys=_FIXTURE))
    assert "inherits the uncertainty of the bone age" in r.caveat


# ── refusals ────────────────────────────────────────────────────────────────

def test_outside_the_table_is_not_extrapolated():
    """Same rule as the RUS score->age curve (M3.1): an endpoint value presented
    as a result is indistinguishable from a computed one."""
    tables = _FakeTables(boys=_FIXTURE)
    assert ah.predict("boys", 140.0, 17.5, tables).available is False
    assert "not extrapolated" in ah.predict("boys", 140.0, 17.5, tables).status


def test_very_young_bone_age_is_refused():
    """Below ~6y the fraction attained is small, so dividing by it multiplies any
    bone-age error into a large error in the prediction.

    The table has to run to maturity or M2C's shape gate rejects it first, which
    would make this pass for the wrong reason.
    """
    young = _FakeTables(boys=[[4.0, 50.0], [8.0, 70.0], [16.5, 99.5]])
    assert ah.shape_problems("boys", young) == [], "fixture trips the shape gate"
    r = ah.predict("boys", 100.0, 5.0, young)
    assert r.available is False and "multiplies any" in r.status


def test_missing_bone_age_or_height_is_refused():
    tables = _FakeTables(boys=_FIXTURE)
    assert ah.predict("boys", 140.0, None, tables).available is False
    assert ah.predict("boys", 0.0, 12.0, tables).available is False


def test_fractions_entered_as_percentages_are_refused():
    """Since M2C this is caught by the shape gate, before any interpolation --
    the whole table is inspected rather than one looked-up value. The message
    still has to name the actual mistake."""
    r = ah.predict("boys", 140.0, 12.0, _FakeTables(boys=[[8.0, 0.7], [16.0, 0.99]]))
    assert r.available is False
    assert "fractions" in r.status


# ── local validation cohort ─────────────────────────────────────────────────

def test_cohort_survey_reports_what_is_missing():
    """With no dual-read films stored, the carve must say so rather than freeze
    an empty or thin set."""
    import os
    import tempfile

    os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "cohort.db"))
    from backend.ai.validation import carve_local_cohort as carve
    from backend.db import init_db, session_scope

    init_db()
    with session_scope() as db:
        report = carve.survey(db)

    assert report.ready_to_freeze is False
    body = report.to_dict()
    assert body["target_size"] == carve.TARGET_SIZE
    assert any("pubertal boys" in r for r in report.reasons), (
        "the stratum reason must explain WHY thinness matters -- published Indian "
        "data show TW3 is worst of three methods in pubertal boys"
    )


def test_freezing_an_unready_cohort_is_refused():
    import os
    import tempfile

    os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "cohort.db"))
    from backend.ai.validation import carve_local_cohort as carve
    from backend.db import init_db, session_scope

    init_db()
    with session_scope() as db:
        with pytest.raises(carve.CohortError, match="not ready to freeze"):
            carve.freeze(db)


def test_cohort_requires_two_distinct_readers():
    """A cohort labelled by one reader measures agreement with that reader, not
    accuracy — bone age has no ground truth beyond expert reading."""
    from backend.ai.validation import carve_local_cohort as carve

    assert carve.MIN_READERS >= 2


def test_cohort_strata_cover_sex_by_pubertal_status():
    from backend.ai.validation import carve_local_cohort as carve

    assert set(carve.PUBERTAL_STRATA) == {"prepubertal", "pubertal"}
    assert carve.MIN_PER_STRATUM >= 10
    assert carve.SOURCE == "external-india", (
        "the cohort must register under a source distinct from internal-rsna, or "
        "the leak guard cannot tell the two test sets apart"
    )
