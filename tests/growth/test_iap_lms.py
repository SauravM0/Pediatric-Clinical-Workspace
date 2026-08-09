"""The M1.1 equivalence gate.

Most of this file SKIPS today, because the IAP 2015 L,M,S values are not public
and are not invented here. The tests are written now so that installing the file
is a data step with an automatic verdict, rather than a code change made months
later by someone reconstructing what "correct" meant.

Two of them are the gate proper:

* :func:`test_lms_reproduces_every_published_cell` — a transcription error in an
  L,M,S triplet is invisible by inspection but shows up immediately as a centile
  that does not match the paper.
* :func:`test_lms_agrees_with_the_legacy_engine_across_a_dense_grid` — a sanity
  band, not equality. The legacy path is a 2-parameter fit to 6 points, so it is
  *expected* to differ slightly; a large divergence means the new file is wrong,
  not that the old one was.

The tests that always run cover the parts that do not need the data: that the
path stays inert without it, that a malformed file is rejected loudly, and that
the module never silently substitutes a guess.
"""
from __future__ import annotations

import numpy as np
import pytest

from backend.growth import blend, iap_lms_reference as lms
from backend.growth import iap_reference as legacy
from backend.growth.lms_core import lms_value_at_z, lms_z_score

requires_lms = pytest.mark.skipif(
    not lms.lms_available(),
    reason="IAP 2015 L,M,S not installed — see backend/growth/data/IAP-LMS-REQUEST.md",
)

_STANDARD_Z = (-1.88079, -1.28155, -0.67449, 0.0, 0.67449, 1.28155, 1.88079)
_AGES = [round(5.0 + 0.25 * i, 2) for i in range(53)]   # 5.0 .. 18.0, 0.25y


def _expected_judged_cells() -> int:
    """How many cells the gate should examine, derived rather than hardcoded.

    Was a flat "at least 1,000 of the 1,134 published". That became wrong when
    M1.1 excluded the four reconstructed height/weight columns (594 cells now),
    and a magic number cannot tell "the gate was narrowed for a reason" from
    "the gate stopped looking". Deriving it from the same registry the gate uses
    means this tracks a deliberate change and still catches an accidental one.
    """
    from backend.growth import iap_table_consistency as tc
    from backend.growth import measures as m

    return len(lms.REQUIRED_AGES) * len(lms.SEXES) * sum(
        len(tc.gate_centiles(k)) for k in m.IAP_TABLE_KEYS
    )


# ── always run: the path must stay inert and honest without data ────────────

def test_path_is_inactive_without_data():
    if lms.LMS_PATH.exists():
        pytest.skip("LMS data installed; inactivity no longer applicable")
    assert lms.lms_available() is False
    assert lms.iap_lms_value_at_z("height", "boys", 10.0, 0.0) is None
    assert lms.iap_lms_z_for_value("height", "boys", 10.0, 140.0) is None


def test_status_explains_itself_rather_than_failing_silently():
    status = lms.lms_status()
    assert "active" in status and "reason" in status
    if not status["active"]:
        assert len(status["reason"]) > 40, "an inactive path must say why"


def test_env_kill_switch_is_a_disable_not_an_enable(monkeypatch):
    """PCW_DISABLE_IAP_LMS can only turn the path OFF. There is deliberately no
    variable that forces it ON: activation is earned by reproducing the
    published table, so a flag could not make a bad file trustworthy."""
    monkeypatch.setenv("PCW_DISABLE_IAP_LMS", "1")
    assert lms.disabled_by_env() is True
    assert lms.lms_available() is False


