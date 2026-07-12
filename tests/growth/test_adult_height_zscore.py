"""Parity guard for the predicted-adult-height percentile (audit F-2).

The frontend used to derive the adult-height z-score with a symmetric
SD = (P75 - P25) / 2. For a normal distribution P75/P25 sit at z = +/-0.6745,
so (P75 - P25) = 1.349 * SD -- the /2 form understates SD ~1.48x and pushes
every derived percentile toward the extremes (a true 75th-centile prediction
was reported as ~84th; a P97 value as z=+2.79 instead of +1.88).

The fix inverts the value against the real (LMS-derived, possibly skewed)
7-centile distribution returned by /api/growth/reference-stats, mirroring what
/api/growth/point does continuously. This test:

  1. reproduces the frontend's `zForValueFromCentileStats` in Python and
     asserts it agrees with the backend's exact /point z-score, and
  2. pins the magnitude of the old bug so it can't silently return.

End-to-end through the real FastAPI app (no DB/model needed for growth).
"""
import os
import tempfile

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "growth_test.db"))

import pytest
from fastapi.testclient import TestClient

from backend.server import app

# Identical anchors + algorithm to the frontend helper (index.html).
_CENTILE_Z = [
    (3, -1.8807936), (10, -1.2815516), (25, -0.6744898), (50, 0.0),
    (75, 0.6744898), (90, 1.2815516), (97, 1.8807936),
]
_IQR_TO_SD = 1.3489795


def z_for_value_from_centile_stats(stats: dict, value: float):
    """Python mirror of the frontend zForValueFromCentileStats."""
    if not stats or not stats.get("available") or not (value and value > 0):
        return None
    pts = [(stats[f"p{c}"], z) for c, z in _CENTILE_Z if isinstance(stats.get(f"p{c}"), (int, float))]
    if len(pts) < 2:
        return None
    pts.sort(key=lambda p: p[0])  # ascending by value

    def lerp(x0, z0, x1, z1):
        return z0 if x1 == x0 else z0 + (value - x0) / (x1 - x0) * (z1 - z0)

    n = len(pts)
    if value <= pts[0][0]:
        return lerp(pts[0][0], pts[0][1], pts[1][0], pts[1][1])
    if value >= pts[n - 1][0]:
        return lerp(pts[n - 2][0], pts[n - 2][1], pts[n - 1][0], pts[n - 1][1])
    for i in range(n - 1):
        if pts[i][0] <= value <= pts[i + 1][0]:
            return lerp(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
    return None


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _stats(client, sex):
    r = client.get(f"/api/growth/reference-stats?measure=height&sex={sex}&age=19")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    return body


def _exact_z(client, sex, value):
    r = client.get(f"/api/growth/point?measure=height&sex={sex}&age=19&value={value}")
    assert r.status_code == 200
    return r.json()["z"]


@pytest.mark.parametrize("sex", ["boys", "girls"])
def test_mirror_matches_backend_exact_z_at_published_centiles(client, sex):
    stats = _stats(client, sex)
    # At each published centile's own value, the mirror must return that
    # centile's z, and the backend's exact inverse must agree.
    for c, z in _CENTILE_Z:
        value = stats[f"p{c}"]
        mirror = z_for_value_from_centile_stats(stats, value)
        exact = _exact_z(client, sex, value)
        assert mirror == pytest.approx(z, abs=1e-6), f"{sex} p{c}: mirror {mirror} != anchor {z}"
        assert mirror == pytest.approx(exact, abs=0.02), f"{sex} p{c}: mirror {mirror} vs backend {exact}"


@pytest.mark.parametrize("sex", ["boys", "girls"])
def test_mirror_matches_backend_between_centiles(client, sex):
    stats = _stats(client, sex)
    # A value halfway (in cm) between P50 and P75 must land close to the backend's
    # continuous inverse -- the monotone interpolation tracks the real curve.
    value = (stats["p50"] + stats["p75"]) / 2
    mirror = z_for_value_from_centile_stats(stats, value)
    exact = _exact_z(client, sex, value)
    assert mirror == pytest.approx(exact, abs=0.06), f"{sex} mid P50-P75: mirror {mirror} vs backend {exact}"


@pytest.mark.parametrize("sex", ["boys", "girls"])
def test_old_symmetric_sd_method_was_materially_wrong(client, sex):
    """Regression guard: the retired (P75-P25)/2 SD overstates tail z ~1.48x."""
    stats = _stats(client, sex)
    old_sd = (stats["p75"] - stats["p25"]) / 2.0
    value_p97 = stats["p97"]
    old_z = (value_p97 - stats["p50"]) / old_sd
    exact = _exact_z(client, sex, value_p97)
    # The old method would report the 97th-centile height as z ~= +2.79.
    assert old_z / exact == pytest.approx(2.0 / _IQR_TO_SD, abs=0.03)
    assert old_z > 2.6 and exact == pytest.approx(1.88, abs=0.05)
