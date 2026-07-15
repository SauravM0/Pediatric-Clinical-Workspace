"""Access to the local RSNA bone-age datasets for validation (PLAN-0 Phase C).

The RSNA challenge ships disjoint sets: a TRAINING set (12,611 images — used to
train, tune, and conformally-calibrate the shipped model) and a separate
VALIDATION set (1,425 images) the model never saw. The validation set is therefore
a clean, truly held-out LOCKED INTERNAL TEST (Plan 5 WI-1). The large image dirs
are gitignored; every path is overridable by env for a different machine.
"""
from __future__ import annotations

import csv
import hashlib
import os
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[3]

VAL_DIR = Path(os.environ.get("RSNA_VAL_DIR", APP_ROOT / "Bone Age Validation Set"))
VAL_CSV = Path(os.environ.get("RSNA_VAL_CSV", VAL_DIR / "Validation Dataset.csv"))
TRAIN_CSV = Path(os.environ.get("RSNA_TRAIN_CSV", APP_ROOT / "archive" / "boneage-training-dataset.csv"))
TRAIN_DIR = Path(os.environ.get("RSNA_DATA_DIR", APP_ROOT / "Bone+Age+Training+Set" / "boneage-training-dataset"))


def data_available() -> bool:
    return VAL_CSV.exists() and VAL_DIR.exists()


def _index_images(root: Path) -> dict[str, Path]:
    return {p.stem: p for p in root.rglob("*.png")}


def read_validation_labels() -> list[dict]:
    """``[{id, is_male, age_months, path}]`` for the held-out RSNA validation set."""
    if not VAL_CSV.exists():
        raise FileNotFoundError(f"RSNA validation CSV not found: {VAL_CSV}")
    files = _index_images(VAL_DIR)
    out: list[dict] = []
    with open(VAL_CSV, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rid = str(row["Image ID"]).strip()
            path = files.get(rid)
            if path is None:
                continue
            out.append({
                "id": rid,
                "is_male": str(row["male"]).strip().lower() in ("true", "1", "yes", "m"),
                "age_months": float(row["Bone Age (months)"]),
                "path": path,
            })
    return out


def read_training_ids() -> set[str]:
    """Training subject ids (off-limits to the locked test). CSV first, else image dir."""
    if TRAIN_CSV.exists():
        with open(TRAIN_CSV, newline="", encoding="utf-8-sig") as f:
            r = csv.DictReader(f)
            col = "id" if r.fieldnames and "id" in r.fieldnames else (r.fieldnames or ["id"])[0]
            return {str(row[col]).strip() for row in r}
    if TRAIN_DIR.exists():
        return {p.stem for p in TRAIN_DIR.rglob("*.png")}
    return set()


def content_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
