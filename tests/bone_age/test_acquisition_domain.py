"""Auto-detecting a photograph of a film, rather than trusting a dropdown.

The gap this closes was found by uploading a real phone photo of a real film --
glare, perspective, a thumb in frame, a wall behind it. `auto_quality_flags`
returned an empty list, and the low-trust caveat appeared ONLY because the
domain was declared by hand. Left alone, the estimate was presented exactly like
a scanner export.

What this is NOT: a diagnostic classifier. `auto_quality_flags` deliberately
refuses to auto-detect fracture, cast, deformity or rotation, because those need
a validated model. How a file was ACQUIRED is a different kind of question -- it
is provenance, and it leaves deterministic traces in EXIF and colour.
"""
from __future__ import annotations

import io
import os
import tempfile

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "domain.db"))

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from PIL import Image  # noqa: E402

from backend.imaging import (  # noqa: E402
    COLOUR_SPREAD_PHOTO_THRESHOLD, CANONICAL_QUALITY_FLAGS, auto_quality_flags,
    detect_acquisition_domain, load_bytes, resolve_image_domain,
)

rng = np.random.default_rng(7)


def _radiograph_bytes(fmt="PNG", as_rgb=False, size=(400, 500)):
    """A grey image. If as_rgb, stored in three channels but still grey in every
    pixel -- the case is_color_source alone cannot tell from a photograph."""
    grey = rng.integers(30, 220, size=(size[1], size[0]), dtype=np.uint8)
    if as_rgb:
        arr = np.stack([grey, grey, grey], axis=-1)
        img = Image.fromarray(arr, mode="RGB")
    else:
        img = Image.fromarray(grey, mode="L")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _photo_bytes(size=(400, 500)):
    """A grey film with a warm colour cast over it, as a room light produces."""
    grey = rng.integers(30, 220, size=(size[1], size[0]), dtype=np.uint8)
    arr = np.stack([
        np.clip(grey.astype(np.int16) + 22, 0, 255),
        grey,
        np.clip(grey.astype(np.int16) - 18, 0, 255),
    ], axis=-1).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr, mode="RGB").save(buf, format="JPEG", quality=88)
    return buf.getvalue()


# ── the false-positive side, which matters most ─────────────────────────────

@pytest.mark.parametrize("fmt,as_rgb", [("PNG", False), ("JPEG", False),
                                        ("PNG", True), ("JPEG", True)])
def test_a_real_radiograph_is_never_called_a_photo(fmt, as_rgb):
    """Including one stored as RGB. A grey image in three channels has a colour
    spread of ~0 however it is saved -- which is exactly why the detector
    measures spread rather than trusting the mode flag."""
    img = load_bytes(_radiograph_bytes(fmt=fmt, as_rgb=as_rgb))
    assert img.colour_spread < COLOUR_SPREAD_PHOTO_THRESHOLD
    assert detect_acquisition_domain(img)["domain"] != "film_photo"


def test_dicom_is_certain_without_inspecting_pixels():
    from backend.imaging import LoadedImage

    img = LoadedImage(analysis=np.zeros((10, 10), dtype=np.uint8), width=10,
                      height=10, bit_depth=16, source_format="DICOM")
    d = detect_acquisition_domain(img)
    assert d["domain"] == "digital_diagnostic" and d["confidence"] == "certain"


# ── the true-positive side ──────────────────────────────────────────────────

def test_a_colour_cast_photograph_is_detected():
    img = load_bytes(_photo_bytes())
    assert img.colour_spread >= COLOUR_SPREAD_PHOTO_THRESHOLD
    d = detect_acquisition_domain(img)
    assert d["domain"] == "film_photo"
    assert any("real colour" in e for e in d["evidence"])


