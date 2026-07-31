"""DICOM de-identification, verified against an explicit allowlist (C.4).

``radiograph_service.attach_image`` stamps every upload
``anonymisation_status="working_copy_deidentified"``. That was an *assertion*,
not a check: nothing confirmed the derived files carry no identifying metadata.
The claim happened to be true -- ``imaging._load_dicom`` reads pixels and four
tags, then writes a plain PNG, so DICOM headers cannot survive -- but a claim
that nothing tests is a claim that quietly stops being true. This module makes
it checkable, and ``tests/security/test_dicom_deid.py`` enforces it.

The model is an ALLOWLIST, not a blocklist. DICOM has thousands of tags, private
vendor blocks can hold anything, and burned-in text is not a tag at all; a
blocklist of "the identifying ones" is a list of the ones somebody thought of.
So: enumerate the few fields the application is permitted to retain, and treat
every other tag as identifying by default.

Note what this does NOT do: pixel data can contain **burned-in identifiers** --
name and date rendered into the image by the modality. No tag inspection finds
those. ``BurnedInAnnotation`` is reported when present so a human can act on it,
and the limitation is stated rather than papered over.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# The only DICOM elements the working copy is allowed to retain. Each is either
# a technical property needed to interpret the image, or a coarse date already
# implied by the clinical record.
ALLOWED_TAGS: frozenset[str] = frozenset({
    "Modality",             # 'CR'/'DX' -- needed to sanity-check the upload
    "ImageLaterality",      # left/right -- a real safety check (wrong hand)
    "Laterality",
    "StudyDate",            # when the film was taken; clinically necessary
    "BitsStored",           # decode parameter
    "PhotometricInterpretation",
    "Rows", "Columns",
    "PixelSpacing", "ImagerPixelSpacing",
    "BurnedInAnnotation",   # retained precisely so it can be WARNED about
})

# Tags whose presence means the source file carried a direct identifier. Used
# only for reporting what was DROPPED -- the allowlist above is the control.
KNOWN_IDENTIFYING_TAGS: frozenset[str] = frozenset({
    "PatientName", "PatientID", "PatientBirthDate", "PatientAddress",
    "PatientTelephoneNumbers", "PatientMotherBirthName", "OtherPatientIDs",
    "OtherPatientNames", "ReferringPhysicianName", "PerformingPhysicianName",
    "OperatorsName", "InstitutionName", "InstitutionAddress",
    "InstitutionalDepartmentName", "StationName", "AccessionNumber",
    "StudyID", "StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID",
    "IssuerOfPatientID", "MilitaryRank", "EthnicGroup", "Occupation",
    "PatientComments", "AdditionalPatientHistory", "RequestingPhysician",
})


@dataclass
class DeidReport:
    """What a working copy retained, dropped, and could not vouch for."""

    retained: dict[str, Any] = field(default_factory=dict)
    dropped_identifying: list[str] = field(default_factory=list)
    dropped_other: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    private_tags_dropped: int = 0

    @property
    def clean(self) -> bool:
        """True when nothing outside the allowlist was retained."""
        return not set(self.retained) - ALLOWED_TAGS

    def to_dict(self) -> dict[str, Any]:
        return {
            "clean": self.clean,
            "retained": sorted(self.retained),
            "dropped_identifying": sorted(self.dropped_identifying),
            "dropped_other_count": len(self.dropped_other),
            "private_tags_dropped": self.private_tags_dropped,
            "warnings": list(self.warnings),
            "limitation": (
                "Tag-level only. Burned-in identifiers rendered into the pixel "
                "data cannot be detected here and require a human check."
            ),
        }


def inspect_dataset(ds) -> DeidReport:
    """Classify every element of a pydicom Dataset against the allowlist."""
    report = DeidReport()
    for element in ds:
        if element.tag.is_private:
            report.private_tags_dropped += 1
            continue
        keyword = element.keyword or str(element.tag)
        if keyword == "PixelData":
            continue
        if keyword in ALLOWED_TAGS:
            report.retained[keyword] = getattr(ds, keyword, None)
        elif keyword in KNOWN_IDENTIFYING_TAGS:
            report.dropped_identifying.append(keyword)
        else:
            report.dropped_other.append(keyword)

    if str(report.retained.get("BurnedInAnnotation", "")).upper() == "YES":
        report.warnings.append(
            "BurnedInAnnotation=YES: the image itself may show the patient's "
            "name or ID. Review before sharing or using for training."
        )
    return report


def verify_working_copy(raw: bytes) -> DeidReport:
    """Verify what a stored working copy actually retains.

    Given the ORIGINAL upload bytes, reports what the derived analysis image can
    possibly carry. The derived file is a plain grayscale PNG written from a
    numpy array (imaging.store_radiograph), so no DICOM element survives into it
    -- this quantifies what was therefore dropped, and flags burned-in risk.
    """
    import pydicom

    from backend.imaging import _looks_like_dicom

    if not _looks_like_dicom(raw):
        rep = DeidReport()
        rep.warnings.append("not a DICOM file; no tag-level metadata to drop")
        return rep

    ds = pydicom.dcmread(__import__("io").BytesIO(raw), force=True, stop_before_pixels=True)
    return inspect_dataset(ds)
