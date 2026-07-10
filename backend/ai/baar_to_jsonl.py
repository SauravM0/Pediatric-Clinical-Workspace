"""Convert BAAR / BoNet RSNA hand keypoints → the localizer's training JSONL.

BoNet (Escobar et al., "Hand Pose Estimation for Pediatric Bone Age Assessment",
MICCAI 2019; BCV-Uniandes) ships manually-annotated keypoints for the public RSNA
hand radiographs, downloadable from the BAAR platform
(https://bcv-uniandes.github.io/baar-wp/). ``train_localizer.py`` wants, per image:

    {"image": "<file.png>", "points": [[x,y] | null, ... 13 in RUS_BONES order ...]}

with points in ORIGINAL image pixels. This script parses the BoNet annotations and
maps each annotated landmark to one of the 13 RUS bone centres.

──────────────────────────────────────────────────────────────────────────────
IMPORTANT — you MUST verify the mapping before trusting the output.
The keypoint *index → anatomical location* ordering depends on the exact BoNet
release you downloaded, and is NOT assumed here. Steps:

  1. python -m backend.ai.baar_to_jsonl --inspect --ann <bonet_ann.json>
       → prints how many keypoints each record has + a sample, so you can see the
         indexing.
  2. Edit LANDMARK_TO_BONE below to map each RUS bone to the right keypoint index
     (or a (i, j) pair whose MIDPOINT is the bone centre).
  3. python -m backend.ai.baar_to_jsonl --preview 8 --ann <ann> --images <dir> \
         --out-preview /tmp/loc_preview
       → writes 8 overlay PNGs; open them and confirm each dot sits on the bone.
  4. Only then generate the full set:
     python -m backend.ai.baar_to_jsonl --ann <ann> --out keypoints.jsonl

The pure parse→map→JSONL logic has a self-test: python -m backend.ai.baar_to_jsonl --selftest
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Optional, Union

from backend.tw3 import RUS_BONES

# ── THE ONE THING YOU MUST SET (see header) ──────────────────────────────────
# Map each RUS bone code → the BoNet keypoint INDEX that marks its centre, OR a
# (i, j) tuple whose midpoint is used, OR None to leave that bone unlabelled
# (unlabelled bones are written as null and skipped in the localizer's loss, which
# is fine — a partial mapping still trains the bones you did map).
#
# Values below are PLACEHOLDERS (all None). Fill them after --inspect / --preview.
# Do NOT guess: a wrong index trains the model to point at the wrong bone.
Mapping = Union[int, tuple, None]
LANDMARK_TO_BONE: dict[str, Mapping] = {
    "radius": None, "ulna": None,
    "mc1": None, "mc3": None, "mc5": None,
    "pp1": None, "pp3": None, "pp5": None,
    "mp3": None, "mp5": None,
    "dp1": None, "dp3": None, "dp5": None,
}


# ── annotation parsing (format-agnostic) ─────────────────────────────────────

def _kps_from_coco(data: dict) -> dict[str, list[Optional[tuple]]]:
    """COCO-style: images[].file_name/id, annotations[].image_id/keypoints
    (flat [x,y,v, x,y,v, ...]; v==0 → not labelled). Returns {file_name: [(x,y)|None,...]}."""
    id_to_name = {img["id"]: img.get("file_name") or img.get("filename")
                  for img in data.get("images", [])}
    out: dict[str, list[Optional[tuple]]] = {}
    for ann in data.get("annotations", []):
        name = id_to_name.get(ann.get("image_id"))
        if not name:
            continue
        flat = ann.get("keypoints") or []
        pts: list[Optional[tuple]] = []
        for i in range(0, len(flat), 3):
            x, y, v = flat[i], flat[i + 1], flat[i + 2] if i + 2 < len(flat) else 1
            pts.append((float(x), float(y)) if v and (x or y) else None)
        # if multiple annotations per image, keep the first (or extend to merge)
        out.setdefault(name, pts)
    return out


def _kps_from_records(rows: list) -> dict[str, list[Optional[tuple]]]:
    """Generic list-of-records: each has an image name and a 'keypoints' list of
    [x,y] pairs (or flat triplets). Returns {name: [(x,y)|None,...]}."""
    out: dict[str, list[Optional[tuple]]] = {}
    for rec in rows:
        name = rec.get("image") or rec.get("file_name") or rec.get("filename")
        if not name:
            continue
        kp = rec.get("keypoints") or rec.get("points") or []
        pts: list[Optional[tuple]] = []
        if kp and isinstance(kp[0], (list, tuple)):          # [[x,y],...] or [[x,y,v],...]
            for p in kp:
                if p and p[0] is not None and (len(p) < 3 or p[2]):
                    pts.append((float(p[0]), float(p[1])))
                else:
                    pts.append(None)
        else:                                                # flat [x,y,v,...]
            for i in range(0, len(kp), 3):
                x, y = kp[i], kp[i + 1]
                v = kp[i + 2] if i + 2 < len(kp) else 1
                pts.append((float(x), float(y)) if v and (x or y) else None)
        out.setdefault(name, pts)
    return out


def _kps_from_csv(path: Path) -> dict[str, list[Optional[tuple]]]:
    """CSV with a filename column + paired coordinate columns named '<i>_x','<i>_y'
    (i = 0..N-1). Missing/blank cells → None for that landmark."""
    out: dict[str, list[Optional[tuple]]] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        cols = reader.fieldnames or []
        idxs = sorted({int(c[:-2]) for c in cols if c.endswith("_x") and c[:-2].isdigit()})
        name_col = next((c for c in ("image", "file_name", "filename", "name") if c in cols), cols[0])
        for row in reader:
            pts: list[Optional[tuple]] = []
            for i in idxs:
                xs, ys = row.get(f"{i}_x", ""), row.get(f"{i}_y", "")
                pts.append((float(xs), float(ys)) if xs not in ("", None) and ys not in ("", None) else None)
            out[row[name_col]] = pts
    return out


def load_keypoints(ann_path: Path) -> dict[str, list[Optional[tuple]]]:
    """Load BoNet keypoints from JSON (COCO or record list) or CSV → {name: [pts]}."""
    if ann_path.suffix.lower() == ".csv":
        return _kps_from_csv(ann_path)
    data = json.loads(ann_path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "annotations" in data:
        return _kps_from_coco(data)
    if isinstance(data, list):
        return _kps_from_records(data)
    if isinstance(data, dict):                               # {name: [pts]} already
        return {k: [tuple(p) if p else None for p in v] for k, v in data.items()}
    raise SystemExit(f"unrecognised annotation structure in {ann_path}")


# ── landmark → RUS bone centre ───────────────────────────────────────────────

def _bone_point(landmarks: list[Optional[tuple]], spec: Mapping) -> Optional[list]:
    """Resolve one bone's centre from the landmark list per its LANDMARK_TO_BONE spec."""
    if spec is None:
        return None
    if isinstance(spec, int):
        p = landmarks[spec] if 0 <= spec < len(landmarks) else None
        return [round(p[0], 1), round(p[1], 1)] if p else None
    if isinstance(spec, (tuple, list)) and len(spec) == 2:   # midpoint of two landmarks
        i, j = spec
        a = landmarks[i] if 0 <= i < len(landmarks) else None
        b = landmarks[j] if 0 <= j < len(landmarks) else None
        if a and b:
            return [round((a[0] + b[0]) / 2, 1), round((a[1] + b[1]) / 2, 1)]
        return None
    raise ValueError(f"bad mapping spec {spec!r}")


