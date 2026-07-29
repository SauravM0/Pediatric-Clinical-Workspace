"""The measure registry is the single source of truth (M0.3).

Before this, the measure set was declared seven times across six files. Adding
head circumference (B11) or sitting height (B14) meant a correct edit in every
one, with nothing failing if one was missed -- a half-registered measure would
render a chart but never be validated, or be scored against the wrong WHO seam.

These tests make that impossible two ways: consumers must *derive* from the
registry (no module may re-declare a literal measure set), and the registry's
rcpchgrowth binding is checked against the real constants so the string-typed
coupling in measures.py cannot rot.
"""
import re
from pathlib import Path

import pytest
import rcpchgrowth as rg

from backend.growth import blend, measures, qa_report, validation, who_reference

_GROWTH_DIR = Path(who_reference.__file__).resolve().parent
_API_GROWTH = _GROWTH_DIR.parents[0] / "api_growth.py"


# ── registry integrity ──────────────────────────────────────────────────────

def test_registry_is_self_consistent():
    for key, m in measures.MEASURES.items():
        assert m.key == key, f"registry key {key!r} disagrees with Measure.key {m.key!r}"
        assert m.unit, f"{key}: missing unit"
        assert m.label, f"{key}: missing label"
        assert m.published_centiles == tuple(sorted(m.published_centiles)), (
            f"{key}: published_centiles must be ascending"
        )
        assert m.has_iap_table == (m.file_part is not None)
        assert m.who_backed == (m.who_measurement_method is not None)


def test_registry_matches_rcpchgrowth_constants():
    """measures.py stores the rcpchgrowth measurement_method as a plain string to
    stay dependency-free (and to keep the planned M1.4 removal local). That is
    only safe if the strings are checked against the real constants."""
    expected = {"height": rg.HEIGHT, "weight": rg.WEIGHT, "bmi": rg.BMI}
    for key, const in expected.items():
        assert measures.MEASURES[key].who_measurement_method == const, (
            f"{key}: registry says {measures.MEASURES[key].who_measurement_method!r}, "
            f"rcpchgrowth says {const!r}"
        )


def test_every_who_backed_measure_has_an_adapter_entry():
    for key in measures.WHO_BACKED_KEYS:
        assert key in who_reference._MEASURE_MAP, (
            f"{key} is WHO-backed in the registry but absent from "
            "who_reference._MEASURE_MAP -- WHO lookups would fail for it"
        )


def test_get_rejects_unknown_measure_with_a_useful_message():
    with pytest.raises(KeyError, match="unknown growth measure"):
        measures.get("sitting_height")   # registered later (B14), not yet
    assert measures.is_valid("height") and not measures.is_valid("sitting_height")


# ── consumers derive, never re-declare ──────────────────────────────────────

def test_consumers_are_wired_to_the_registry():
    assert validation.MEASURES == measures.MEASURE_KEYS
    assert validation.MONOTONIC_MEASURES == measures.MONOTONIC_MEASURE_KEYS
    assert blend._REQUIRE_MONOTONIC == measures.REQUIRE_MONOTONIC
    assert qa_report._MEASURE_FILE_PART == measures.FILE_PART

    from backend import api_growth

    assert api_growth._VALID_MEASURES == measures.MEASURE_KEYS
    assert api_growth._UNITS == measures.UNITS


# Per-measure POLICY dicts are a legitimate exception to the structural guard
# below: a validation tolerance is a property of the validation, not of the
# measure, so it correctly lives in validation.py. They are still per-measure
# and still incomplete-able, so test_policy_dicts_cover_every_measure enforces
# coverage instead. Anything not listed here must derive from the registry.
_POLICY_DICTS = ("SLOPE_ATOL", "CURVATURE_ATOL", "TRANSITION_STEP_ATOL")


def test_no_module_redeclares_the_measure_set():
    """Structural guard: a literal ("height", "weight", "bmi") tuple/dict anywhere
    outside measures.py is exactly the drift this registry exists to prevent."""
    literal = re.compile(r"""["']height["']\s*[,:].{0,40}?["']weight["']\s*[,:]""", re.S)
    offenders = []
    for path in list(_GROWTH_DIR.rglob("*.py")) + [_API_GROWTH]:
        if path.name == "measures.py":
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if any(stripped.startswith(name) for name in _POLICY_DICTS):
                continue
            if literal.search(line):
                offenders.append(f"{path.name}:{lineno}: {line.strip()[:70]}")

    assert not offenders, (
        "Measure set re-declared outside measures.py:\n  " + "\n  ".join(offenders) +
        "\nImport from backend.growth.measures instead."
    )


def test_policy_dicts_cover_every_measure():
    """The per-measure validation tolerances are exempt from the structural guard,
    so they get an explicit completeness check instead.

    These are looked up unguarded (`SLOPE_ATOL[measure]`), so a measure added to
    the registry without a tolerance raises KeyError deep inside
    run_full_validation() rather than failing here with an actionable message.
    """
    for name in _POLICY_DICTS:
        policy = getattr(validation, name)
        missing = [k for k in measures.MEASURE_KEYS if k not in policy]
        assert not missing, (
            f"validation.{name} has no entry for {missing} -- "
            "run_full_validation() will raise KeyError on those measures. "
            "Add a tolerance when registering a new measure."
        )
        unknown = [k for k in policy if not measures.is_valid(k)]
        assert not unknown, f"validation.{name} has entries for unregistered measures: {unknown}"


# ── seam sets: derived, but seam monotonicity is NOT ────────────────────────

def test_seam_measure_sets_come_from_the_registry():
    assert who_reference._SEAM_2Y.measures == measures.SEAM_2Y_KEYS
    assert who_reference._SEAM_5Y.measures == measures.SEAM_5Y_KEYS
    # Weight does not depend on the recumbent-length/standing-height convention.
    assert "weight" not in measures.SEAM_2Y_KEYS
    assert {"height", "bmi"} <= measures.SEAM_2Y_KEYS


def test_seam_monotonicity_is_not_derived_from_measure_monotonicity():
    """Regression guard for a subtle refactor hazard.

    _Seam.monotonic selects which BRIDGE to use across that seam; Measure.monotonic
    says whether the measure may ever decrease with age. They are different
    properties and coincidentally disagree: the 5y handoff uses the bounded
    (signed) bridge for EVERY measure, height included, even though height is a
    monotonic measure. Deriving one from the other would silently switch height's
    5y seam to the monotone bridge and change rendered values.
    """
    assert who_reference._SEAM_5Y.monotonic is False
    assert measures.MEASURES["height"].monotonic is True
    assert who_reference._SEAM_2Y.monotonic is True
    assert measures.MEASURES["bmi"].monotonic is False
