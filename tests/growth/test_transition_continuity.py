"""Gate the WHO<->IAP composite handoff discontinuity (audit GC-2/GC-3).

blend._quintic_bridge can absorb a large WHO/IAP disagreement as a single flat
value step ENTERING the 3-5y window (blend.py). On the current data that step is
exactly 0, but the old QA suite had no check for it -- so such a step could ship
silently, marked 'non-gating'. These tests:

  1. confirm the current composite has no handoff jump for any centile, and
  2. prove the new gate actually FAILS when a step is present (so it can't be a
     no-op), and
  3. guard the honest 'product-derived composite' label on the chart.
"""
import os
import tempfile

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "growth_test.db"))

import pytest
from fastapi.testclient import TestClient

from backend.growth import blend, validation
from backend.server import app


def test_current_composite_has_no_visible_handoff_step():
    res = validation.check_transition_value_continuity()
    assert res, "check produced no results"
    for key, r in res.items():
        assert r["pass"], f"{key}: unexpected handoff step {r}"
        if r["step"] is not None:
            assert r["step"] <= 1e-6, f"{key}: step {r['step']} should be ~0 on current data"


def test_full_validation_includes_and_passes_transition_check():
    report = validation.run_full_validation()
    assert "transition_value_continuity" in report.details
    assert report.all_pass, f"failures: {report.failures[:5]}"


def test_gate_fails_when_a_real_step_is_injected(monkeypatch):
    """Prove the gate is not a no-op: if the bridge returns a flat step whose
    start value is far from pure WHO (the exact secant<=0 absorption the audit
    flagged), the check must fail and run_full_validation must go red."""
    real_bridge = blend._quintic_bridge

    def fake_bridge(measure, sex, z):
        b = real_bridge(measure, sex, z)
        if b is None:
            return None
        # Force a 3-unit jump at BLEND_LO (bridge starts 3 units above WHO).
        who_lo = blend.who.who_value_at_z(measure, sex, blend.BLEND_LO, z)
        y1 = b[3]
        return (who_lo + 3.0, 0.0, 0.0, y1, 0.0, 0.0)

    monkeypatch.setattr(blend, "_quintic_bridge", fake_bridge)

    res = validation.check_transition_value_continuity()
    failed = [k for k, r in res.items() if not r["pass"]]
    assert failed, "the gate did not catch an injected 3-unit handoff step"
    # and it must propagate to the top-level report
    report = validation.run_full_validation()
    assert not report.all_pass
    assert any("transition_value_continuity" in f for f in report.failures)


def test_chart_reference_label_is_honest_about_the_composite():
    client = TestClient(app)
    r = client.get("/api/growth/chart?measure=height&sex=boys&age_min=0&age_max=18")
    assert r.status_code == 200
    ref = r.json()["reference"].lower()
    assert "composite" in ref, f"reference should disclose the composite: {ref!r}"
    assert "4.0-5.0" not in ref, "stale transition window label (it is 3-5y)"