def to_rus_points(landmarks: list[Optional[tuple]]) -> list[Optional[list]]:
    """Landmark list → 13 points in RUS_BONES order (null where unmapped/missing)."""
    return [_bone_point(landmarks, LANDMARK_TO_BONE[b]) for b in RUS_BONES]


def convert(ann_path: Path, out_path: Path, images_dir: Optional[Path] = None) -> dict:
    """Write the localizer JSONL. Returns simple stats. Skips images that resolve to
    zero mapped points (nothing to learn from), and — if images_dir is given — images
    whose file is missing on disk."""
    kps = load_keypoints(ann_path)
    n_written = n_empty = n_missing_file = 0
    per_bone = {b: 0 for b in RUS_BONES}
    with open(out_path, "w", encoding="utf-8") as fh:
        for name, landmarks in kps.items():
            if images_dir and not (images_dir / name).exists():
                n_missing_file += 1
                continue
            pts = to_rus_points(landmarks)
            if not any(p for p in pts):
                n_empty += 1
                continue
            for b, p in zip(RUS_BONES, pts):
                if p:
                    per_bone[b] += 1
            fh.write(json.dumps({"image": name, "points": pts}) + "\n")
            n_written += 1
    return {"written": n_written, "empty_skipped": n_empty,
            "missing_file_skipped": n_missing_file, "per_bone": per_bone,
            "mapped_bones": [b for b in RUS_BONES if LANDMARK_TO_BONE[b] is not None]}


# ── inspection / preview / self-test ─────────────────────────────────────────

def inspect(ann_path: Path, n: int = 3) -> None:
    kps = load_keypoints(ann_path)
    counts = {len(v) for v in kps.values()}
    print(f"{len(kps)} images · keypoints-per-image seen: {sorted(counts)}")
    mapped = [b for b in RUS_BONES if LANDMARK_TO_BONE[b] is not None]
    print(f"LANDMARK_TO_BONE currently maps {len(mapped)}/13 bones: {mapped or '(none — edit the file)'}")
    for name, lm in list(kps.items())[:n]:
        shown = [f"{i}:({p[0]:.0f},{p[1]:.0f})" if p else f"{i}:·" for i, p in enumerate(lm)]
        print(f"  {name}: {' '.join(shown)}")