def test_camera_exif_alone_is_enough():
    """EXIF is routinely stripped by messaging apps, so it cannot be required --
    but when present it is close to proof, because an imaging workstation does
    not write FNumber and ISO."""
    from backend.imaging import LoadedImage

    img = LoadedImage(analysis=np.zeros((400, 400), dtype=np.uint8), width=400,
                      height=400, bit_depth=8, source_format="JPEG",
                      camera_exif={"Make": "Apple", "Model": "iPhone 15"})
    d = detect_acquisition_domain(img)
    assert d["domain"] == "film_photo"
    assert any("EXIF" in e for e in d["evidence"])


def test_both_signals_together_raise_confidence():
    from backend.imaging import LoadedImage

    img = LoadedImage(analysis=np.zeros((400, 400), dtype=np.uint8), width=400,
                      height=400, bit_depth=8, source_format="JPEG",
                      camera_exif={"Make": "Apple"}, colour_spread=9.0)
    assert detect_acquisition_domain(img)["confidence"] == "high"


def test_no_evidence_is_reported_as_unknown_not_as_clean():
    """Absence of evidence is not evidence of a scanner export -- a photo with
    EXIF stripped and colour removed looks identical, and the wording says so."""
    img = load_bytes(_radiograph_bytes())
    d = detect_acquisition_domain(img)
    assert d["domain"] == "unknown" and d["auto_detected"] is False
    assert "stripped photo looks the same" in " ".join(d["evidence"])


# ── resolution: detection defaults, the clinician decides ───────────────────

def test_detection_fills_in_what_the_clinician_left_blank():
    """The actual fix. Before this, an undeclared domain meant 'unknown', which
    is not low-trust, so the caveat never appeared."""
    photo = load_bytes(_photo_bytes())
    for declared in (None, "", "unknown"):
        r = resolve_image_domain(photo, declared)
        assert r["domain"] == "film_photo"
        assert r["source"] == "auto-detected"


def test_a_clinician_declaration_always_wins():
    """They were in the room. Detection defaults the field; it does not overrule."""
    clean = load_bytes(_radiograph_bytes())
    assert resolve_image_domain(clean, "film_photo")["domain"] == "film_photo"

    photo = load_bytes(_photo_bytes())
    r = resolve_image_domain(photo, "digital_diagnostic")
    assert r["domain"] == "digital_diagnostic"
    assert r["source"] == "clinician-declared"


def test_a_contradicted_declaration_is_honoured_but_surfaced():
    photo = load_bytes(_photo_bytes())
    r = resolve_image_domain(photo, "digital_diagnostic")
    assert r["conflict"] is not None
    assert "scanner export does not produce" in r["conflict"]
    assert r["domain"] == "digital_diagnostic", "the declaration must still stand"


def test_agreement_produces_no_conflict():
    clean = load_bytes(_radiograph_bytes())
    assert resolve_image_domain(clean, "digital_diagnostic")["conflict"] is None
    photo = load_bytes(_photo_bytes())
    assert resolve_image_domain(photo, "film_photo")["conflict"] is None


# ── the contract this deliberately does not touch ───────────────────────────

def test_no_new_quality_flag_was_invented():
    """The flag vocabulary is pinned to case_input_schema.json. Acquisition
    provenance has its own field (image_domain) and belongs there, not as a
    fourteenth quality flag."""
    assert "PHOTO_OF_FILM" not in CANONICAL_QUALITY_FLAGS
    photo = load_bytes(_photo_bytes())
    flags, notes = auto_quality_flags(photo)
    assert flags == [], "detection must not add a gating flag"
    assert any("real colour" in n for n in notes), "but the evidence must be visible"


def test_detection_never_blocks_an_estimate():
    """A photographed film still yields a usable screening number -- it just must
    not be presented as if it came off the scanner. Blocking would push people
    toward mis-declaring the domain to get any number at all."""
    from backend.imaging import gate_ai_estimate

    photo = load_bytes(_photo_bytes())
    flags, _ = auto_quality_flags(photo)
    assert gate_ai_estimate(flags, [])["accepted"] is True
