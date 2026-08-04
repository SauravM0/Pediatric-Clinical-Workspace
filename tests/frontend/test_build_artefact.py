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


# ── module structure (M6 component extraction) ──────────────────────────────

_EXPECTED_MODULES = {
    "domain.js": ("TW3_CONFIG", "maturationCategory"),
    "qrisk3.js": ("QRISK3_FEMALE", "QRISK3_MALE", "function qrisk3"),
    "growthMath.js": ("zForValueFromCentileStats", "CENTILE_Z"),
    "charts.jsx": ("GrowthChart", "COMBINED_CHART_YMAX"),
    "ui.jsx": ("SectionHeader", "MetricRow"),
    "app.jsx": ("function App()", "ReactDOM.createRoot"),
}


def test_stateless_layers_are_separate_modules():
    """M6's second half: the parts with no dependency on App's state now live in
    their own files, so they can be read, diffed and reasoned about without
    scrolling through the application."""
    for name, needles in _EXPECTED_MODULES.items():
        path = SRC_DIR / name
        assert path.exists(), f"expected module {name} is missing"
        body = path.read_text(encoding="utf-8")
        for needle in needles:
            assert needle in body, f"{name} does not contain {needle!r}"


def test_extracted_code_is_no_longer_duplicated_in_app():
    """A split that copies rather than moves is worse than no split: two
    definitions drift, and the bundler would silently pick one."""
    app = (SRC_DIR / "app.jsx").read_text(encoding="utf-8")
    for moved in ("const QRISK3_FEMALE", "function GrowthChartCombined",
                  "function SectionHeader", "const CENTILE_Z",
                  "function maturationCategory"):
        assert moved not in app, (
            f"{moved!r} is still defined in app.jsx as well as its new module — "
            "the extraction copied instead of moving"
        )


def test_app_imports_what_it_uses():
    app = (SRC_DIR / "app.jsx").read_text(encoding="utf-8")
    for module in ("./domain.js", "./qrisk3.js", "./growthMath.js",
                   "./charts.jsx", "./ui.jsx"):
        assert f'from "{module}"' in app, f"app.jsx does not import {module}"


def test_qrisk3_module_is_self_contained():
    """tests/cvd/test_qrisk3.py compares these coefficients against the backend
    character for character. Keeping them in one small file makes that a file
    diff rather than a search through three thousand lines."""
    body = (SRC_DIR / "qrisk3.js").read_text(encoding="utf-8")
    assert "import" not in body.split("export")[0], (
        "qrisk3.js gained a dependency; it should stay standalone"
    )
    assert "normalCDF" in body


def test_app_is_smaller_than_before_the_split():
    """Not a vanity metric: the file was 3,857 lines and every panel edit meant
    opening all of it."""
    lines = len((SRC_DIR / "app.jsx").read_text(encoding="utf-8").splitlines())
    assert lines < 3200, f"app.jsx is {lines} lines; the extraction did not land"


# ── context-based state (M6 state refactor) ─────────────────────────────────

def test_clinical_state_context_exists_with_grouped_selectors():
    """Panels read a narrow slice, not the whole store. A single god-hook would
    let any panel reach any value and make the sharing surface unreviewable."""
    body = (SRC_DIR / "state.jsx").read_text(encoding="utf-8")
    for hook in ("usePatient", "useLiver", "useRenal", "useFrax"):
        assert f"function {hook}(" in body, f"{hook} selector is missing"
    assert "ClinicalStateProvider" in body


def test_using_state_outside_the_provider_fails_loudly():
    """A panel rendered outside the provider would otherwise crash on an
    undefined field somewhere deeper, pointing at the wrong place entirely."""
    body = (SRC_DIR / "state.jsx").read_text(encoding="utf-8")
    assert "throw new Error" in body
    assert "must be used inside" in body


@pytest.mark.parametrize("panel", ["LiverPanel", "RenalPanel", "FraxPanel"])
def test_extracted_panels_consume_context_not_props(panel):
    body = (SRC_DIR / "panels" / f"{panel}.jsx").read_text(encoding="utf-8")
    assert 'from "../state.jsx"' in body, f"{panel} does not read from context"
    assert f"function {panel}()" in body, (
        f"{panel} takes props -- the point of the context is that it does not have to"
    )


def test_app_renders_panels_as_elements_not_inline_jsx():
    app = (SRC_DIR / "app.jsx").read_text(encoding="utf-8")
    for panel in ("LiverPanel", "RenalPanel", "FraxPanel"):
        assert f"<{panel} />" in app, f"app.jsx does not render <{panel} />"
    assert "<ClinicalStateProvider" in app, "App does not provide the context"
    # The old inline blocks must be gone, not merely bypassed.
    assert "activeTab === 'liver' && (" not in app
    assert "Liver Fibrosis · FIB-4 Index" not in app, (
        "the liver panel markup is still in app.jsx as well as its own file"
    )


def test_context_value_is_explicit_rather_than_a_spread():
    """A spread would silently widen what panels can reach as App grows; the
    explicit list doubles as the record of what is genuinely cross-panel."""
    app = (SRC_DIR / "app.jsx").read_text(encoding="utf-8")
    start = app.index("const clinicalState = useMemo")
    assert "..." not in app[start:start + 700], "clinicalState is built with a spread"
