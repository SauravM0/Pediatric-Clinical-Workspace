"""Test bootstrap: make the repo importable and point the DB at a throwaway file
so tests never touch the real local database (set before any backend import)."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault(
    "TW3_DB_PATH", str(Path(tempfile.mkdtemp(prefix="tw3test_")) / "test.db")
)
