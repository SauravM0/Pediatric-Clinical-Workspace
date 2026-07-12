"""Reference-case gate for the provisional TW3-C score->age curve (S-BA-2).

The score->age curve is digitized (provisional, +/-~0.5y) -- the single biggest
deterministic bone-age accuracy risk. It must not present as definitive until it
is validated on real evidence: it should reproduce a clinic's own
historically-reported films within tolerance. These tests prove the gate:

  * with no reference films entered, the curve stays provisional (current state);
  * once >= min_cases films reproduce within tolerance, it clears;
  * a single missed film keeps it provisional;
  * fewer than min_cases (even if all pass) is not enough.

Nothing here enters real clinical data -- cases are synthesised from the shipped
curve so the mechanism can be verified with the tables the app already ships.
"""
import dataclasses

from backend.tw3 import RUS_BONES, compute, load_tables, validate_curve
from backend.api_bone_age import _provisional_curve, _curve_validation_summary


def _stages(grade: str) -> dict[str, str]:
    # ulna has no grade 8; every other grade is valid for all 13 RUS bones.
    return {b: grade for b in RUS_BONES}


def _case(tables, sex: str, grade: str, offset_years: float = 0.0, cid: str = "c") -> dict:
    """A reference case whose expected age = what the shipped curve computes for
    these stages, shifted by offset_years (0 => passes, large => fails)."""
    r = compute(_stages(grade), sex, tables)
    assert r.bone_age_years is not None, r.status
    return {"id": cid, "sex": sex, "stages": _stages(grade),
            "expected_bone_age_years": round(r.bone_age_years + offset_years, 3)}


def _with_cases(tables, cases, min_cases=3, tol=0.5):
    return dataclasses.replace(tables, reference_cases=tuple(cases),
                               curve_min_cases=min_cases, curve_tolerance_years=tol)


def test_no_reference_cases_stays_provisional():
    t = load_tables()
    cv = validate_curve(t)
    assert cv.n_cases == 0 and cv.validated is False
    assert _provisional_curve(t) is True  # declared provisional + unvalidated


def test_curve_clears_provisional_once_enough_cases_reproduce():
    t = load_tables()
    cases = [_case(t, "girls", "7", 0.0, "a"),
             _case(t, "boys", "5", 0.0, "b"),
             _case(t, "girls", "4", 0.0, "c")]
    tv = _with_cases(t, cases, min_cases=3, tol=0.5)
    cv = validate_curve(tv)
    assert cv.n_cases == 3 and cv.n_passing == 3 and cv.validated is True
    assert _provisional_curve(tv) is False  # now validated on local evidence


def test_one_missed_film_keeps_it_provisional():
    t = load_tables()
    cases = [_case(t, "girls", "7", 0.0, "a"),
             _case(t, "boys", "5", 0.0, "b"),
             _case(t, "girls", "4", 2.0, "c")]  # off by 2 yr -> fails tolerance
    tv = _with_cases(t, cases, min_cases=3, tol=0.5)
    cv = validate_curve(tv)
    assert cv.n_passing == 2 and cv.validated is False
    assert _provisional_curve(tv) is True
    bad = [c for c in cv.cases if c.id == "c"][0]
    assert bad.within_tolerance is False and abs(bad.error_years) >= 1.5


def test_fewer_than_min_cases_is_not_enough():
    t = load_tables()
    cases = [_case(t, "girls", "7", 0.0, "a"), _case(t, "boys", "5", 0.0, "b")]
    tv = _with_cases(t, cases, min_cases=3, tol=0.5)
    cv = validate_curve(tv)
    assert cv.n_passing == 2 and cv.n_cases == 2 and cv.validated is False


def test_summary_shape_is_patient_safe_and_complete():
    t = load_tables()
    cases = [_case(t, "girls", "7", 0.0, "a")]
    s = _curve_validation_summary(_with_cases(t, cases, min_cases=3))
    assert set(s) >= {"declared_provisional", "validated", "n_cases", "n_passing",
                      "min_cases", "tolerance_years", "cases"}
    assert s["cases"][0]["id"] == "a"
    # only case-level scoring fields, never raw patient identifiers
    assert set(s["cases"][0]) == {"id", "sex", "expected_years", "computed_years",
                                  "error_years", "within_tolerance", "status"}
