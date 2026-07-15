"""Freeze the RSNA validation set as the checksum-locked internal test
(Plan 5 WI-1 / PLAN-0 C1).

Writes ``locked_test.json`` (subject ids + image content hashes + a canonical
SHA-256) and REFUSES if it overlaps the training set — the cross-artifact leak
guard (validation_protocol.md §3). The frozen registry is then the single source
of truth for what is off-limits to training/tuning/feedback/calibration.

Run once (regenerate only deliberately):
    python -m backend.ai.validation.carve_locked_test
"""
from __future__ import annotations

from . import rsna_data
from .leak_guard import assert_disjoint, save_registry

DATASET = "rsna-bone-age-validation-2017 (1425 held-out images)"
SOURCE = "internal-rsna"


def carve() -> dict:
    """Freeze the locked test and prove it is disjoint from training. Returns a summary."""
    labels = rsna_data.read_validation_labels()
    if not labels:
        raise SystemExit("no RSNA validation images resolved — check the dataset paths")
    ids = [r["id"] for r in labels]
    hashes = [rsna_data.content_sha256(r["path"]) for r in labels]

    reg = save_registry(ids, hashes, dataset=DATASET, source=SOURCE)

    # Cross-artifact leak guard: the locked test must not overlap the training set
    # (the model's train/tune/calibration data). Raises LeakError on any overlap.
    train_ids = rsna_data.read_training_ids()
    assert_disjoint(reg, {"train": {"patient_ids": train_ids}})

    return {"n_images": len(ids), "n_unique_hashes": len(set(hashes)),
            "checksum_verified": reg.checksum_verified,
            "disjoint_from_train_ids": len(train_ids)}


def main() -> int:
    if not rsna_data.data_available():
        print("RSNA validation data not present — cannot carve the locked test.")
        print(f"  looked for: {rsna_data.VAL_CSV}")
        return 1
    r = carve()
    print(f"Locked test frozen: {r['n_images']} images "
          f"({r['n_unique_hashes']} unique content hashes), "
          f"checksum_verified={r['checksum_verified']}, "
          f"disjoint from {r['disjoint_from_train_ids']} training ids.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
