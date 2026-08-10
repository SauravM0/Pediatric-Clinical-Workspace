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
    for hook in ("usePatient", "useLiver", "useRenal", "useFrax", "useBoneAge"):
        assert f"function {hook}(" in body, f"{hook} selector is missing"
    assert "ClinicalStateProvider" in body


_SELECTOR_CONSUMERS = {
    "useLiver": ["LiverPanel"],
    "useRenal": ["RenalPanel"],
    "useFrax": ["FraxPanel"],
    "useOverview": ["OverviewPanel"],
    "useGrowth": ["GrowthPanel"],
    "useQrisk": ["QriskPanel"],
    "useLedger": ["LedgerPanel"],
    "useBoneAge": ["BoneAgePanel"],
}


def _code_only(source: str) -> str:
    """Strip comments and string CONTENT, keeping code.

    Without this the guard is vacuous: RenalPanel's subtitle reads "Multi-equation
    clearance monitoring", so the prose word `monitoring` satisfied a search for
    the identifier `monitoring` and the leak it was written to catch sailed
    through. Template-literal `${...}` expressions are kept, since those are real
    code.
    """
    def _template(match: re.Match) -> str:
        return " ".join(re.findall(r"\$\{([^{}]*)\}", match.group(0)))

    # Strings FIRST, comments second. The other order breaks on
    # `accept=".dcm,image/*"`: the `/*` inside that attribute opens a phantom
    # comment that swallows the next several hundred lines of real code, which
    # is what made this guard report nine used names as unused.
    src = re.sub(r'"(?:[^"\\\n]|\\.)*"', ' "" ', source)
    src = re.sub(r"`(?:[^`\\]|\\.)*`", _template, src, flags=re.S)
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"//[^\n]*", " ", src)
    # Single-quoted strings are deliberately LEFT ALONE. JSX text is not quoted,
    # so a prose apostrophe ("someone's") opens a phantom string that swallows
    # the real code after it -- which produced four false positives the first
    # time this ran. The strings that actually carry field names here are JSX
    # attributes (double-quoted) and subtitles (template literals); single quotes
    # in this codebase hold CSS values like '11px'.
    return src


