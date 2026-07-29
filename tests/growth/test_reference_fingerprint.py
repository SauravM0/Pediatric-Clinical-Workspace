"""Chart cache is keyed on the reference data, not just the request (M0.4).

`_cached_series` memoises ~2-3s chart builds. That was safe only while the
reference data was immutable at runtime. M1 introduces a real IAP LMS source
file and M2 adds velocity tables, at which point a swapped data file with an
unchanged request signature would keep serving the OLD curve for the process
lifetime -- a silent, clinically wrong, stale read.

Threading a data fingerprint into the cache key makes that structurally
impossible rather than something to remember to invalidate. These tests pin
that property.
"""
import os
import tempfile

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "fp_test.db"))

from backend import api_growth
from backend.growth import data_integrity, reference_data


def test_fingerprint_is_stable_and_short():
    a, b = reference_data.fingerprint(), reference_data.fingerprint()
    assert a == b, "fingerprint must be deterministic within a process"
    assert len(a) == 16 and all(c in "0123456789abcdef" for c in a)


def test_fingerprint_tracks_the_reference_data(monkeypatch):
    """The whole point: change a published value, get a different key."""
    before = reference_data.fingerprint()

    real = data_integrity.compute_manifest()
    tampered = dict(real)
    first = sorted(tampered)[0]
    tampered[first] = "0" * 64          # simulate one changed percentile

    reference_data.fingerprint.cache_clear()
    monkeypatch.setattr(data_integrity, "compute_manifest", lambda: tampered)
    after = reference_data.fingerprint()

    assert after != before, (
        "fingerprint did not change when IAP reference content changed -- the "
        "chart cache would keep serving curves built from the old numbers"
    )

    reference_data.fingerprint.cache_clear()
    monkeypatch.undo()
    assert reference_data.fingerprint() == before, "fingerprint must be reversible"


def test_fingerprint_tracks_the_rcpchgrowth_version(monkeypatch):
    """rcpchgrowth ships every WHO value, so an upgrade can move the curves --
    which is exactly why requirements.txt pins it exactly."""
    before = reference_data.fingerprint()
    reference_data.fingerprint.cache_clear()
    monkeypatch.setattr(reference_data, "_rcpchgrowth_version", lambda: "0.0.0-fake")
    assert reference_data.fingerprint() != before

    reference_data.fingerprint.cache_clear()
    monkeypatch.undo()
    assert reference_data.fingerprint() == before


def test_stale_curve_is_unreachable_after_a_data_change(monkeypatch):
    """End-to-end: the cached entry built under fingerprint A must not be served
    once the data (and therefore the fingerprint) has moved to B."""
    api_growth._cached_series.cache_clear()
    reference_data.fingerprint.cache_clear()

    api_growth._series("height", "boys", 5.0, 6.0, 0.5)
    hits_before = api_growth._cached_series.cache_info()

    # Same request, unchanged data -> served from cache.
    api_growth._series("height", "boys", 5.0, 6.0, 0.5)
    assert api_growth._cached_series.cache_info().hits == hits_before.hits + 1

    # Same request, CHANGED data -> must miss and rebuild, not reuse.
    tampered = dict(data_integrity.compute_manifest())
    tampered[sorted(tampered)[0]] = "1" * 64
    reference_data.fingerprint.cache_clear()
    monkeypatch.setattr(data_integrity, "compute_manifest", lambda: tampered)

    misses_before = api_growth._cached_series.cache_info().misses
    api_growth._series("height", "boys", 5.0, 6.0, 0.5)
    assert api_growth._cached_series.cache_info().misses == misses_before + 1, (
        "a reference-data change did not force a cache miss -- stale curves would be served"
    )

    reference_data.fingerprint.cache_clear()
    monkeypatch.undo()


def test_cache_is_bounded():
    """maxsize was None (unbounded) while every key component is caller-supplied:
    measures x sexes x age ranges x render steps x data versions."""
    assert api_growth._cached_series.cache_info().maxsize is not None


def test_describe_exposes_provenance():
    d = reference_data.describe()
    assert d["fingerprint"] == reference_data.fingerprint()
    assert d["iap_numeric_cells"] == 1134, "IAP source cell count changed unexpectedly"
    assert len(d["iap_csv_checksums"]) == len(data_integrity.CSV_FILES)
