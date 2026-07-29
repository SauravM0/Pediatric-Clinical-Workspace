"""Makes tests/ importable so every suite can share helpers (M6).

pytest's prepend import mode inserts the directory of each collected file,
so tests/frontend/ and tests/cvd/ land on sys.path but tests/ itself does
not. This conftest exists at tests/ purely so that it does -- which is what
lets any suite do `from _frontend_source import frontend_source` instead of
each one re-deriving the path to the frontend app.
"""
