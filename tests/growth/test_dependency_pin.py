"""Reproducibility lock for the clinical reference dependency (audit GC-7).

``rcpchgrowth`` supplies the WHO reference LMS values that the growth charts
render and score against. If it is allowed to float (``>=``) a routine upgrade
can silently change chart output; if the installed environment drifts from the
pin, a report generated here is no longer reproducible elsewhere. Both are
clinical-accuracy risks, so both are asserted here.

This test is intentionally dependency-light (regex + importlib.metadata) so it
runs even where the full app stack is unavailable.
"""
from __future__ import annotations

import re
from importlib.metadata import version
from pathlib import Path

_REQUIREMENTS = Path(__file__).resolve().parents[2] / "requirements.txt"
# The single validated version. Bumping this is a deliberate act that must be
# accompanied by re-running the growth validation suite (see the comment block
# in requirements.txt).
_EXPECTED = "4.5.0"


def _pinned_spec() -> str:
    """The rcpchgrowth requirement line, ignoring comments/blank lines."""
    for raw in _REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("#") or not line:
            continue
        if re.match(r"^rcpchgrowth\b", line):
            return line
    raise AssertionError("rcpchgrowth is not listed in requirements.txt")


def test_rcpchgrowth_is_exactly_pinned():
    spec = _pinned_spec()
    assert spec == f"rcpchgrowth=={_EXPECTED}", (
        "rcpchgrowth must be exactly pinned (== the validated version), not a "
        f"floating floor, for reproducible WHO reference output. Found: {spec!r}"
    )


def test_installed_version_matches_pin():
    installed = version("rcpchgrowth")
    assert installed == _EXPECTED, (
        f"Installed rcpchgrowth {installed!r} != validated pin {_EXPECTED!r}. "
        "The environment has drifted from the locked clinical reference; "
        "reinstall from requirements.txt or re-validate before bumping the pin."
    )