def _selector_fields(body: str, hook: str) -> set[str]:
    """Keys a selector hook returns."""
    start = body.index(f"function {hook}(")
    ret = body.index("return", start)
    depth, end = 0, ret
    for i in range(body.index("{", ret), len(body)):
        if body[i] == "{":
            depth += 1
        elif body[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    block = body[ret:end]
    # `name: s.thing` and shorthand `name,`
    keys = set(re.findall(r"([a-zA-Z_$][\w$]*)\s*:", block))
    keys |= set(re.findall(r"^\s*([a-zA-Z_$][\w$]*)\s*,\s*$", block, re.M))
    return keys


@pytest.mark.parametrize("hook,panels", sorted(_SELECTOR_CONSUMERS.items()))
def test_selectors_expose_nothing_the_panel_does_not_use(hook, panels):
    """A slice must not carry a value its panel never reads.

    Not tidiness. `useRenal` exposed `monitoring` — the bone-age AI monitoring
    payload — to the renal panel, which destructured it and never used it. It
    got there because that state sits next to the renal fields in
    clinicalState. Nothing broke, and that is the problem: the narrow selectors
    exist so a panel *cannot* reach a value nobody decided to share with it, and
    an unused field is exactly how that guarantee erodes into a god-object one
    key at a time.
    """
    state = (SRC_DIR / "state.jsx").read_text(encoding="utf-8")
    exposed = _selector_fields(state, hook)
    assert exposed, f"could not parse the fields {hook} returns"

    used: set[str] = set()
    for panel in panels:
        body = (SRC_DIR / "panels" / f"{panel}.jsx").read_text(encoding="utf-8")
        # Everything after the destructuring line: what the panel actually reads.
        # Prose and comments stripped first, or a field name mentioned in a
        # subtitle counts as a use of the value.
        after = _code_only(body[body.index(f"{hook}()"):])
        used |= set(re.findall(r"\b([a-zA-Z_$][\w$]*)\b", after))

    unused = sorted(f for f in exposed if f not in used)
    assert not unused, (
        f"{hook} exposes {unused} to {panels}, which never read them. Remove the "
        "field from the selector, or use it — a slice that carries what nobody "
        "asked for is the first step back to one shared store."
    )


def test_using_state_outside_the_provider_fails_loudly():
    """A panel rendered outside the provider would otherwise crash on an
    undefined field somewhere deeper, pointing at the wrong place entirely."""
    body = (SRC_DIR / "state.jsx").read_text(encoding="utf-8")
    assert "throw new Error" in body
    assert "must be used inside" in body


_PANELS = ["LiverPanel", "RenalPanel", "FraxPanel", "OverviewPanel",
           "GrowthPanel", "QriskPanel", "LedgerPanel", "BoneAgePanel"]


@pytest.mark.parametrize("panel", _PANELS)
def test_extracted_panels_consume_context_not_props(panel):
    body = (SRC_DIR / "panels" / f"{panel}.jsx").read_text(encoding="utf-8")
    assert 'from "../state.jsx"' in body, f"{panel} does not read from context"
    assert f"function {panel}()" in body, (
        f"{panel} takes props -- the point of the context is that it does not have to"
    )


def test_app_renders_panels_as_elements_not_inline_jsx():
    app = (SRC_DIR / "app.jsx").read_text(encoding="utf-8")
    for panel in _PANELS:
        assert f"<{panel} />" in app, f"app.jsx does not render <{panel} />"
    assert "<ClinicalStateProvider" in app, "App does not provide the context"


def test_no_panel_markup_is_left_behind_in_app():
    """A distinctive string from each panel. If markup survives in app.jsx as
    well as its own file, the two copies drift and only one is rendered."""
    app = (SRC_DIR / "app.jsx").read_text(encoding="utf-8")
    # Markup strings unique to a panel. Deliberately NOT bare identifiers like
    # "QRISK3" -- that appears legitimately in app.jsx's import line, its
    # moduleStatus title and a comment, so it would fail on correct code.
    for needle in ("Liver Fibrosis · FIB-4 Index",
                   "QRISK3 · 10-Year Cardiovascular Risk",
                   "FRAX Plus · 10-Year Fracture Risk",
                   "Every module's headline at a glance",
                   "Bone Age · 20-bone staging (13 RUS + 7 carpal)",
                   "activeTab === 'liver' && (",
                   "activeTab === 'qrisk' && (",
                   "activeTab === 'boneage' && (",
                   "activeTab === 'growth' && (() =>"):
        assert needle not in app, f"{needle!r} is still inline in app.jsx"


def test_app_is_now_mostly_state_and_handlers():
    """Started at 3,857 lines with every panel inline. What is left is the state,
    the input column and the wiring -- every panel, including Bone Age, is its
    own file."""
    lines = len((SRC_DIR / "app.jsx").read_text(encoding="utf-8").splitlines())
    assert lines < 1500, f"app.jsx is {lines} lines; the panel extraction regressed"


def test_domain_state_lives_in_its_own_module():
    """The two groups M6's ownership audit found worth relocating.

    App still OWNS this state -- the hooks run in App's render -- but the
    declarations, defaults and the comments explaining them belong with their
    domain, not in a 60-line run inside a 1,300-line component.
    """
    for module, hook, sample in (
        ("boneAgeState.js", "useBoneAgeState", "const [rusStages, setRusStages]"),
        ("qriskState.js", "useQriskInputs", "const [qAF, setQAF]"),
    ):
        body = (SRC_DIR / module).read_text(encoding="utf-8")
        assert f"function {hook}(" in body, f"{module} does not define {hook}"
        assert f"export {{ {hook}" in body, f"{module} does not export {hook}"
        assert sample in body, f"{module} lost {sample!r}"

    app = (SRC_DIR / "app.jsx").read_text(encoding="utf-8")
    for hook in ("useBoneAgeState", "useQriskInputs"):
        assert f"{hook}()" in app, f"app.jsx does not call {hook}"
    # ...and does not also declare them, which would be two independent states
    # with the panel reading one and App writing the other.
    for moved in ("const [rusStages,", "const [qAF,", "const [ltTables,",
                  "const [cholRatio,", "const [aiEstimate,"):
        assert moved not in app, (
            f"{moved!r} is declared in app.jsx as well as its state module -- "
            "two useState calls means two separate states"
        )


def test_app_no_longer_declares_most_of_the_state_inline():
    """Started at ~97 useState declarations in one component."""
    app = (SRC_DIR / "app.jsx").read_text(encoding="utf-8")
    declared = len(re.findall(r"const\s*\[\s*\w+\s*,\s*\w+\s*\]\s*=\s*useState", app))
    assert declared < 40, f"app.jsx still declares {declared} useState bindings inline"


def test_every_name_in_clinical_state_is_defined_in_app():
    """A name listed in clinicalState but never bound is a ReferenceError at
    MOUNT — the whole app renders nothing, not just one panel.

    Not hypothetical: adding `loadLocalCohort` to the context without also
    destructuring it from useBoneAgeHandlers took the entire workspace down to a
    blank page. esbuild cannot see it (the name could legally come from an
    import or an outer scope), so nothing else catches it.
    """
    app = (SRC_DIR / "app.jsx").read_text(encoding="utf-8")
    start = app.index("const clinicalState = {")
    depth, end = 0, start
    for i in range(app.index("{", start), len(app)):
        if app[i] == "{":
            depth += 1
        elif app[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    listed = set(re.findall(r"^\s*([a-zA-Z_$][\w$]*)\s*,\s*$",
                            app[start:end], re.M))

    before = app[:start]
    bound = set()
    # const/let/var bindings, destructured names, function params and imports.
    bound |= set(re.findall(r"\b(?:const|let|var)\s+([a-zA-Z_$][\w$]*)", before))
    for block in re.findall(r"(?:const|let|var)\s*\{([^}]*)\}\s*=", before, re.S):
        bound |= {n.strip().split(":")[-1].strip().split("=")[0].strip()
                  for n in block.split(",") if n.strip()}
    # const [value, setValue] = useState(...) — how nearly all of this state is
    # bound, and the case the first version of this guard missed entirely.
    for block in re.findall(r"(?:const|let|var)\s*\[([^\]]*)\]\s*=", before, re.S):
        bound |= {n.strip().split("=")[0].strip()
                  for n in block.split(",") if n.strip()}
    for block in re.findall(r"import\s*\{([^}]*)\}", before, re.S):
        bound |= {n.strip().split(" as ")[-1].strip() for n in block.split(",") if n.strip()}
    bound |= set(re.findall(r"function\s+([a-zA-Z_$][\w$]*)", before))

    missing = sorted(n for n in listed if n not in bound)
    assert not missing, (
        f"clinicalState lists {missing}, which app.jsx never binds — the app "
        "will throw at mount and render a blank page"
    )


def test_context_value_is_explicit_rather_than_a_spread():
    """A spread would silently widen what panels can reach as App grows; the
    explicit list doubles as the record of what is genuinely cross-panel."""
    app = (SRC_DIR / "app.jsx").read_text(encoding="utf-8")
    start = app.index("const clinicalState = {")
    assert "..." not in app[start:start + 700], "clinicalState is built with a spread"


# ── bone age: handlers and panel (the last and largest extraction) ──────────

def test_bone_age_handlers_are_their_own_module():
    """Bone Age was 907 lines with ~34 mostly-async handlers. The panel renders;
    the handlers -- fetch, upload, adjudication, audit -- live apart from it so
    the markup can be read without scrolling past the network code."""
    body = (SRC_DIR / "boneAgeHandlers.js").read_text(encoding="utf-8")
    assert "function useBoneAgeHandlers(" in body
    assert "export { useBoneAgeHandlers }" in body
    assert "<div" not in body, (
        "boneAgeHandlers.js grew markup -- it is a .js file, so esbuild will not "
        "even transform JSX in it, and the failure would be a parse error"
    )


def test_app_owns_bone_age_state_but_not_bone_age_handlers():
    """The asymmetry is deliberate and worth pinning: App still reads 27 of the
    bone-age STATE values (the header, the ledger and the export all need them),
    but none of the handlers. So the handlers moved out and the state stayed."""
    app = (SRC_DIR / "app.jsx").read_text(encoding="utf-8")
    assert "useBoneAgeHandlers({" in app, "App no longer wires up the handlers"
    for moved in ("const runEstimate", "const calculateAssessment",
                  "const loadCoverage", "const loadAdjudication",
                  "const resolveAdjudication", "const saveLetterTables"):
        assert moved not in app, (
            f"{moved!r} is defined in app.jsx as well as boneAgeHandlers.js"
        )


def test_bone_age_panel_declares_every_name_it_uses_from_context():
    """A name used but never destructured from useBoneAge() is a ReferenceError
    at RENDER time. The bundler does not report it -- the panel simply blanks
    out when a doctor opens the tab -- so it is checked here instead."""
    body = (SRC_DIR / "panels" / "BoneAgePanel.jsx").read_text(encoding="utf-8")
    slice_start = body.index("useBoneAge()")
    declared_block = body[body.index("{", body.index("function BoneAgePanel")):slice_start]
    declared = set(re.findall(r"\b([a-zA-Z_$][\w$]*)\b", declared_block))
    imported = set(re.findall(r"import\s*\{([^}]*)\}", body))
    for group in imported:
        declared |= {n.strip().split(" as ")[-1].strip() for n in group.split(",")}

    # Handler names follow a stable convention; those are the ones that were
    # rewired and so the ones at risk of being used without being declared.
    used = set(re.findall(r"\b((?:handle|run|load|refresh|fetch|save|apply|toggle)"
                          r"[A-Z][\w$]*)\b", body))
    missing = sorted(n for n in used if n not in declared)
    assert not missing, (
        f"BoneAgePanel uses {missing} without destructuring them from useBoneAge() "
        "-- these would be ReferenceErrors the moment the tab is opened"
    )
