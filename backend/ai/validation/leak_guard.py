"""Frozen test-set registry + cross-artifact leak guard (Plan 5 WI-1).

Every validation number is meaningless if the test set leaked into training. This
module is the single source of truth for what is off-limits to training/tuning/
feedback/calibration, and the guard that REFUSES to evaluate on any overlap --
by patient AND by image hash (validation_protocol.md §3: split by patient, keep a
fully external test set, never let a child appear in two splits).

The registry is checksum-locked (same canonical SHA-256 as the TW3 tables) so a
frozen test set cannot be silently edited. Pure JSON + set math -- no DB, no model.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from backend.tw3 import compute_checksum  # one canonical checksum across the product

_REGISTRY_PATH = Path(__file__).with_name("locked_test.json")

# The RSNA carve owns the unsuffixed filename because it was frozen first and is
# referenced by that name; every other dataset gets its own file.
RSNA_DATASET_PREFIX = "rsna-"


def registry_path(dataset: str) -> Path:
    """Where a given dataset's frozen registry lives.

    One file per dataset, because there is more than one frozen test set: the
    RSNA locked test and the local Indian dual-read cohort answer different
    questions and must both survive. Before this, both carves called
    save_registry with no path, so freezing the local cohort OVERWROTE the RSNA
    registry -- destroying the record of 1,425 held-out images, and leaving every
    later leak check to pass vacuously against the wrong set.
    """
    if not dataset or dataset.startswith(RSNA_DATASET_PREFIX):
        return _REGISTRY_PATH
    slug = "".join(c if c.isalnum() else "_" for c in dataset.lower()).strip("_")
    return _REGISTRY_PATH.with_name(f"locked_test_{slug}.json")


class LeakError(RuntimeError):
    """Raised when a test set overlaps a training/tuning/feedback/calibration set."""


class RegistryError(ValueError):
    """Raised when the frozen test registry is malformed or checksum-altered."""


@dataclass(frozen=True)
class TestRegistry:
    dataset: str
    source: str                        # e.g. "internal-rsna" | "external-india" | "TEMPLATE"
    frozen_at: str
    patient_ids: frozenset             # str-normalised
    image_hashes: frozenset            # str-normalised
    checksum_verified: bool
    raw: dict = field(repr=False, default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not (self.patient_ids or self.image_hashes)


def _norm(vals: Optional[Iterable[Any]]) -> frozenset:
    return frozenset(str(v) for v in (vals or []) if v is not None and str(v) != "")


def build_from_dict(data: Mapping[str, Any]) -> TestRegistry:
    """Validate a registry dict and verify its checksum if present."""
    if not isinstance(data, Mapping):
        raise RegistryError("registry must be a JSON object")
    for key in ("patient_ids", "image_hashes"):
        if key in data and not isinstance(data[key], list):
            raise RegistryError(f"'{key}' must be a list")

    stored = data.get("checksum")
    checksum_verified = False
    if stored:
        actual = compute_checksum(dict(data))
        if actual != stored:
            raise RegistryError(
                "locked-test registry checksum mismatch -- the frozen test set has "
                "been altered since it was locked. Refusing to use it. "
                f"(expected {str(stored)[:12]}..., got {actual[:12]}...)"
            )
        checksum_verified = True

    return TestRegistry(
        dataset=str(data.get("dataset", "")),
        source=str(data.get("source", "")),
        frozen_at=str(data.get("frozen_at", "")),
        patient_ids=_norm(data.get("patient_ids")),
        image_hashes=_norm(data.get("image_hashes")),
        checksum_verified=checksum_verified,
        raw=dict(data),
    )


def load_registry(path: Path = _REGISTRY_PATH) -> TestRegistry:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistryError(f"locked-test registry not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RegistryError(f"locked-test registry is not valid JSON: {exc}") from exc
    return build_from_dict(data)


def save_registry(patient_ids: Iterable[Any], image_hashes: Iterable[Any], *,
                  dataset: str, source: str, path: Optional[Path] = None,
                  allow_replace: bool = False) -> TestRegistry:
    """Freeze a test set: write a checksum-locked registry. Sorted for reproducibility.

    Defaults to this dataset's own file (:func:`registry_path`) rather than to a
    single shared one, and REFUSES to write over a registry that belongs to a
    different dataset. The checksum lock exists so a frozen set cannot be
    silently edited; overwriting the whole file would have walked straight past
    it, which is exactly what happened when both carves shared a default path.
    """
    path = Path(path) if path is not None else registry_path(dataset)
    if path.exists() and not allow_replace:
        try:
            existing = load_registry(path)
        except RegistryError:
            existing = None
        if existing is not None and existing.dataset and existing.dataset != dataset:
            raise RegistryError(
                f"{path.name} already holds the frozen registry for "
                f"{existing.dataset!r} ({len(existing.patient_ids)} patients, frozen "
                f"{existing.frozen_at}). Refusing to overwrite it with {dataset!r} -- "
                "a frozen test set is the record of what is off-limits to training, "
                "and replacing it makes every later leak check pass vacuously. "
                "Pass allow_replace=True only for a deliberate re-carve."
            )

    data = {
        "dataset": dataset,
        "source": source,
        "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "patient_ids": sorted({str(v) for v in patient_ids if str(v)}),
        "image_hashes": sorted({str(v) for v in image_hashes if str(v)}),
    }
    data["checksum"] = compute_checksum(data)
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return build_from_dict(data)


def assert_disjoint(test: TestRegistry, others: Mapping[str, Mapping[str, Iterable[Any]]]) -> None:
    """Refuse if ``test`` shares any patient id or image hash with any other set.

    ``others``: ``{"train": {"patient_ids": [...], "image_hashes": [...]}, "val": {...},
    "feedback": {...}, "calibration": {...}}``. Raises :class:`LeakError` naming the
    first offending set and the overlapping ids -- evaluation must not proceed on a
    leaked test set.
    """
    for name, sets in (others or {}).items():
        pid_overlap = test.patient_ids & _norm((sets or {}).get("patient_ids"))
        hash_overlap = test.image_hashes & _norm((sets or {}).get("image_hashes"))
        if pid_overlap or hash_overlap:
            detail = []
            if pid_overlap:
                detail.append(f"patients {sorted(pid_overlap)[:5]}")
            if hash_overlap:
                detail.append(f"image_hashes {sorted(hash_overlap)[:5]}")
            raise LeakError(
                f"locked test set leaks into '{name}': {'; '.join(detail)}. "
                "Refusing to evaluate on a leaked test set (validation_protocol.md §3)."
            )
