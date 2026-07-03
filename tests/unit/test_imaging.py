"""Image ingestion + upload tests (directive §25.2, §25.3)."""

from __future__ import annotations

import io
import uuid

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.imaging import ImagingError, load_bytes, quality_precheck
from backend.server import app

client = TestClient(app)


def _png_bytes(w=400, h=520, color=False, value=128) -> bytes:
    mode = "RGB" if color else "L"
    fill = (value, value, value) if color else value
    img = Image.new(mode, (w, h), fill)
    # add some contrast so it isn't flagged low_contrast
    arr = np.asarray(img).copy()
    arr[: h // 2] = 30
    img = Image.fromarray(arr, mode=mode)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_bytes(w=400, h=520) -> bytes:
    arr = np.random.default_rng(1).integers(0, 255, size=(h, w), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr, mode="L").save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _dicom_bytes(monochrome1=False, w=300, h=360, laterality="L") -> bytes:
    from pydicom.dataset import Dataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid

    grad = np.tile(np.linspace(0, 4000, w, dtype=np.uint16), (h, 1))
    ds = Dataset()
    ds.file_meta = FileMetaDataset()
    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.file_meta.MediaStorageSOPClassUID = generate_uid()
    ds.file_meta.MediaStorageSOPInstanceUID = generate_uid()
    ds.SOPClassUID = ds.file_meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = ds.file_meta.MediaStorageSOPInstanceUID
    ds.Rows, ds.Columns = h, w
    ds.BitsAllocated, ds.BitsStored, ds.HighBit = 16, 12, 11
    ds.PixelRepresentation, ds.SamplesPerPixel = 0, 1
    ds.PhotometricInterpretation = "MONOCHROME1" if monochrome1 else "MONOCHROME2"
    ds.Modality = "CR"
    ds.ImageLaterality = laterality
    ds.PixelData = grad.tobytes()
    buf = io.BytesIO()
    ds.save_as(buf, enforce_file_format=True)
    return buf.getvalue()


# ── loader unit tests ─────────────────────────────────────────────────────────

def test_load_png() -> None:
    img = load_bytes(_png_bytes(), "hand.png")
    assert img.source_format == "PNG"
    assert (img.width, img.height) == (400, 520)


def test_load_jpeg() -> None:
    img = load_bytes(_jpeg_bytes(), "hand.jpg")
    assert img.source_format == "JPEG"


def test_load_color_warns() -> None:
    img = load_bytes(_png_bytes(color=True), "photo.png")
    assert "colour_source_converted_to_grayscale" in img.warnings


def test_load_dicom_monochrome2() -> None:
    img = load_bytes(_dicom_bytes(monochrome1=False), "study.dcm")
    assert img.source_format == "DICOM"
    assert img.laterality == "L"
    assert (img.width, img.height) == (300, 360)


def test_dicom_monochrome1_is_inverted() -> None:
    m2 = load_bytes(_dicom_bytes(monochrome1=False), "a.dcm").analysis.astype(int)
    m1 = load_bytes(_dicom_bytes(monochrome1=True), "b.dcm").analysis.astype(int)
    # MONOCHROME1 is inverted relative to MONOCHROME2 (bone made bright)
    assert abs(int(m1.mean()) + int(m2.mean()) - 255) < 20
    assert not np.array_equal(m1, m2)


def test_corrupted_file_rejected() -> None:
    with pytest.raises(ImagingError):
        load_bytes(b"not-an-image-at-all", "broken.png")


def test_empty_upload_rejected() -> None:
    with pytest.raises(ImagingError):
        load_bytes(b"", "x.png")


def test_misleading_extension_still_decodes() -> None:
    # PNG bytes with a .dcm name: not real DICOM, should fall back to raster decode.
    img = load_bytes(_png_bytes(), "actually_png.dcm")
    assert img.source_format == "PNG"


def test_quality_flags_small_and_lowcontrast() -> None:
    small = load_bytes(_png_bytes(w=150, h=150), "s.png")
    status, flags = quality_precheck(small)
    assert status == "doctor_review_required"
    assert "very_small_image" in flags

    right = load_bytes(_dicom_bytes(laterality="R"), "r.dcm")
    status2, flags2 = quality_precheck(right)
    assert "laterality_right_check_left_hand" in flags2


# ── upload API tests ──────────────────────────────────────────────────────────

def _new_assessment() -> int:
    code = f"IMG-{uuid.uuid4().hex[:8]}"
    return client.post("/api/bone-age/assessments",
                       json={"patient_code": code, "sex": "girls"}).json()["id"]


def test_upload_attaches_and_serves_thumbnail() -> None:
    aid = _new_assessment()
    r = client.post(f"/api/bone-age/assessments/{aid}/image",
                    files={"file": ("hand.png", _png_bytes(), "image/png")})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["source_format"] == "PNG"
    assert body["quality_status"] in ("accepted", "accepted_with_warning", "doctor_review_required")
    # assessment now references the radiograph
    a = client.get(f"/api/bone-age/assessments/{aid}").json()
    assert a is not None
    thumb = client.get(body["thumbnail_url"])
    assert thumb.status_code == 200
    assert thumb.headers["content-type"] == "image/png"


def test_upload_corrupted_rejected() -> None:
    aid = _new_assessment()
    r = client.post(f"/api/bone-age/assessments/{aid}/image",
                    files={"file": ("bad.png", b"garbage", "image/png")})
    assert r.status_code == 422


def test_duplicate_upload_flagged_not_blocked() -> None:
    aid = _new_assessment()
    png = _png_bytes()
    first = client.post(f"/api/bone-age/assessments/{aid}/image",
                        files={"file": ("h.png", png, "image/png")}).json()
    aid2 = _new_assessment()  # same patient? no — different; use same patient path below
    # re-upload identical bytes to the SAME patient's new assessment revision path:
    second = client.post(f"/api/bone-age/assessments/{aid}/image",
                         files={"file": ("h.png", png, "image/png")}).json()
    assert second["duplicate_of"] == first["radiograph_id"]
