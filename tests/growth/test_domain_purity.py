"""backend/growth stays free of persistence (M2).

The most valuable architectural property in this repository is that the domain
packages are pure: ``backend/growth`` imports no SQLAlchemy and no FastAPI, so it
is deterministic, testable without a database, and reusable.

M2 is the milestone most likely to destroy that. The obvious way to compute a
velocity is to hand the growth package a Session and let it fetch the child's
history. It would work, and it would end the property -- every growth test would
then need a database, and the engine could no longer be lifted out.

The boundary is instead: ``growth_service`` does all persistence and passes
PLAIN VALUES (lists of ``(age_years, value)`` tuples) into the domain. These
tests make a violation fail loudly instead of being noticed a year later.

The same contract already holds for ``backend/tw3`` (pure) vs
``assessment_service`` (persistence), so this is an existing pattern being kept,
not a new rule.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

_GROWTH = Path(__file__).resolve().parents[2] / "backend" / "growth"

_FORBIDDEN_PREFIXES = ("sqlalchemy", "fastapi", "backend.models", "backend.db",
                       "backend.growth_service", "backend.assessment_service")


def _modules() -> list[Path]:
    files = sorted(p for p in _GROWTH.rglob("*.py") if "__pycache__" not in p.parts)
    assert files, f"no modules found under {_GROWTH} -- this guard would pass vacuously"
    return files


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


@pytest.mark.parametrize("path", _modules(), ids=lambda p: p.name)
def test_growth_module_has_no_persistence_dependency(path):
    """Catches the import wherever it hides -- including inside a function body,
    which a plain substring search over the source would miss."""
    offenders = sorted(
        name for name in _imported_names(path)
        if any(name == p or name.startswith(p + ".") for p in _FORBIDDEN_PREFIXES)
    )
    assert not offenders, (
        f"backend/growth/{path.name} imports {offenders}. The growth engine is pure "
        "by contract: persistence belongs in growth_service, which passes plain "
        "(age, value) tuples in. See this module's docstring for why."
    )


def test_the_guard_would_catch_a_real_violation(tmp_path):
    """Negative control: a guard that cannot fail is not a guard."""
    bad = tmp_path / "bad.py"
    bad.write_text("def f():\n    from sqlalchemy.orm import Session\n", encoding="utf-8")
    names = _imported_names(bad)
    assert any(n.startswith("sqlalchemy") for n in names), (
        "function-level imports are not detected -- the guard has a hole"
    )


def test_service_layer_is_the_one_that_talks_to_the_database():
    """The counterpart: growth_service SHOULD import persistence. If it stopped,
    the logic would have moved somewhere it does not belong."""
    svc = Path(__file__).resolve().parents[2] / "backend" / "growth_service.py"
    names = _imported_names(svc)
    assert any(n.startswith("sqlalchemy") for n in names)
    assert "backend.models" in names


def test_velocity_accepts_plain_values_only():
    """The boundary in practice: the pure function's signature takes floats, so
    an ORM row cannot be passed without the service converting it first."""
    import inspect

    from backend.growth import velocity

    # Every module here uses `from __future__ import annotations`, so annotations
    # are strings at runtime -- compare the text, not the type object.
    params = inspect.signature(velocity.velocity).parameters
    for name in ("a1", "v1", "a2", "v2"):
        assert params[name].annotation == "float", f"{name} should be a plain float"
