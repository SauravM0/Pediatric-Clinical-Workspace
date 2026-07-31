"""The de-identification claim is verified, not asserted (C.4).

Every upload is stamped ``anonymisation_status="working_copy_deidentified"``.
Nothing checked it. These tests build a DICOM stuffed with identifiers, run it
through the real ingest path, and confirm none of them reach the stored working
copy -- so the stamp is backed by evidence.
"""
from __future__ import annotations

import io

import pytest

pydicom = pytest.importorskip("pydicom")

from backend.imaging import load_bytes, store_radiograph
from backend.security.dicom_deid import (
    ALLOWED_TAGS,
    KNOWN_IDENTIFYING_TAGS,
    inspect_dataset,
    verify_working_copy,
)


def _identified_dicom(*, burned_in: str = "NO") -> bytes:
    """A minimal but realistically over-stuffed CR study."""
    import numpy as np
    from pydicom.dataset import Dataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian

    ds = Dataset()
    ds.PatientName = "Sharma^Aarav"
    ds.PatientID = "MRN-99887"
    ds.PatientBirthDate = "20150714"
    ds.PatientAddress = "12 Model Colony, Pune"
    ds.ReferringPhysicianName = "Khadilkar^V"
    ds.PerformingPhysicianName = "Rao^S"
    ds.OperatorsName = "tech01"
    ds.InstitutionName = "Jehangir Hospital"
    ds.InstitutionAddress = "32 Sassoon Road, Pune"
    ds.StationName = "CR-ROOM-2"
    ds.AccessionNumber = "ACC-555"
    ds.StudyID = "ST-1"
    ds.StudyInstanceUID = "1.2.826.0.1.3680043.8.498.1"
    ds.SeriesInstanceUID = "1.2.826.0.1.3680043.8.498.2"
    ds.SOPInstanceUID = "1.2.826.0.1.3680043.8.498.3"
    ds.EthnicGroup = "Asian Indian"
    ds.PatientComments = "mother requests results by phone"

    ds.Modality = "CR"
    ds.ImageLaterality = "L"
    ds.StudyDate = "20260726"
    ds.BurnedInAnnotation = burned_in

    arr = (np.linspace(0, 4095, 64 * 64, dtype="uint16")).reshape(64, 64)
    ds.Rows, ds.Columns = 64, 64
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated, ds.BitsStored, ds.HighBit = 16, 12, 11
    ds.PixelRepresentation = 0
    ds.PixelData = arr.tobytes()

    ds.file_meta = FileMetaDataset()
    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.1"
    ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID

    buf = io.BytesIO()
    ds.save_as(buf, enforce_file_format=True)
    return buf.getvalue()


def test_identifying_tags_are_all_dropped():
    report = verify_working_copy(_identified_dicom())
    assert report.clean, f"retained beyond the allowlist: {set(report.retained) - ALLOWED_TAGS}"
    for tag in ("PatientName", "PatientID", "PatientBirthDate", "InstitutionName",
                "ReferringPhysicianName", "AccessionNumber", "StudyInstanceUID"):
        assert tag in report.dropped_identifying, f"{tag} was not classified as identifying"


def test_only_allowlisted_tags_are_retained():
    report = verify_working_copy(_identified_dicom())
    assert set(report.retained) <= ALLOWED_TAGS
    # The retained ones must be genuinely useful, not incidental.
    assert "Modality" in report.retained
    assert report.retained["ImageLaterality"] == "L"


def test_no_identifier_survives_into_the_stored_working_copy(tmp_path):
    """The end-to-end claim: what lands on disk carries none of it."""
    raw = _identified_dicom()
    loaded = load_bytes(raw, "study.dcm")
    paths = store_radiograph(tmp_path / "1", raw, loaded, "dcm")

    for kind in ("analysis", "thumbnail"):
        blob = open(paths[kind], "rb").read()
        for needle in (b"Sharma", b"Aarav", b"MRN-99887", b"Jehangir",
                       b"Khadilkar", b"ACC-555", b"20150714"):
            assert needle not in blob, (
                f"{needle!r} survived into the stored {kind} image -- the "
                "'working_copy_deidentified' stamp would be false"
            )


def test_the_original_is_kept_byte_for_byte():
    """De-identification applies to the WORKING COPY. The original is retained
    unmodified on purpose (it is the medico-legal record), which is exactly why
    it is never served -- see radiograph_service.radiograph_file."""
    raw = _identified_dicom()
    loaded = load_bytes(raw, "study.dcm")
    import tempfile
    from pathlib import Path

    dest = Path(tempfile.mkdtemp()) / "1"
    paths = store_radiograph(dest, raw, loaded, "dcm")
    assert open(paths["original"], "rb").read() == raw
    assert b"Sharma" in open(paths["original"], "rb").read()


def test_burned_in_annotation_is_warned_about_not_silently_passed():
    """A tag scan cannot see text rendered into pixels. The honest response is a
    warning for a human, not a clean bill of health."""
    report = verify_working_copy(_identified_dicom(burned_in="YES"))
    assert any("BurnedInAnnotation" in w for w in report.warnings)
    assert "burned-in" in report.to_dict()["limitation"].lower()


def test_private_tags_are_dropped_wholesale():
    """Vendor private blocks can hold anything, so they are never allowlisted."""
    from pydicom.dataset import Dataset

    ds = Dataset()
    ds.Modality = "CR"
    block = ds.private_block(0x000B, "TEST CREATOR", create=True)
    block.add_new(0x01, "LO", "patient nickname")
    report = inspect_dataset(ds)
    assert report.private_tags_dropped >= 1
    assert report.clean


def test_allowlist_and_identifying_list_do_not_overlap():
    """A tag cannot be both permitted and identifying -- that would make the
    classification ambiguous and the report meaningless."""
    assert not (ALLOWED_TAGS & KNOWN_IDENTIFYING_TAGS)


def test_non_dicom_upload_is_reported_honestly():
    report = verify_working_copy(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    assert report.clean and any("not a DICOM" in w for w in report.warnings)
