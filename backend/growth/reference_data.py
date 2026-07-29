"""Fingerprint of every input that can change a rendered growth curve (M0.4).

``api_growth`` memoises chart series because each build costs ~2-3s (WHO lookups
dominate). That cache was previously keyed only on the request parameters, which
was safe only because the reference data was effectively immutable at runtime.
It is about to stop being immutable: M1 introduces a real IAP LMS source file
and M2 adds velocity reference tables, and a swapped data file with an unchanged
request signature would otherwise keep serving the old curve for the process
lifetime — a silent, and clinically wrong, stale read.

Rather than remember to call ``cache_clear()`` at every future data-touching
site, the fingerprint is threaded into the cache key: changed data yields a new
key, and the stale entry simply becomes unreachable. Staleness becomes
structurally impossible instead of a discipline.

Cheap by construction: the digest is computed once per process and memoised, so
the per-request cost is a dict lookup.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache

from . import data_integrity


@lru_cache(maxsize=1)
def fingerprint() -> str:
    """Short digest over every reference input that can move a curve.

    Covers the six IAP 2015 CSVs (by parsed numeric content, so reformatting
    does not churn the key) and the pinned rcpchgrowth version, which supplies
    all WHO values. Memoised for the process lifetime: reference data is loaded
    at import and does not change under a running server, so recomputing per
    request would be pure waste. A data change ships as a new process.
    """
    parts: list[str] = []

    for name, digest in sorted(data_integrity.compute_manifest().items()):
        parts.append(f"{name}={digest}")

    parts.append(f"rcpchgrowth={_rcpchgrowth_version()}")

    payload = "|".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _rcpchgrowth_version() -> str:
    """Installed rcpchgrowth version — it ships the WHO reference values, so an
    upgrade can silently change chart output (hence the exact pin in
    requirements.txt). Reported as 'unknown' rather than raising if metadata is
    unavailable, so a fingerprint is always obtainable."""
    try:
        from importlib.metadata import version

        return version("rcpchgrowth")
    except Exception:  # pragma: no cover - defensive
        return "unknown"


def describe() -> dict:
    """Human-readable provenance block, for /api/growth/validate and reports."""
    return {
        "fingerprint": fingerprint(),
        "rcpchgrowth_version": _rcpchgrowth_version(),
        "iap_csv_checksums": data_integrity.compute_manifest(),
        "iap_numeric_cells": data_integrity.numeric_cell_count(),
    }
