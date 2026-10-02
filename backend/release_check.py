"""Release-readiness check (step 8).

    python -m backend.release_check            # fast checks
    python -m backend.release_check --tests    # also run the full test suite
    python -m backend.release_check --json     # machine-readable

Answers one question: may THIS copy of the workspace be installed for clinical
use? Every check reports PASS, WARN or FAIL, and the exit code is 1 if anything
FAILs. It reads state only; it never changes a file, the database or git.

FAIL = a release blocker (wrong numbers possible, patient data exposed, or a
       clinical claim nobody has signed off).
WARN = acceptable only as a recorded, deliberate decision (e.g. auth off by the
       owner's choice, a reference that is refused rather than approximated).

A PASS here is necessary, not sufficient: validation/RELEASE-CHECKLIST.md lists
the human steps (clinician sign-off, site acceptance, regulatory position) that
no script can perform.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


def _check(name: str, fn: Callable[[], tuple[str, str]]) -> dict:
    try:
        level, detail = fn()
    except Exception as exc:  # noqa: BLE001 -- a check that crashes is a failed check
        level, detail = FAIL, f"check crashed: {type(exc).__name__}: {exc}"
    return {"check": name, "level": level, "detail": detail}


# ── individual checks ───────────────────────────────────────────────────────

def frontend_bundle() -> tuple[str, str]:
    node = shutil.which("node")
    if not node:
        return WARN, "node not found: cannot verify app.js / app.css match the source"
    r = subprocess.run([node, "build.mjs", "--check"], cwd=ROOT, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip().splitlines()
    return (PASS if r.returncode == 0 else FAIL), (out[-1] if out else f"exit {r.returncode}")


def growth_validation() -> tuple[str, str]:
    from backend.growth.validation import run_full_validation
    rep = run_full_validation()
    if rep.all_pass:
        return PASS, "growth curve validation: all checks pass"
    return FAIL, f"growth validation failures: {rep.failures[:5]}"


def who_tables() -> tuple[str, str]:
    from backend.growth import who_lms_reference as w
    s = w.lms_status()
    mode = (s.get("equivalence") or {}).get("mode")
    if s["active"]:
        return PASS, f"WHO LMS tables active ({mode} equivalence)"
    return WARN, f"WHO LMS tables inactive, rcpchgrowth fallback in use: {s['reason']}"


def reference_data() -> tuple[str, str]:
    from backend.api_reference_data import reference_data_status
    s = reference_data_status()
    missing = [i["title"] for i in s["items"] if not i["active"]]
    detail = f"{s['active_count']}/{s['total']} active"
    if missing:
        return WARN, detail + "; refused (not approximated) until supplied: " + "; ".join(missing)
    return PASS, detail


def vignettes() -> tuple[str, str]:
    from backend import clinical_vignettes as cv
    rs = cv.run()
    bad = [r["id"] for r in rs if not r["passed"]]
    if bad:
        return FAIL, f"vignettes disagree with their hand derivation: {bad}"
    return PASS, f"{len(rs)}/{len(rs)} vignettes match their hand derivation"


def vignette_signoff() -> tuple[str, str]:
    from backend import clinical_vignettes as cv
    rs = cv.run()
    disagree = [r["id"] for r in rs if r["clinician_disagrees"]]
    unsigned = [r["id"] for r in rs if not r["signed_off"]]
    if disagree:
        return FAIL, f"a clinician DISAGREES with: {disagree}"
    if unsigned:
        return FAIL, (f"{len(unsigned)}/{len(rs)} vignettes have no clinician sign-off "
                      "(validation/clinical_vignettes.json -> signoff)")
    return PASS, f"all {len(rs)} vignettes signed off"


def authentication() -> tuple[str, str]:
    from backend.security.deps import auth_disabled
    if not auth_disabled():
        return PASS, "authentication enforced"
    return WARN, ("authentication OFF (owner decision): the network guard limits the app to "
                  "this computer, and approvals are attributed to 'dev-no-auth'")


def encryption() -> tuple[str, str]:
    from backend.security.crypto import encryption_available, key_location
    if not encryption_available():
        return FAIL, ("identifiers are NOT encrypted at rest: set PCW_ENCRYPTION_KEY_FILE "
                      "to a key stored outside the app folder before patient data is entered")
    loc = key_location()
    if loc.get("inside_app_folder"):
        return FAIL, "the encryption key file is inside the app folder: a copy of the folder carries the key"
    return PASS, f"identifiers encrypted at rest (key from {loc['source']})"


def runtime_licences() -> tuple[str, str]:
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    lines = [ln.split("#", 1)[0].strip() for ln in req.splitlines()]
    if any(ln.startswith("rcpchgrowth") for ln in lines):
        return FAIL, "rcpchgrowth (AGPL-3.0) is a runtime requirement again"
    return PASS, "no AGPL package in the runtime requirements"


def ai_model() -> tuple[str, str]:
    from backend.ai import boneage
    if not boneage.model_available():
        return WARN, "bone-age AI model not installed: the AI estimate is unavailable (TW3 unaffected)"
    meta = boneage.model_metadata() or {}
    if not meta.get("conformal"):
        return FAIL, "AI model has no conformal calibration: its interval cannot be shown honestly"
    return PASS, (f"AI model {meta.get('model_version')} (screening only; never enterable as the "
                  f"TW3 bone age), validation MAE {meta.get('val_mae_months')} months")


def source_control() -> tuple[str, str]:
    git = shutil.which("git")
    if not git:
        return WARN, "git not found: cannot tell which revision this is"
    dirty = subprocess.run([git, "status", "--porcelain"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    tag = subprocess.run([git, "describe", "--tags", "--exact-match"], cwd=ROOT,
                         capture_output=True, text=True)
    notes = []
    if dirty:
        notes.append(f"{len(dirty.splitlines())} uncommitted change(s)")
    if tag.returncode != 0:
        notes.append("HEAD is not a tagged release")
    if notes:
        return WARN, ("; ".join(notes) + ": a clinical release should be installed from a "
                      "committed, tagged revision so it can be identified and reproduced")
    return PASS, f"clean tagged revision {tag.stdout.strip()}"


def test_suite() -> tuple[str, str]:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                       cwd=ROOT, capture_output=True, text=True)
    tail = [ln for ln in r.stdout.strip().splitlines() if ln.strip()][-1:] or ["(no output)"]
    return (PASS if r.returncode == 0 else FAIL), tail[0]


CHECKS: list[tuple[str, Callable[[], tuple[str, str]]]] = [
    ("Frontend bundle", frontend_bundle),
    ("Growth validation", growth_validation),
    ("WHO tables", who_tables),
    ("Reference data", reference_data),
    ("Clinical vignettes", vignettes),
    ("Clinician sign-off", vignette_signoff),
    ("Authentication", authentication),
    ("Encryption at rest", encryption),
    ("Runtime licences", runtime_licences),
    ("Bone-age AI", ai_model),
    ("Source control", source_control),
]


def run(with_tests: bool = False) -> dict:
    os.environ.setdefault("PCW_SKIP_CACHE_WARMUP", "1")
    checks = list(CHECKS) + ([("Test suite", test_suite)] if with_tests else [])
    results = [_check(n, f) for n, f in checks]
    fails = sum(r["level"] == FAIL for r in results)
    return {"ready": fails == 0, "fail": fails,
            "warn": sum(r["level"] == WARN for r in results), "results": results}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tests", action="store_true", help="also run the full pytest suite")
    ap.add_argument("--json", action="store_true", help="print JSON")
    args = ap.parse_args(argv)
    # Details quote clinical text (arrows, en dashes); a Windows console in
    # cp1252 would crash printing them, so never let output encoding fail the check.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass
    report = run(with_tests=args.tests)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for r in report["results"]:
            print(f"[{r['level']}] {r['check']:<20} {r['detail']}")
        print()
        print("READY FOR CLINICAL RELEASE" if report["ready"] else
              f"NOT READY: {report['fail']} blocker(s), {report['warn']} warning(s). "
              "See validation/RELEASE-CHECKLIST.md.")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
