"""Locate the frontend application source for the static-analysis guards (M6).

The guards in this folder pin frontend behaviour by parsing the source rather
than driving a browser -- a deliberate zero-dependency choice (see
test_growth_chart_axis.py). Until M6 that source was the inline
`<script type="text/babel">` block in ``frontend/index.html``; it now lives in
``frontend/src/*.jsx`` and is compiled to ``frontend/app.js`` by build.mjs.

It lives at tests/ rather than tests/frontend/ because the CVD and bone-age
suites also assert against frontend source, and tests/conftest.py puts this
directory on sys.path for every suite.

Every guard goes through :func:`frontend_source` so the next move -- splitting
app.jsx into components -- is a one-line change here instead of an edit in each
test file. It concatenates every .jsx under src/, so a constant keeps being
found wherever it ends up.

:func:`frontend_source` deliberately does NOT read the built app.js. The guards
exist to constrain what a developer writes; asserting against generated output
would let a source change slip through whenever the artefact was stale (the
staleness itself is covered separately by test_build_artefact.py).

The empty-source assertion matters more than it looks: these guards work by
searching text, so a path that silently resolves to nothing turns every one of
them into a test that always passes.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = _ROOT / "frontend"
SRC_DIR = FRONTEND_DIR / "src"
INDEX_HTML = FRONTEND_DIR / "index.html"
BUILT_BUNDLE = FRONTEND_DIR / "app.js"


@lru_cache(maxsize=1)
def frontend_source() -> str:
    """Concatenated text of every authored frontend module."""
    files = sorted(SRC_DIR.rglob("*.jsx")) + sorted(SRC_DIR.rglob("*.js"))
    assert files, (
        f"no frontend source found under {SRC_DIR}. Every guard in this folder "
        "works by searching this text, so an empty result would silently turn "
        "them all into tests that always pass."
    )
    text = "\n".join(f.read_text(encoding="utf-8") for f in files)
    assert len(text) > 50_000, (
        f"frontend source is only {len(text)} chars -- suspiciously small; the "
        "guards below would not be searching what they think they are."
    )
    return text


@lru_cache(maxsize=1)
def index_html() -> str:
    """The HTML shell only (no application logic since M6)."""
    return INDEX_HTML.read_text(encoding="utf-8")
