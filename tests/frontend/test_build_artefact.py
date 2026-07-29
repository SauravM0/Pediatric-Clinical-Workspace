"""The committed bundle must match the committed source (M6).

frontend/app.js is a build output that is deliberately COMMITTED, so a fresh
clone runs offline with one command and no npm install -- a real property for a
clinical tool used in low-connectivity clinics.

The cost of committing a generated file is drift: the browser executes app.js,
so if someone edits frontend/src/ and forgets `npm run build`, the reviewed
source is not what runs in front of a patient. Nothing else in the suite would
notice -- the other frontend guards read src/ (by design), and the Python tests
never touch either. This is the only check standing between a stale artefact and
production, which is why it fails hard rather than warning.

Skips (rather than fails) when node/esbuild are unavailable, so the Python suite
still runs on a machine without the JS toolchain. The artefact's existence and
provenance are checked unconditionally.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from _frontend_source import BUILT_BUNDLE, INDEX_HTML, SRC_DIR, frontend_source

_ROOT = Path(__file__).resolve().parents[2]


def _node_available() -> bool:
    return shutil.which("node") is not None and (_ROOT / "node_modules" / "esbuild").exists()


# ── unconditional: the artefact exists and is wired up ──────────────────────

def test_bundle_is_committed():
    assert BUILT_BUNDLE.exists(), (
        f"{BUILT_BUNDLE} is missing. It is committed on purpose so a fresh clone "
        "runs offline without npm install. Run: npm run build"
    )
    assert BUILT_BUNDLE.stat().st_size > 50_000, "bundle is suspiciously small"


def test_bundle_is_marked_generated():
    head = BUILT_BUNDLE.read_text(encoding="utf-8")[:400]
    assert "GENERATED FILE" in head and "build.mjs" in head, (
        "the bundle lost its generated-file banner -- someone editing it directly "
        "would have no warning that their change is about to be overwritten"
    )


def test_index_html_loads_the_bundle_and_not_babel():
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'src="static/app.js"' in html, "index.html no longer loads the built bundle"

    # Check for a real Babel *reference*, not the word: the shell carries a
    # comment explaining that babel.min.js was removed, and a bare substring
    # search on "babel" flags that comment. Strip comments first, then look for
    # the two ways Babel could actually come back.
    without_comments = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    assert "babel" not in without_comments.lower(), (
        "index.html loads Babel again -- M6 removed in-browser transpilation "
        "(a 3.1 MB download that re-compiled the whole app on every page load)"
    )
    assert 'type="text/babel"' not in without_comments


def test_no_application_logic_left_in_the_shell():
    """index.html is a shell; logic lives in src/ so it can be built and tested."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert "ReactDOM.createRoot" not in html
    assert "COMBINED_CHART_YMAX" not in html


def test_react_is_still_vendored_and_external():
    """The bundle must not inline React: vendor files stay the single copy, and
    the app stays offline without npm."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert "vendor/react.production.min.js" in html
    assert "vendor/react-dom.production.min.js" in html
    assert not (_ROOT / "frontend" / "vendor" / "babel.min.js").exists(), (
        "babel.min.js is back in vendor/ -- 3.1 MB that M6 removed"
    )


def test_source_is_jsx_modules():
    files = list(SRC_DIR.rglob("*.jsx"))
    assert files, f"no .jsx modules under {SRC_DIR}"
    assert len(frontend_source()) > 200_000


# ── the freshness check itself ──────────────────────────────────────────────

@pytest.mark.skipif(not _node_available(), reason="node/esbuild not installed")
def test_bundle_matches_source():
    """Rebuild in memory and compare byte-for-byte with the committed artefact."""
    result = subprocess.run(
        ["node", "build.mjs", "--check"],
        cwd=_ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        "frontend/app.js is stale -- the committed source is NOT what the browser "
        f"executes.\n{result.stdout}\n{result.stderr}\nRun: npm run build"
    )
