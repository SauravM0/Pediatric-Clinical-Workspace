"""Single release path guard (PLAN-0 A5).

Every model promotion (Plan 3 screening, Plan 4 localizer/stager) routes through
the Plan 5 release gate (release_gate.evaluate_candidate) via decide_release, and a
model reaches DEPLOYED only on a PASSING gate AND a named human sign-off. There is
no side path: if the gate is not consulted or does not pass, nothing deploys — a
signature cannot override a failed gate. This test locks that invariant so a future
change can't quietly add a bypass.
"""
import backend.ai.release as release
from backend.ai.release import DEPLOYED, REJECTED, decide_release
from backend.ai.validation.release_gate import Verdict

_ARGS = dict(model_kind="screening", version="v", dataset="d",
             targets=[60, 72, 84], candidate_preds=[61, 73, 85])


def test_decide_release_always_consults_the_gate(monkeypatch):
    calls = {"n": 0}
    real = release.evaluate_candidate

    def spy(*a, **k):
        calls["n"] += 1
        return real(*a, **k)

    monkeypatch.setattr(release, "evaluate_candidate", spy)
    decide_release(**_ARGS, signed_off_by="Dr X")
    assert calls["n"] == 1               # a release decision cannot skip the gate


def test_failing_gate_never_deploys_even_when_signed(monkeypatch):
    monkeypatch.setattr(release, "evaluate_candidate",
                        lambda *a, **k: Verdict(False, ("FAIL forced",), {}))
    d = decide_release(**_ARGS, signed_off_by="Dr X")
    assert d.status == REJECTED           # a signature cannot override a failed gate


def test_passing_gate_still_needs_signoff_to_deploy(monkeypatch):
    monkeypatch.setattr(release, "evaluate_candidate",
                        lambda *a, **k: Verdict(True, ("PASS forced",), {"passed": True}))
    assert decide_release(**_ARGS).status != DEPLOYED                       # no sign-off
    assert decide_release(**_ARGS, signed_off_by="Dr X").status == DEPLOYED  # both required
