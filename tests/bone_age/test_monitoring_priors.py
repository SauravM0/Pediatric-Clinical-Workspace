"""CPP monitoring priors (Plan 2 WI-6) — soft, external, non-gating."""
import pytest

from backend.monitoring import priors


def test_expected_bands_sum_to_about_one():
    for group in ("cpp", "control"):
        assert abs(sum(priors.expected_bands(group).values()) - 1.0) < 0.02


def test_matching_distribution_is_within_expected():
    # feed the CPP prior itself (as counts) -> tv ~ 0 -> within expected
    counts = {b: int(round(f * 70)) for b, f in priors.expected_bands("cpp").items()}
    r = priors.plausibility_check(counts, "cpp")
    assert r["within_expected"] is True
    assert r["tv_distance"] < 0.05
    assert r["gating"] is False               # NEVER a gate
    assert "EXTERNAL" in r["caveat"]


def test_divergent_distribution_flags_soft_warning():
    # everything piled in the youngest band -> far from the CPP prior
    weird = {"<6": 70, "6-7": 0, "7-8": 0, "8-9": 0, "9-10": 0,
             "10-11": 0, "11-12": 0, "12-13": 0, "13+": 0}
    r = priors.plausibility_check(weird, "cpp")
    assert r["within_expected"] is False
    assert r["tv_distance"] > 0.5
    assert r["gating"] is False


def test_empty_observed_is_handled():
    r = priors.plausibility_check({}, "cpp")
    assert r["within_expected"] is None and r["tv_distance"] is None


def test_unknown_group_raises():
    with pytest.raises(ValueError):
        priors.expected_bands("nonsense")


def test_cvmi_is_deprioritised_note_present():
    assert "de-prioritise" in priors.MATURITY_NOTES["cvmi"].lower()
