"""Canonical image-paired, patient-grouped dataset exporter (directive §12, §13).

Reads the doctor-confirmed assessments from the local database and writes a
self-describing dataset that later stages (localisation, per-bone stage
classifiers) train from. It is deliberately the *only* exporter: the report-text
pipeline (``dataset.py``) is a coverage counter, not a training set.

Guarantees that matter clinically and statistically:

* **Patient-level splits.** Every radiograph of the same child stays in ONE split
  (train / val / locked test). Crops are never split randomly. The exporter
  refuses to proceed if any patient appears in two splits (directive §12).
* **Doctor-confirmed only.** Only ``confirmed_stage`` values entered by the
  doctor are exported; superseded/rejected assessments are skipped. Nothing from
  the unreviewed report parser is included (directive §11).
* **Honest gaps.** Assessments without an attached film are exported as
  annotation-only rows (``inclusion_status='annotation_only'``) so coverage is
  still visible, but they contribute no image/crop. Crops are produced only where
  a ``localisation_box`` exists; until localisation is wired that count is 0 and
  the manifest says so — no fabricated crops.

Output layout::

    <out>/
        images/<split>/<radiograph_id>.<ext>          # immutable original copy
        normalized_images/<split>/<radiograph_id>.png  # analysis PNG
        crops/<split>/<radiograph_id>__<bone>.png      # only if a box exists
        annotations.jsonl                              # one row per (film, bone)
        patients.csv
        splits.json
        coverage.csv
        manifest.json

Run::

    python -m backend.tw3.pipeline.export_dataset --out dataset [--seed 42]
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import APP_VERSION, DB_SCHEMA_VERSION, RADIOGRAPH_DIR
from backend.models import Patient, Radiograph, TW3Assessment
from backend.tw3 import AssessmentStatus, bone_group, load_tables

# Assessments in these states are not valid current annotations to train from.
_EXCLUDED_STATUSES = frozenset({
    AssessmentStatus.SUPERSEDED.value,
    AssessmentStatus.REJECTED.value,
})

_DEFAULT_RATIOS = (0.70, 0.15, 0.15)  # train / val / test
_SPLITS = ("train", "val", "test")


class ExportError(RuntimeError):
    """Raised when the dataset cannot be exported safely (e.g. patient overlap)."""


# ── helpers ─────────────────────────────────────────────────────────────────

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _age_band(months: Optional[int]) -> str:
    """Whole-year band, e.g. 126 -> '10-11y'; None -> 'unknown'."""
    if months is None:
        return "unknown"
    y = months // 12
    return f"{y}-{y + 1}y"


def _image_domain(rg: Radiograph) -> tuple[str, str]:
    """Image domain (directive §16). Prefer the doctor-confirmed ``source_domain``;
    otherwise fall back to a value inferred from the format, clearly labelled."""
    confirmed = rg.source_domain
    if confirmed and confirmed != "unknown":
        return confirmed, "doctor_confirmed"
    fmt = (rg.source_format or "").upper()
    if fmt == "DICOM":
        return "digital_diagnostic", "inferred_from_format"
    if fmt in ("PNG", "JPEG", "BMP"):
        # Could be a PACS export, a screenshot, or a photo of film — unknown here.
        return "raster_unverified", "inferred_from_format"
    return "unknown", "unknown"


def _split_by_patient(patient_ids: list[int], seed: int,
                      ratios: tuple[float, float, float]) -> dict[int, str]:
    """Deterministically assign whole patients to splits. Returns {patient_id: split}."""
    ordered = sorted(patient_ids)
    rng = random.Random(seed)
    rng.shuffle(ordered)
    n = len(ordered)
    n_train = int(round(n * ratios[0]))
    n_val = int(round(n * ratios[1]))
    # Give the remainder to train; test gets whatever is left.
    n_train = min(n_train, n)
    n_val = min(n_val, n - n_train)
    assign: dict[int, str] = {}
    for i, pid in enumerate(ordered):
        if i < n_train:
            assign[pid] = "train"
        elif i < n_train + n_val:
            assign[pid] = "val"
        else:
            assign[pid] = "test"
    return assign


def _assert_no_patient_overlap(splits: dict[str, list[int]]) -> None:
    seen: dict[int, str] = {}
    for split, pids in splits.items():
        for pid in pids:
            if pid in seen:
                raise ExportError(
                    f"patient {pid} appears in both '{seen[pid]}' and '{split}' — "
                    "refusing to export a leaking split (directive §12)."
                )
            seen[pid] = split


def _crop_box(analysis_path: Path, box: list[float], dest: Path) -> bool:
    """Crop [x0,y0,x1,y1] (or [x,y,w,h] if the 3rd/4th look like sizes) from the
    analysis PNG. Returns True on success. Defensive: any failure returns False."""
    try:
        from PIL import Image
        if not analysis_path.exists() or not box or len(box) != 4:
            return False
        x0, y0, a, b = (float(v) for v in box)
        # Heuristic: treat as xywh when the last two are smaller than the first two
        # is unreliable; assume [x0,y0,x1,y1] unless x1<=x0 or y1<=y0.
        x1, y1 = (a, b) if (a > x0 and b > y0) else (x0 + a, y0 + b)
        with Image.open(analysis_path) as im:
            crop = im.crop((int(x0), int(y0), int(x1), int(y1)))
            if crop.width < 2 or crop.height < 2:
                return False
            dest.parent.mkdir(parents=True, exist_ok=True)
            crop.save(dest)
        return True
    except Exception:
        return False


# ── record assembly ─────────────────────────────────────────────────────────

@dataclass
class _FilmRecord:
    assessment: TW3Assessment
    patient: Patient
    radiograph: Optional[Radiograph]
    confirmed: dict[str, str]  # bone_code -> confirmed_stage (doctor-confirmed)
    boxes: dict[str, list]     # bone_code -> localisation box (if any)


def _aggregate_coverage(records: list["_FilmRecord"]) -> dict[tuple, dict]:
    """Per (stage_system, bone, stage) cell: unique patients by sex + annotation
    and image counts. Shared by the CSV export and the coverage endpoint so the
    dataset file and the dashboard never disagree (directive §13, §38)."""
    cov: dict[tuple, dict] = defaultdict(
        lambda: {"boys": set(), "girls": set(), "n_annotations": 0, "n_with_image": 0})
    for r in records:
        pid = r.patient.id
        sex = r.assessment.sex_at_birth
        has_image = bool(r.radiograph and r.radiograph.internal_file_path)
        for bone, stage in r.confirmed.items():
            c = cov[(r.assessment.stage_system, bone, stage)]
            c["boys" if sex == "boys" else "girls"].add(pid)
            c["n_annotations"] += 1
            if has_image:
                c["n_with_image"] += 1
    return cov


def _collect(db: Session) -> list[_FilmRecord]:
    rows = db.execute(select(TW3Assessment)).scalars().all()
    records: list[_FilmRecord] = []
    for a in rows:
        if a.assessment_status in _EXCLUDED_STATUSES:
            continue
        confirmed = {b.bone_code: b.confirmed_stage for b in a.bones if b.confirmed_stage}
        if not confirmed:
            continue  # nothing doctor-confirmed to export
        boxes: dict[str, list] = {}
        for b in a.bones:
            if b.localisation_box:
                try:
                    boxes[b.bone_code] = json.loads(b.localisation_box)
                except (TypeError, ValueError):
                    pass
        rg = db.get(Radiograph, a.radiograph_id) if a.radiograph_id else None
        records.append(_FilmRecord(a, a.patient, rg, confirmed, boxes))
    return records


# ── main export ──────────────────────────────────────────────────────────────

def export_dataset(db: Session, out_dir: Path, *, seed: int = 42,
                   ratios: tuple[float, float, float] = _DEFAULT_RATIOS) -> dict:
    """Export the doctor-confirmed dataset to ``out_dir``. Returns the manifest dict."""
    if abs(sum(ratios) - 1.0) > 1e-6:
        raise ExportError(f"split ratios must sum to 1.0, got {ratios}")

    out_dir = Path(out_dir)
    records = _collect(db)
    if not records:
        raise ExportError(
            "no doctor-confirmed assessments to export. Stage at least one bone "
            "and save an assessment first."
        )

    # Patient-level split over every patient that has a confirmed annotation.
    patient_ids = sorted({r.patient.id for r in records})
    assignment = _split_by_patient(patient_ids, seed, ratios)
    splits: dict[str, list[int]] = {s: [] for s in _SPLITS}
    for pid, split in assignment.items():
        splits[split].append(pid)
    for s in splits:
        splits[s].sort()
    _assert_no_patient_overlap(splits)

    # Fresh output tree.
    if out_dir.exists():
        shutil.rmtree(out_dir)
    for sub in ("images", "normalized_images", "crops"):
        for s in _SPLITS:
            (out_dir / sub / s).mkdir(parents=True, exist_ok=True)

    tables = load_tables()
    scoring_table_version = tables.version
    scoring_table_checksum = tables.raw.get("checksum")
    export_ts = _utcnow_iso()

    annotations: list[dict] = []
    patient_stats: dict[int, dict] = {
        pid: {"assessments": 0, "radiographs": set(), "confirmed_bones": 0}
        for pid in patient_ids
    }
    n_images = n_crops = 0

    for r in records:
        pid = r.patient.id
        split = assignment[pid]
        stats = patient_stats[pid]
        stats["assessments"] += 1
        stats["confirmed_bones"] += len(r.confirmed)

        has_image = bool(r.radiograph and r.radiograph.internal_file_path)
        image_rel = norm_rel = None
        domain, domain_src = ("none", "no_radiograph")

        if has_image:
            rg = r.radiograph
            stats["radiographs"].add(rg.id)
            domain, domain_src = _image_domain(rg)
            src_dir = RADIOGRAPH_DIR / str(rg.id)
            analysis = src_dir / "analysis.png"
            if analysis.exists():
                norm_rel = f"normalized_images/{split}/{rg.id}.png"
                shutil.copy2(analysis, out_dir / norm_rel)
                n_images += 1
            original = Path(rg.internal_file_path)
            if original.exists():
                image_rel = f"images/{split}/{rg.id}{original.suffix}"
                shutil.copy2(original, out_dir / image_rel)

        inclusion = "included" if has_image else "annotation_only"
        exclusion_reason = None if has_image else "no_radiograph"
        sex = r.assessment.sex_at_birth

        for bone, stage in r.confirmed.items():
            grp = bone_group(bone)
            box = r.boxes.get(bone)
            crop_rel = None
            if has_image and box:
                analysis = RADIOGRAPH_DIR / str(r.radiograph.id) / "analysis.png"
                candidate = out_dir / f"crops/{split}/{r.radiograph.id}__{bone}.png"
                if _crop_box(analysis, box, candidate):
                    crop_rel = f"crops/{split}/{r.radiograph.id}__{bone}.png"
                    n_crops += 1

            annotations.append({
                "image_hash": r.radiograph.image_hash if has_image else None,
                "patient_group_id": pid,
                "source_assessment_id": r.assessment.id,
                "radiograph_id": r.radiograph.id if has_image else None,
                "split": split,
                "stage_system": r.assessment.stage_system,
                "bone_code": bone,
                "bone_group": grp,
                "confirmed_stage": stage,
                "bounding_box": box,
                "sex": sex,
                "chronological_age_months": r.assessment.chronological_age_months,
                "age_band": _age_band(r.assessment.chronological_age_months),
                "image_domain": domain,
                "image_domain_source": domain_src,
                "inclusion_status": inclusion,
                "exclusion_reason": exclusion_reason,
                "review_status": r.assessment.assessment_status,
                "annotation_version": APP_VERSION,
                "scoring_table_version": scoring_table_version,
                "image_path": image_rel,
                "normalized_image_path": norm_rel,
                "crop_path": crop_rel,
                "export_timestamp": export_ts,
            })

    # ── write annotations.jsonl ──
    with (out_dir / "annotations.jsonl").open("w", encoding="utf-8") as fh:
        for row in annotations:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    # ── patients.csv ──
    with (out_dir / "patients.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["patient_group_id", "patient_code", "sex", "split",
                    "n_assessments", "n_radiographs", "n_confirmed_bones"])
        for pid in patient_ids:
            p = next(r.patient for r in records if r.patient.id == pid)
            st = patient_stats[pid]
            w.writerow([pid, p.patient_code, p.sex_at_birth, assignment[pid],
                        st["assessments"], len(st["radiographs"]), st["confirmed_bones"]])

    # ── coverage.csv (directive §13 matrix) ──
    coverage = _aggregate_coverage(records)
    with (out_dir / "coverage.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["stage_system", "bone_code", "bone_group", "stage",
                    "unique_boys", "unique_girls", "n_annotations", "n_with_image"])
        for (system, bone, stage), c in sorted(coverage.items()):
            w.writerow([system, bone, bone_group(bone), stage,
                        len(c["boys"]), len(c["girls"]), c["n_annotations"], c["n_with_image"]])

    # ── consensus.json (multi-rater agreement, directive §quality gate) ──
    # Where the SAME film has ≥2 independent reads, reduce them to a per-bone
    # majority label + list the bones that disagree (adjudication). Additive: the
    # per-assessment annotations above are untouched; this is the training-grade view.
    from backend.tw3.consensus import build_film_consensus
    film_reads = [{"radiograph_id": r.radiograph.id if r.radiograph else None,
                   "stage_system": r.assessment.stage_system,
                   "stages": r.confirmed} for r in records]
    consensus_summary = build_film_consensus(film_reads)
    (out_dir / "consensus.json").write_text(
        json.dumps(consensus_summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── splits.json ──
    (out_dir / "splits.json").write_text(
        json.dumps({s: splits[s] for s in _SPLITS}, indent=2), encoding="utf-8")

    # ── manifest.json ──
    manifest = {
        "export_timestamp": export_ts,
        "app_version": APP_VERSION,
        "db_schema_version": DB_SCHEMA_VERSION,
        "scoring_table_version": scoring_table_version,
        "scoring_table_checksum": scoring_table_checksum,
        "seed": seed,
        "split_ratios": {"train": ratios[0], "val": ratios[1], "test": ratios[2]},
        "counts": {
            "patients": len(patient_ids),
            "assessments": len(records),
            "annotations": len(annotations),
            "normalized_images": n_images,
            "crops": n_crops,
            "per_split_patients": {s: len(splits[s]) for s in _SPLITS},
            "multireader_films": consensus_summary["n_multireader_films"],
            "films_needing_adjudication": consensus_summary["films_needing_adjudication"],
        },
        "stage_systems_present": sorted({r.assessment.stage_system for r in records}),
        "notes": [
            "Patient-level splits — no child appears in two splits.",
            "Only doctor-confirmed stages are exported; superseded/rejected are skipped.",
            ("No crops produced: localisation boxes are not yet wired. Crops appear "
             "here automatically once bone boxes are stored." if n_crops == 0 else
             f"{n_crops} crops produced from stored localisation boxes."),
            "image_domain is the doctor-confirmed source_domain where set, else "
            "inferred from format (see image_domain_source); treat "
            "digital/compressed/film-photo separately for evaluation (§16).",
            ("consensus.json: no film has ≥2 independent reads yet, so no consensus "
             "label was formed — it fills automatically once multiple raters stage the "
             "same film." if consensus_summary["n_multireader_films"] == 0 else
             f"consensus.json: {consensus_summary['n_multireader_films']} multi-reader "
             f"film(s); {consensus_summary['films_needing_adjudication']} have bones "
             "needing adjudication."),
        ],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


# ── coverage dashboard (directive §13) ───────────────────────────────────────

def _support_level(n_unique_patients: int) -> str:
    """Engineering readiness bands for when AI suggestions may be considered
    (directive §13 — these are NOT proof of clinical validity)."""
    if n_unique_patients >= 50:
        return "candidate"
    if n_unique_patients >= 25:
        return "limited"
    if n_unique_patients >= 10:
        return "experimental"
    if n_unique_patients >= 1:
        return "minimal"
    return "empty"


def coverage_report(db: Session) -> dict:
    """Live per-bone×stage coverage matrix computed from the DB — no files written.
    Same aggregation as coverage.csv, so the dashboard matches the exported dataset."""
    records = _collect(db)
    agg = _aggregate_coverage(records)
    cells: list[dict] = []
    per_system: dict[str, dict] = defaultdict(
        lambda: {"cells": 0, "annotations": 0, "patients": set(), "bones": set()})
    for (system, bone, stage), c in sorted(agg.items()):
        ub, ug = len(c["boys"]), len(c["girls"])
        cells.append({
            "stage_system": system, "bone_code": bone, "bone_group": bone_group(bone),
            "stage": stage, "unique_boys": ub, "unique_girls": ug, "unique_total": ub + ug,
            "n_annotations": c["n_annotations"], "n_with_image": c["n_with_image"],
            "support": _support_level(ub + ug),
        })
        s = per_system[system]
        s["cells"] += 1
        s["annotations"] += c["n_annotations"]
        s["bones"].add(bone)
        s["patients"].update(c["boys"])
        s["patients"].update(c["girls"])
    summary = {sys: {"cells_covered": v["cells"], "annotations": v["annotations"],
                     "unique_patients": len(v["patients"]), "bones_touched": len(v["bones"])}
               for sys, v in per_system.items()}
    return {
        "generated_at": _utcnow_iso(),
        "n_assessments": len(records),
        "n_patients": len({r.patient.id for r in records}),
        "cells": cells,
        "summary": summary,
        "thresholds": {"experimental": 10, "limited": 25, "candidate": 50},
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse

    from backend.db import init_db, session_scope

    ap = argparse.ArgumentParser(description="Export the doctor-confirmed TW3 dataset")
    ap.add_argument("--out", default="dataset", help="output directory (default: dataset/)")
    ap.add_argument("--seed", type=int, default=42, help="split seed (default: 42)")
    ap.add_argument("--train", type=float, default=_DEFAULT_RATIOS[0])
    ap.add_argument("--val", type=float, default=_DEFAULT_RATIOS[1])
    ap.add_argument("--test", type=float, default=_DEFAULT_RATIOS[2])
    args = ap.parse_args()

    init_db()
    try:
        with session_scope() as db:
            manifest = export_dataset(
                db, Path(args.out), seed=args.seed,
                ratios=(args.train, args.val, args.test))
    except ExportError as exc:
        raise SystemExit(f"export refused: {exc}")

    c = manifest["counts"]
    print(f"Dataset written to: {Path(args.out).resolve()}")
    print(f"  patients   : {c['patients']}  (train/val/test "
          f"{c['per_split_patients']['train']}/{c['per_split_patients']['val']}/"
          f"{c['per_split_patients']['test']})")
    print(f"  assessments: {c['assessments']}")
    print(f"  annotations: {c['annotations']}")
    print(f"  normalized images: {c['normalized_images']}   crops: {c['crops']}")
    for note in manifest["notes"]:
        print(f"  · {note}")


if __name__ == "__main__":
    main()
