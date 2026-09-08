"""Train a CPU bone-age screening model (whole-image Greulich-Pyle regression).

Image + sex → bone age (months) with a MobileNet​V3-Small backbone. Trains on the
small bundled validation set OR — for much better accuracy — the FULL RSNA training
set (~12.6k images). Point it at the data; it auto-detects the CSV columns
(handles both the Kaggle `id,boneage,male` layout and the bundled
`Image ID,male,Bone Age (months)` layout):

    # full RSNA (recommended; run on a free Colab/Kaggle GPU, then copy the ONNX back):
    python -m backend.ai.train_boneage --data /path/rsna/images --csv /path/rsna/train.csv \
        --img-size 224 --epochs 30

    # or via env vars:
    RSNA_DATA_DIR=/path/imgs RSNA_CSV=/path/train.csv python -m backend.ai.train_boneage --img-size 224

    # quick pipeline check on the bundled validation set (fast):
    python -m backend.ai.train_boneage --limit 200 --epochs 1

Exports ONNX + metadata for backend/ai/boneage.py; inference reads ``input_size``
from the metadata, so a model trained at 224 runs at 224 locally. The printed
held-out MAE is the real accuracy. Whole-image, NOT TW3 — a screening triage.

Why this helps: the shipped model saw only ~1,425 images (MAE ~14 mo). The full
RSNA set is ~9× larger; more data is the dominant accuracy lever here.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image

from backend.ai.boneage import IMG_SIZE, META_PATH, MODEL_PATH, _MEAN, _STD

APP_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DIR = APP_ROOT / "datasets" / "validation"

_ID_COLS = ("id", "image id", "imageid", "image_id", "case", "filename", "fileid")
_AGE_COLS = ("boneage", "bone age (months)", "bone_age_months", "boneage_months",
             "bone age", "age")
_TRUE = {"true", "1", "m", "male", "yes", "y"}


# ── dataset ──────────────────────────────────────────────────────────────────

def _resolve_data(args) -> tuple[Path, Path]:
    data_dir = Path(args.data or os.environ.get("RSNA_DATA_DIR") or _DEFAULT_DIR)
    if args.csv:
        csv_path: Path | None = Path(args.csv)
    elif os.environ.get("RSNA_CSV"):
        csv_path = Path(os.environ["RSNA_CSV"])
    else:
        bundled = _DEFAULT_DIR / "Validation Dataset.csv"
        csv_path = bundled if bundled.exists() else next(iter(sorted(data_dir.glob("*.csv"))), None)
    if csv_path is None or not csv_path.exists():
        raise SystemExit(f"CSV not found — pass --csv (looked under {data_dir})")
    if not data_dir.exists():
        raise SystemExit(f"image directory not found: {data_dir}")
    return data_dir, csv_path


def _detect_cols(fieldnames: list[str]) -> tuple[str, str, str | None]:
    low = {f.lower().strip(): f for f in (fieldnames or [])}

    def pick(cands: tuple[str, ...], what: str) -> str:
        for c in cands:
            if c in low:
                return low[c]
        raise SystemExit(f"could not find a {what} column in CSV headers: {fieldnames}")

    return pick(_ID_COLS, "image-id"), pick(_AGE_COLS, "bone-age(months)"), low.get("male")


def _index_images(data_dir: Path) -> dict[str, Path]:
    idx: dict[str, Path] = {}
    for ext in ("*.png", "*.jpg", "*.jpeg"):
        for p in data_dir.rglob(ext):
            idx.setdefault(p.stem, p)
    return idx


def _load_rows(data_dir: Path, csv_path: Path, limit: int | None = None) -> list[tuple[Path, float, float]]:
    imgs = _index_images(data_dir)
    rows: list[tuple[Path, float, float]] = []
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        id_col, age_col, male_col = _detect_cols(reader.fieldnames)
        for r in reader:
            key = str(r[id_col]).strip()
            path = imgs.get(key) or imgs.get(key.rsplit(".", 1)[0])
            if path is None:
                continue
            try:
                months = float(str(r[age_col]).strip())
            except (ValueError, TypeError):
                continue
            sex = 1.0 if (male_col and str(r[male_col]).strip().lower() in _TRUE) else 0.0
            rows.append((path, sex, months))
            if limit and len(rows) >= limit:
                break
    if not rows:
        raise SystemExit(f"no labelled images matched between {csv_path} and images under {data_dir}")
    return rows


# ── model ────────────────────────────────────────────────────────────────────

def _build_backbone():
    from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

    return mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.DEFAULT)


def _build_net():
    import torch
    from torch import nn

    backbone = _build_backbone()

    class BoneAgeNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.features = backbone.features
            self.avgpool = backbone.avgpool  # global pool → 576, independent of input size
            self.head = nn.Sequential(
                nn.Linear(576 + 1, 256), nn.ReLU(), nn.Dropout(0.3), nn.Linear(256, 1)
            )

        def forward(self, image, sex):
            f = self.avgpool(self.features(image)).flatten(1)
            return self.head(torch.cat([f, sex], dim=1)).squeeze(1)

    return BoneAgeNet()


def _export(net, best_state, mae, mode, n, n_val, img_size, dataset_name) -> None:
    import torch

    if best_state is not None:
        net.load_state_dict(best_state)
    net.eval()
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        net, (torch.zeros(1, 3, img_size, img_size), torch.zeros(1, 1)),
        str(MODEL_PATH), input_names=["image", "sex"],
        output_names=["bone_age_months"], opset_version=17, dynamo=False,
    )
    meta = {
        "model_version": f"boneage-gp-mnv3s-{mode}-{date.today().isoformat()}",
        "val_mae_months": round(mae, 1), "val_mae_years": round(mae / 12, 2),
        "n_images": int(n), "n_val": int(n_val), "input_size": int(img_size), "mode": mode,
        "method": "Greulich-Pyle whole-image (screening)",
        "trained_on": dataset_name,
    }
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\nBest val MAE: {mae:.1f} months ({mae / 12:.2f} y)")
    print(f"Exported: {MODEL_PATH}\nMetadata: {meta}")


# ── image cache (keyed by size + count so switching datasets is safe) ─────────

def _load_all_images(rows, img_size, use_cache=True):
    cache = MODEL_PATH.with_name(f"_img_cache_{img_size}_{len(rows)}.npz")
    if use_cache and cache.exists():
        d = np.load(cache)
        if d["imgs"].shape[0] == len(rows):
            return d["imgs"], d["sex"], d["y"]
    imgs, sexes, ys = [], [], []
    for i, (path, sex, months) in enumerate(rows):
        try:
            g = Image.open(path).convert("L").resize((img_size, img_size))
        except Exception:
            continue
        imgs.append(np.asarray(g, dtype=np.uint8)); sexes.append(sex); ys.append(months)
        if (i + 1) % 500 == 0:
            print(f"  loaded {i + 1}/{len(rows)}")
    imgs = np.asarray(imgs, dtype=np.uint8)
    sex = np.asarray(sexes, dtype=np.float32)[:, None]
    y = np.asarray(ys, dtype=np.float32)
    if use_cache:
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        np.savez(cache, imgs=imgs, sex=sex, y=y)
    return imgs, sex, y


def train_finetune(rows, img_size=IMG_SIZE, epochs=25, dataset_name="rsna", use_cache=True) -> None:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, Dataset
    from torchvision.transforms.v2 import functional as TF

    print(f"Dataset: {len(rows)} labelled images · {img_size}px · fine-tune · {epochs} epochs")
    imgs, sex, y = _load_all_images(rows, img_size, use_cache)
    mean = torch.tensor(_MEAN).view(3, 1, 1)
    std = torch.tensor(_STD).view(3, 1, 1)

    rng = np.random.default_rng(42)
    idx = rng.permutation(len(y))
    n_val = max(1, int(0.15 * len(y)))
    val_idx, tr_idx = idx[:n_val], idx[n_val:]

    class DS(Dataset):
        def __init__(self, ix, train):
            self.ix = ix; self.train = train

        def __len__(self):
            return len(self.ix)

        def __getitem__(self, i):
            j = self.ix[i]
            img = torch.from_numpy(imgs[j].astype(np.float32) / 255.0)[None].repeat(3, 1, 1)
            if self.train:
                img = TF.rotate(img, float(rng.uniform(-12, 12)))
                # small zoom/shift so more data generalises; hands are always left → no flip
                img = TF.affine(img, angle=0, translate=[int(rng.uniform(-8, 8)), int(rng.uniform(-8, 8))],
                                scale=float(rng.uniform(0.92, 1.08)), shear=[0.0])
                img = torch.clamp(img * float(rng.uniform(0.9, 1.1)), 0, 1)
            img = (img - mean) / std
            return img, torch.tensor([sex[j, 0]], dtype=torch.float32), torch.tensor(y[j])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    tr = DataLoader(DS(tr_idx, True), batch_size=32, shuffle=True, num_workers=0)
    va = DataLoader(DS(val_idx, False), batch_size=64, shuffle=False, num_workers=0)

    net = _build_net().to(device)
    opt = torch.optim.Adam([
        {"params": net.features.parameters(), "lr": 3e-4},
        {"params": net.head.parameters(), "lr": 1e-3},
    ], weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
    loss_fn = nn.L1Loss()
    best_mae, best_state = float("inf"), None

    for epoch in range(epochs):
        net.train()
        for img, s, target in tr:
            img, s, target = img.to(device), s.to(device), target.to(device)
            opt.zero_grad()
            loss_fn(net(img, s), target).backward()
            opt.step()
        sched.step()
        net.eval()
        errs = []
        with torch.no_grad():
            for img, s, target in va:
                img, s, target = img.to(device), s.to(device), target.to(device)
                errs.append(torch.abs(net(img, s) - target).cpu())
        mae = float(torch.cat(errs).mean())
        if mae < best_mae:
            best_mae = mae
            best_state = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
        print(f"  epoch {epoch + 1:2d}/{epochs}  val MAE {mae:.1f} mo  (best {best_mae:.1f})")

    net.to("cpu")
    _export(net, best_state, best_mae, "ft", len(y), n_val, img_size, dataset_name)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default=None, help="image directory (or RSNA_DATA_DIR)")
    ap.add_argument("--csv", default=None, help="labels CSV (or RSNA_CSV)")
    ap.add_argument("--img-size", type=int, default=IMG_SIZE, dest="img_size")
    ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--limit", type=int, default=None, help="cap #images (quick pipeline test)")
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    data_dir, csv_path = _resolve_data(args)
    rows = _load_rows(data_dir, csv_path, args.limit)
    train_finetune(rows, img_size=args.img_size, epochs=args.epochs,
                   dataset_name=data_dir.name, use_cache=not args.no_cache)


if __name__ == "__main__":
    main()
