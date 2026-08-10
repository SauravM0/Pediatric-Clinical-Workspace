"""M1.4: replacing the AGPL rcpchgrowth dependency with WHO's own LMS tables.

The tables are not committed — see data/WHO-LMS-REQUEST.md. Tests that need them
bootstrap into a temp directory from the installed package, which is exactly the
path the CLI offers and lets the whole gate run today.

What is being protected here is not "the code works" but "no number a clinician
has already seen changes". That is why the gate is equivalence against the
incumbent rather than reproduction of a published table: while rcpchgrowth is
still installed it is a perfect oracle for its own behaviour, and it stops being
available the moment the dependency is dropped.
"""
from __future__ import annotations

import pytest

from backend.growth import who_lms_reference as who_lms
from backend.growth import who_reference

rcpch = pytest.importorskip("rcpchgrowth")


@pytest.fixture
def installed(tmp_path, monkeypatch):
    """Bootstrap the WHO tables into tmp_path and point the module at them."""
    from backend.growth import ingest_who_lms as ingest

    monkeypatch.setattr(who_lms, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(ingest, "PROVENANCE_PATH", tmp_path / "PROVENANCE.json")
    who_lms.reset_cache()
    result = ingest.from_installed_rcpchgrowth()
    who_lms.reset_cache()
    yield result
    who_lms.reset_cache()


# ── inert without data ──────────────────────────────────────────────────────

def test_path_is_inactive_without_tables(tmp_path, monkeypatch):
    monkeypatch.setattr(who_lms, "_DATA_DIR", tmp_path)
    who_lms.reset_cache()
    try:
        assert who_lms.lms_available() is False
        assert who_lms.value_at_z("height", "boys", 5.0, 0.0) is None
        status = who_lms.lms_status()
        assert status["active"] is False
        assert len(status["reason"]) > 40, "an inactive path must say why"
    finally:
        who_lms.reset_cache()


def test_the_repository_ships_no_who_tables():
    """They are WHO's to publish and the operator's to install. Committing a set
    lifted from an AGPL package is the specific thing M1.4 exists to avoid."""
    import subprocess

    tracked = subprocess.run(["git", "ls-files", "backend/growth/data/who_lms/"],
                             capture_output=True, text=True).stdout.split()
    assert not [t for t in tracked if t.endswith(".csv")], (
        f"WHO LMS tables are committed: {tracked}"
    )


def test_env_kill_switch_is_a_disable_not_an_enable(monkeypatch):
    """There is deliberately no variable that forces our tables ON: activation
    is earned by matching the incumbent, so a flag could not make a bad table
    trustworthy."""
    monkeypatch.setenv("PCW_DISABLE_WHO_LMS", "1")
    assert who_lms.disabled_by_env() is True
    assert who_lms.lms_available() is False


def test_a_partial_table_set_is_refused(tmp_path, monkeypatch):
    """Half our tables and half rcpchgrowth's would be two references at once,
    with nothing to detect a disagreement."""
    monkeypatch.setattr(who_lms, "_DATA_DIR", tmp_path)
    (tmp_path / "who_boys_height.csv").write_text(
        "age_years,L,M,S\n" + "".join(f"{i/12},1,50,0.04\n" for i in range(30)),
        encoding="utf-8")
    who_lms.reset_cache()
    try:
        with pytest.raises(who_lms.WhoLmsDataError, match="incomplete"):
            who_lms._load()
    finally:
        who_lms.reset_cache()


def test_a_suspiciously_sparse_table_is_refused(tmp_path, monkeypatch):
    """WHO publishes daily or monthly; a handful of rows would be interpolated
    across the steepest part of infant growth."""
    monkeypatch.setattr(who_lms, "_DATA_DIR", tmp_path)
    for sex in who_lms.SEXES:
        for measure in who_lms.MEASURES:
            who_lms.table_path(measure, sex).write_text(
                "age_years,L,M,S\n0,1,50,0.04\n1,1,75,0.04\n", encoding="utf-8")
    who_lms.reset_cache()
    try:
        with pytest.raises(who_lms.WhoLmsDataError, match="rows"):
            who_lms._load()
    finally:
        who_lms.reset_cache()


# ── the gate, run for real ──────────────────────────────────────────────────

def test_bootstrapped_tables_reproduce_the_incumbent(installed):
    """THE gate. Every percentile the charts draw, every measure and sex, across
    a dense age grid."""
    report = who_lms._equivalence()
    assert report["checked"] > 5000, f"only {report['checked']} points compared"
    assert report["ok"] is True, report
    for measure, worst in report["worst"].items():
        assert worst <= who_lms.EQUIVALENCE_TOL[measure], (
            f"{measure}: worst deviation {worst} at {report['worst_at'][measure]}"
        )


def test_the_gate_excludes_only_ages_the_app_cannot_read(installed):
    """Ages strictly inside a seam window are skipped because
    who_value_at_z evaluates a bridge there and never calls the raw lookup --
    but the window ENDPOINTS, which the bridge does read, must be compared."""
    grid = who_lms._grid()
    eps = who_reference._SEAM_DERIV_EPS
    for seam in who_reference._SEAMS:
        for edge in (seam.lo, seam.hi):
            assert any(abs(a - edge) < 1e-9 for a in grid), f"{edge} not compared"
            assert any(abs(a - (edge - eps)) < 1e-9 for a in grid)
            assert any(abs(a - (edge + eps)) < 1e-9 for a in grid)
        midpoint = (seam.lo + seam.hi) / 2
        assert not any(abs(a - midpoint) < 1e-9 for a in grid), (
            "a mid-window age is being compared, but the app never reads one"
        )


def test_a_corrupted_table_fails_the_gate(installed, tmp_path):
    """Negative control on the gate itself: shift one measure and it must fail."""
    path = who_lms.table_path("height", "boys")
    rows = path.read_text(encoding="utf-8").splitlines()
    shifted = [rows[0]]
    for line in rows[1:]:
        age, l, m, s = line.split(",")
        shifted.append(f"{age},{l},{float(m) + 0.5},{s}")
    path.write_text("\n".join(shifted) + "\n", encoding="utf-8")
    who_lms.reset_cache()

    report = who_lms._equivalence()
    assert report["ok"] is False
    assert report["worst"]["height"] > who_lms.EQUIVALENCE_TOL["height"]
    assert who_lms.lms_available() is False


def test_the_overlap_is_resolved_by_range_not_deduplication(installed):
    """WHO's two studies overlap and carry different L/S there. Interleaving
    them put an over-five row between two under-five neighbours and moved the
    +-3 SD lines by up to 0.55 cm at 5.0y -- the median was unaffected, which is
    why only the tails showed it."""
    import csv

    with open(who_lms.table_path("height", "girls"), newline="", encoding="utf-8") as f:
        ages = [float(r["age_years"]) for r in csv.DictReader(f)]
    assert ages == sorted(ages)
    assert len(ages) == len(set(ages)), "duplicate ages survived the merge"
    # No over-five row may sit below the under-five table's last age.
    around = [a for a in ages if 4.99 < a < 5.09]
    assert around == sorted(around) and len(around) > 5


# ── the strangler seam ──────────────────────────────────────────────────────

def test_who_reference_uses_our_tables_once_they_are_live(installed):
    """The seam. Installing the tables must actually change where the number
    comes from -- otherwise the dependency could never be dropped."""
    assert who_lms.lms_available() is True
    for measure in ("height", "weight", "bmi"):
        for sex in ("boys", "girls"):
            for age in (0.5, 3.0, 7.0, 9.5):
                direct = who_lms.value_at_z(measure, sex, age, 0.0)
                through = who_reference._raw_who_value_at_z(measure, sex, age, 0.0)
                assert through == pytest.approx(direct), (
                    f"{sex}/{measure} @ {age}: who_reference did not delegate"
                )


def test_value_and_z_flip_together(installed):
    """Scoring on one model while drawing from another is the display-vs-scoring
    mismatch this project already fixed once for IAP (GC-3/GC-4)."""
    for measure in ("height", "weight", "bmi"):
        for age in (1.0, 4.0, 8.0):
            for target in (-2.0, 0.0, 2.0):
                value = who_reference.who_value_at_z(measure, "girls", age, target)
                if value is None:
                    continue
                got = who_reference.who_z_for_value(measure, "girls", age, value)
                assert got == pytest.approx(target, abs=1e-4)


def test_public_output_is_unchanged_by_the_swap(installed):
    """What actually matters: no number a clinician has already seen moves.

    Compares the PUBLIC seam-smoothed curve with our tables live against the
    same curve with them disabled, which is the incumbent.
    """
    import os

    ages = [round(0.25 * i, 2) for i in range(0, 77)]
    with_ours = {}
    for measure in ("height", "weight", "bmi"):
        for sex in ("boys", "girls"):
            for age in ages:
                for z in (-2.0, 0.0, 2.0):
                    with_ours[(measure, sex, age, z)] = who_reference.who_value_at_z(
                        measure, sex, age, z)

    os.environ["PCW_DISABLE_WHO_LMS"] = "1"
    who_lms.reset_cache()
    try:
        worst, worst_at = 0.0, None
        for key, ours in with_ours.items():
            incumbent = who_reference.who_value_at_z(*key)
            if ours is None or incumbent is None:
                assert ours is incumbent or (ours is None) == (incumbent is None), (
                    f"coverage differs at {key}"
                )
                continue
            d = abs(ours - incumbent)
            if d > worst:
                worst, worst_at = d, key
        assert worst <= 0.02, f"public output moved by {worst:.4f} at {worst_at}"
    finally:
        os.environ.pop("PCW_DISABLE_WHO_LMS", None)
        who_lms.reset_cache()


def test_weight_still_stops_at_ten_years(installed):
    """WHO's own limit, not a gap in our tables."""
    assert who_lms.value_at_z("weight", "boys", 9.5, 0.0) is not None
    assert who_lms.value_at_z("weight", "boys", 10.5, 0.0) is None
    assert who_lms.WEIGHT_MAX_AGE == 10.0


def test_provenance_records_the_bootstrap_source(installed, tmp_path):
    """A bootstrap must never be mistakable for WHO provenance."""
    from backend.growth import ingest_who_lms as ingest

    ingest.write_provenance(installed, who_lms.lms_status())
    import json

    blob = json.loads((tmp_path / "PROVENANCE.json").read_text(encoding="utf-8"))
    assert blob["source"].startswith("rcpchgrowth-")
    assert "AGPL" in (blob.get("licence_caveat") or "")