def preview(ann_path: Path, images_dir: Path, out_dir: Path, n: int = 8) -> None:
    """Overlay mapped bone points on n images so the mapping can be eyeballed."""
    from PIL import Image, ImageDraw  # lazy: only needed here
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    kps = load_keypoints(ann_path)
    done = 0
    for name, lm in kps.items():
        src = images_dir / name
        if not src.exists():
            continue
        pts = to_rus_points(lm)
        if not any(pts):
            continue
        img = Image.open(src).convert("RGB")
        d = ImageDraw.Draw(img)
        for b, p in zip(RUS_BONES, pts):
            if p:
                x, y = p
                d.ellipse([x - 6, y - 6, x + 6, y + 6], outline=(255, 0, 0), width=3)
                d.text((x + 8, y - 6), b, fill=(255, 0, 0))
        img.save(out_dir / f"preview_{name}.png")
        done += 1
        if done >= n:
            break
    print(f"wrote {done} preview image(s) to {out_dir} — confirm every dot sits on its bone")


def _selftest() -> None:
    """Pure logic check (no PIL/torch): synthetic COCO → correct JSONL rows."""
    global LANDMARK_TO_BONE
    saved = dict(LANDMARK_TO_BONE)
    try:
        # map radius→kp0, ulna→kp1, mc3→midpoint(kp2,kp3); leave the rest None
        LANDMARK_TO_BONE.update({b: None for b in RUS_BONES})
        LANDMARK_TO_BONE["radius"] = 0
        LANDMARK_TO_BONE["ulna"] = 1
        LANDMARK_TO_BONE["mc3"] = (2, 3)
        coco = {
            "images": [{"id": 7, "file_name": "7.png"}],
            "annotations": [{"image_id": 7, "keypoints": [10, 20, 1, 30, 40, 2, 0, 0, 1, 100, 100, 1]}],
        }
        lm = _kps_from_coco(coco)["7.png"]
        assert lm[0] == (10.0, 20.0) and lm[1] == (30.0, 40.0) and lm[2] is None, lm
        pts = to_rus_points(lm)
        assert pts[RUS_BONES.index("radius")] == [10.0, 20.0], pts
        assert pts[RUS_BONES.index("ulna")] == [30.0, 40.0], pts
        # mc3 = midpoint of kp2 (None) and kp3 (100,100) → None because kp2 missing
        assert pts[RUS_BONES.index("mc3")] is None, pts
        # now give kp2 a value and re-check midpoint math
        lm2 = [(10.0, 20.0), (30.0, 40.0), (0.0, 0.0), (100.0, 100.0)]
        # (0,0) reads as None in COCO parse, so test midpoint directly with non-zero:
        lm2[2] = (50.0, 60.0)
        assert _bone_point(lm2, (2, 3)) == [75.0, 80.0], _bone_point(lm2, (2, 3))
        print("selftest OK — parse, index map, and midpoint all correct")
    finally:
        LANDMARK_TO_BONE = saved


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ann", type=Path, help="BoNet annotations (.json COCO/records or .csv)")
    ap.add_argument("--images", type=Path, default=None, help="image dir (to skip missing files / for preview)")
    ap.add_argument("--out", type=Path, default=Path("keypoints.jsonl"), help="output JSONL")
    ap.add_argument("--inspect", action="store_true", help="print keypoint counts + a sample and exit")
    ap.add_argument("--preview", type=int, metavar="N", default=0, help="write N overlay PNGs and exit")
    ap.add_argument("--out-preview", type=Path, default=Path("loc_preview"))
    ap.add_argument("--selftest", action="store_true", help="run the pure-logic self-test and exit")
    args = ap.parse_args()

    if args.selftest:
        _selftest(); return
    if not args.ann:
        ap.error("--ann is required (unless --selftest)")
    if args.inspect:
        inspect(args.ann); return
    if args.preview:
        if not args.images:
            ap.error("--preview needs --images")
        preview(args.ann, args.images, args.out_preview, args.preview); return

    if all(v is None for v in LANDMARK_TO_BONE.values()):
        ap.error("LANDMARK_TO_BONE is empty — edit backend/ai/baar_to_jsonl.py first "
                 "(run --inspect, then map bones to keypoint indices). Refusing to write an all-null set.")
    stats = convert(args.ann, args.out, args.images)
    print(json.dumps(stats, indent=2))
    print(f"\nWrote {stats['written']} rows → {args.out}. Next: train_localizer --ann {args.out}")


if __name__ == "__main__":
    main()