def test_template_exists_and_carries_no_values():
    """The template must never acquire numbers -- a plausible-looking fabricated
    file is exactly what the gate exists to catch, and shipping one invites it."""
    template = lms.LMS_PATH.parent / "iap_2015_lms.template.csv"
    assert template.exists()
    body = [ln for ln in template.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#") and not ln.startswith("sex,")]
    assert body == [], f"the template contains data rows: {body[:3]}"


def test_required_grid_is_the_full_published_range():
    assert lms.REQUIRED_AGES[0] == 5.0 and lms.REQUIRED_AGES[-1] == 18.0
    assert len(lms.REQUIRED_AGES) == 27


def test_partial_table_is_rejected_not_extrapolated(tmp_path, monkeypatch):
    """A file covering only part of the age range must fail loudly. Silently
    interpolating across a gap would produce a reference nobody published."""
    partial = tmp_path / "iap_2015_lms.csv"
    rows = ["sex,measure,age_years,L,M,S"]
    for sex in ("boy", "girl"):
        for measure in ("height", "weight", "bmi"):
            for age in (5.0, 5.5, 6.0):        # far short of 18.0
                rows.append(f"{sex},{measure},{age},1.0,100.0,0.1")
    partial.write_text("\n".join(rows), encoding="utf-8")

    monkeypatch.setattr(lms, "LMS_PATH", partial)
    lms.reset_cache()
    try:
        with pytest.raises(lms.LmsDataError, match="missing for age"):
            lms._load()
    finally:
        lms.reset_cache()


def test_nonsense_parameters_are_rejected(tmp_path, monkeypatch):
    bad = tmp_path / "iap_2015_lms.csv"
    bad.write_text("sex,measure,age_years,L,M,S\nboy,height,5.0,1.0,-100.0,0.1\n",
                   encoding="utf-8")
    monkeypatch.setattr(lms, "LMS_PATH", bad)
    lms.reset_cache()
    try:
        with pytest.raises(lms.LmsDataError, match="must be positive"):
            lms._load()
    finally:
        lms.reset_cache()


def test_cole_handles_l_near_zero():
    """Cole degenerates at L=0 and must use the log form X = M*exp(S*z). Not
    theoretical: the current engine fits L as low as 0.005 for girls' BMI, so
    this branch is exercised on real data."""
    import math

    for L in (1.0, 1e-3, 1e-8, 0.0, -0.5):
        value = lms_value_at_z(L, 100.0, 0.10, 1.0)
        expected = 100.0 * math.exp(0.10) if L == 0 else 100.0 * (1 + L * 0.10) ** (1 / L)
        assert value == pytest.approx(expected, abs=1e-6), f"L={L}"
        assert lms_z_score(value, L, 100.0, 0.10) == pytest.approx(1.0, abs=1e-6)


# ── the gate: runs automatically once the data lands ────────────────────────

@requires_lms
def test_lms_reproduces_every_published_cell():
    """THE gate. If the LMS cannot regenerate the paper's own percentile table,
    the transcription is wrong -- and a wrong L,M,S is undetectable by eye."""
    report = lms._reproduction()
    assert report["checked"] == _expected_judged_cells(), (
        f"gate examined {report['checked']} cells, expected {_expected_judged_cells()}"
    )
    for measure, worst in report["worst"].items():
        assert worst <= lms.REPRODUCTION_TOL[measure], (
            f"{measure}: worst deviation {worst} exceeds {lms.REPRODUCTION_TOL[measure]}"
        )


@requires_lms
@pytest.mark.parametrize("sex", ["boys", "girls"])
@pytest.mark.parametrize("measure", ["height", "weight", "bmi"])
def test_lms_agrees_with_the_legacy_engine_across_a_dense_grid(sex, measure):
    """Sanity band, not equality. The legacy path is a 2-parameter fit to 6
    published points, so it is expected to differ a little; a large divergence
    means the NEW file is wrong, not that the old one was."""
    tol = {"height": 1.5, "weight": 1.5, "bmi": 1.0}[measure]
    worst = 0.0
    for age in _AGES:
        for z in _STANDARD_Z:
            new = lms.iap_lms_value_at_z(measure, sex, age, z)
            old = legacy.iap_value_at_z(measure, sex, age, z)
            if new is None or old is None:
                continue
            worst = max(worst, abs(new - old))
    assert worst <= tol, f"{sex}/{measure}: diverges from the legacy engine by {worst:.3f}"


@requires_lms
@pytest.mark.parametrize("sex", ["boys", "girls"])
@pytest.mark.parametrize("measure", ["height", "weight", "bmi"])
def test_value_and_z_are_exact_inverses(sex, measure):
    """The property the legacy path could only approximate: one closed-form
    transform, so display and scoring agree everywhere, tails included."""
    for age in (5.0, 8.5, 12.0, 15.5, 18.0):
        for z in (-3.5, -3.0, -2.0, 0.0, 2.0, 3.0, 3.5):
            value = lms.iap_lms_value_at_z(measure, sex, age, z)
            assert value is not None
            assert lms.iap_lms_z_for_value(measure, sex, age, value) == pytest.approx(z, abs=1e-6)


@requires_lms
@pytest.mark.parametrize("sex", ["boys", "girls"])
@pytest.mark.parametrize("measure", ["height", "weight", "bmi"])
def test_tail_error_is_eliminated_not_merely_reduced(sex, measure):
    """M1.2 left a residual ~0.07 SD because it grafted an LMS-shaped tail onto a
    fitted ladder. With real parameters the tail IS the distribution."""
    for age in (6.0, 10.0, 14.0, 17.0):
        for target in (-4.0, -3.0, 3.0, 4.0):
            value = lms.iap_lms_value_at_z(measure, sex, age, target)
            got = lms.iap_lms_z_for_value(measure, sex, age, value)
            assert got == pytest.approx(target, abs=1e-6)


@requires_lms
@pytest.mark.parametrize("sex", ["boys", "girls"])
def test_centiles_never_cross(sex):
    for measure in ("height", "weight", "bmi"):
        for age in _AGES:
            values = [lms.iap_lms_value_at_z(measure, sex, age, z) for z in _STANDARD_Z]
            assert all(np.diff(values) > 0), f"{sex}/{measure} centiles cross at {age}"


@requires_lms
@pytest.mark.parametrize("sex", ["boys", "girls"])
def test_height_and_weight_medians_still_increase_with_age(sex):
    for measure in ("height", "weight"):
        medians = [lms.iap_lms_value_at_z(measure, sex, a, 0.0) for a in _AGES]
        assert all(np.diff(medians) >= -1e-9), f"{sex}/{measure} median decreases"


@requires_lms
def test_who_iap_seam_still_validates():
    """The legacy guard band exists because blend._quintic_bridge probes
    derivatives right at 5.0y. Before the old machinery is deleted, the full
    validation suite must still be green with the LMS path live."""
    from backend.growth import validation

    report = validation.run_full_validation()
    assert report.all_pass, f"seam/ordering regressions: {report.failures[:5]}"


# ── dry run: prove the gate has teeth, without inventing a reference ────────

def _synthetic_lms_file(path) -> int:
    """Write an LMS file from the engine's OWN fitted L,M,S.

    This is a test fixture, not a reference. Those fitted values are a
    2-parameter approximation to 6 published points per age, so they should
    FAIL the reproduction gate -- which is precisely what makes them a good
    probe of whether the gate works.
    """
    rows = ["sex,measure,age_years,L,M,S"]
    for sex, csv_sex in (("boys", "boy"), ("girls", "girl")):
        for measure in ("height", "weight", "bmi"):
            for age in lms.REQUIRED_AGES:
                l, m, s = legacy._SERIES[(sex, measure)].lms_at(age)
                rows.append(f"{csv_sex},{measure},{age},{l:.6f},{m:.6f},{s:.6f}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return len(rows) - 1


def test_gate_runs_end_to_end_and_rejects_an_approximate_table(tmp_path, monkeypatch):
    """The whole machinery, exercised: parse -> interpolate -> reproduce -> verdict.

    Fed the current engine's own fitted parameters, the gate must REJECT them.
    That is the correct answer: a fit that lands within ~0.4-0.65 units of the
    published table is not the published table, and accepting it would defeat
    the point of asking the authors for the real values.

    Note this refit is fitted to ALL seven columns, so it is a compromise across
    them and misses p3/p97 by ~0.2 — which the gate still judges. A refit of
    only p3/p50/p97 would pass, and that limitation is pinned separately in
    test_iap_lms_ingestion.py.
    """
    synthetic = tmp_path / "iap_2015_lms.csv"
    n = _synthetic_lms_file(synthetic)
    assert n == 162, f"expected 162 rows (27 ages x 3 measures x 2 sexes), wrote {n}"

    monkeypatch.setattr(lms, "LMS_PATH", synthetic)
    lms.reset_cache()
    try:
        assert lms._load() is not None, "a complete, well-formed file failed to parse"

        report = lms._reproduction()
        assert report["checked"] == _expected_judged_cells()
        assert set(report["worst"]) == {"height", "weight", "bmi"}

        assert report["ok"] is False, (
            "the gate ACCEPTED the engine's own approximate fit. It is supposed to "
            "distinguish real published parameters from a refit; if it cannot, a "
            "bad transcription would activate silently."
        )
        assert lms.lms_available() is False
        assert "does not reproduce" in lms.lms_status()["reason"]
    finally:
        lms.reset_cache()


def test_interpolation_is_per_parameter_not_per_value(tmp_path, monkeypatch):
    """Between published knots, L, M and S are each interpolated and THEN Cole is
    applied. Interpolating the resulting values instead is subtly wrong for a
    skewed distribution -- the curve between two knots is not the Cole transform
    of interpolated parameters unless you do it in that order."""
    synthetic = tmp_path / "iap_2015_lms.csv"
    _synthetic_lms_file(synthetic)
    monkeypatch.setattr(lms, "LMS_PATH", synthetic)
    lms.reset_cache()
    try:
        mid = 10.25                                   # between 10.0 and 10.5 knots
        l, m, s = lms.lms_at("weight", "boys", mid)
        direct = lms.iap_lms_value_at_z("weight", "boys", mid, 1.88079)
        assert direct == pytest.approx(lms_value_at_z(l, m, s, 1.88079), abs=1e-9)

        lo = lms.iap_lms_value_at_z("weight", "boys", 10.0, 1.88079)
        hi = lms.iap_lms_value_at_z("weight", "boys", 10.5, 1.88079)
        assert direct != pytest.approx((lo + hi) / 2, abs=1e-9), (
            "the midpoint equals the average of the endpoint VALUES, which means "
            "values are being interpolated rather than parameters"
        )
    finally:
        lms.reset_cache()
