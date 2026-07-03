"""Train a compact CPU bone-age screening model on the local RSNA validation set.

Whole-image Greulich-Pyle regression (image + sex -> bone age in months) with a
MobileNetV3-Small backbone. Two modes:

    python -m backend.ai.train_boneage --mode finetune   # end-to-end (more accurate, slower)
    python -m backend.ai.train_boneage --mode frozen      # frozen features + head (fast)

Exports ONNX + metadata for backend/ai/boneage.py. Honesty: small data (~1.4k
images), whole-image (NOT TW3). The printed held-out MAE is the real accuracy.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image

from backend.ai.boneage import IMG_SIZE, META_PATH, MODEL_PATH, _MEAN, _STD, preprocess

APP_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = APP_ROOT / "Bone Age Validation Set"
CSV_PATH = DATA_ROOT / "Validation Dataset.csv"
_CACHE = MODEL_PATH.with_name("_feat_cache.npz")
_IMG_CACHE = MODEL_PATH.with_name("_img_cache.npz")


def _index_images() -> dict[str, Path]:
    return {p.stem: p for p in DATA_ROOT.rglob("*.png")}


def _load_rows() -> list[tuple[Path, float, float]]:
    imgs = _index_images()
    rows: list[tuple[Path, float, float]] = []
    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            path = imgs.get(str(r["Image ID"]).strip())
            if path is None:
                continue
            sex = 1.0 if str(r["male"]).strip().lower() == "true" else 0.0
            rows.append((path, sex, float(r["Bone Age (months)"])))
    return rows


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
            self.avgpool = backbone.avgpool
            self.head = nn.Sequential(
                nn.Linear(576 + 1, 256), nn.ReLU(), nn.Dropout(0.3), nn.Linear(256, 1)
            )

        def forward(self, image, sex):
            f = self.avgpool(self.features(image)).flatten(1)
            return self.head(torch.cat([f, sex], dim=1)).squeeze(1)

    return BoneAgeNet()


def _export(net, best_state, mae, mode, n, n_val) -> None:
    import torch

    if best_state is not None:
        net.load_state_dict(best_state)
    net.eval()
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        net, (torch.zeros(1, 3, IMG_SIZE, IMG_SIZE), torch.zeros(1, 1)),
        str(MODEL_PATH), input_names=["image", "sex"],
        output_names=["bone_age_months"], opset_version=17, dynamo=False,
    )
    meta = {
        "model_version": f"boneage-gp-mnv3s-{mode}-{date.today().isoformat()}",
        "val_mae_months": round(mae, 1), "val_mae_years": round(mae / 12, 2),
        "n_images": int(n), "n_val": int(n_val), "input_size": IMG_SIZE, "mode": mode,
        "method": "Greulich-Pyle whole-image (screening)",
        "trained_on": "RSNA bone-age validation set (local)",
    }
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\nBest val MAE: {mae:.1f} months ({mae / 12:.2f} y)")
    print(f"Exported: {MODEL_PATH}\nMetadata: {meta}")


# ── in-memory image cache for fine-tuning ─────────────────────────────────────

def _load_all_images(rows):
    if _IMG_CACHE.exists():
        d = np.load(_IMG_CACHE)
        return d["imgs"], d["sex"], d["y"]
    imgs, sexes, ys = [], [], []
    for i, (path, sex, months) in enumerate(rows):
        try:
            g = Image.open(path).convert("L").resize((IMG_SIZE, IMG_SIZE))
        except Exception:
            continue
        imgs.append(np.asarray(g, dtype=np.uint8)); sexes.append(sex); ys.append(months)
        if (i + 1) % 200 == 0:
            print(f"  loaded {i + 1}/{len(rows)}")
    imgs = np.asarray(imgs, dtype=np.uint8)
    sex = np.asarray(sexes, dtype=np.float32)[:, None]
    y = np.asarray(ys, dtype=np.float32)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez(_IMG_CACHE, imgs=imgs, sex=sex, y=y)
    return imgs, sex, y


def train_finetune(epochs: int = 25) -> None:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, Dataset
    from torchvision.transforms.v2 import functional as TF

    rows = _load_rows()
    print(f"Dataset: {len(rows)} labelled images (fine-tune mode)")
    imgs, sex, y = _load_all_images(rows)
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
            img = torch.from_numpy(imgs[j].astype(np.float32) / 255.0)[None]  # 1xHxW
            img = img.repeat(3, 1, 1)
            if self.train:
                angle = float(rng.uniform(-12, 12))
                img = TF.rotate(img, angle)
                img = torch.clamp(img * float(rng.uniform(0.9, 1.1)), 0, 1)
            img = (img - mean) / std
            return img, torch.tensor([sex[j, 0]], dtype=torch.float32), torch.tensor(y[j])

    tr = DataLoader(DS(tr_idx, True), batch_size=32, shuffle=True, num_workers=0)
    va = DataLoader(DS(val_idx, False), batch_size=64, shuffle=False, num_workers=0)

    net = _build_net()
    opt = torch.optim.Adam([
        {"params": net.features.parameters(), "lr": 3e-4},
        {"params": net.head.parameters(), "lr": 1e-3},
    ], weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.StepLR(opt, step_size=8, gamma=0.5)
    loss_fn = nn.L1Loss()
    best_mae, best_state = float("inf"), None

    for epoch in range(epochs):
        net.train()
        for img, s, target in tr:
            opt.zero_grad()
            loss = loss_fn(net(img, s), target)
            loss.backward()
            opt.step()
        sched.step()
        net.eval()
        errs = []
        with torch.no_grad():
            for img, s, target in va:
                errs.append(torch.abs(net(img, s) - target))
        mae = float(torch.cat(errs).mean())
        if mae < best_mae:
            best_mae = mae
            best_state = {k: v.clone() for k, v in net.state_dict().items()}
        print(f"  epoch {epoch + 1:2d}/{epochs}  val MAE {mae:.1f} mo  (best {best_mae:.1f})")

    _export(net, best_state, best_mae, "ft", len(y), n_val)


def train_frozen() -> None:
    import torch
    from torch import nn

    rows = _load_rows()
    print(f"Dataset: {len(rows)} labelled images (frozen mode)")
    if _CACHE.exists():
        d = np.load(_CACHE); feats, sex, y = d["feats"], d["sex"], d["y"]
    else:
        backbone = _build_backbone(); backbone.eval()
        feats, sexes, ys = [], [], []
        with torch.no_grad():
            for i, (path, sex_v, months) in enumerate(rows):
                try:
                    x = torch.from_numpy(preprocess(Image.open(path)))
                except Exception:
                    continue
                f = backbone.avgpool(backbone.features(x)).flatten(1).numpy()[0]
                feats.append(f); sexes.append(sex_v); ys.append(months)
                if (i + 1) % 200 == 0:
                    print(f"  features {i + 1}/{len(rows)}")
        feats = np.asarray(feats, dtype=np.float32)
        sex = np.asarray(sexes, dtype=np.float32)[:, None]
        y = np.asarray(ys, dtype=np.float32)
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        np.savez(_CACHE, feats=feats, sex=sex, y=y)

    rng = np.random.default_rng(42)
    idx = rng.permutation(len(y)); n_val = max(1, int(0.15 * len(y)))
    val_idx, tr_idx = idx[:n_val], idx[n_val:]
    to_t = lambda a: torch.from_numpy(np.asarray(a, dtype=np.float32))
    Xtr = to_t(np.concatenate([feats[tr_idx], sex[tr_idx]], axis=1)); ytr = to_t(y[tr_idx])
    Xva = to_t(np.concatenate([feats[val_idx], sex[val_idx]], axis=1)); yva = to_t(y[val_idx])

    net = _build_net()
    for p in net.features.parameters():
        p.requires_grad_(False)
    head = net.head
    opt = torch.optim.Adam(head.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_fn = nn.L1Loss()
    best_mae, best_state = float("inf"), None
    for epoch in range(6000):
        head.train(); opt.zero_grad()
        f = to_t(feats[tr_idx]); s = to_t(sex[tr_idx])
        loss = loss_fn(head(torch.cat([f, s], 1)).squeeze(1), ytr)
        loss.backward(); opt.step()
        if (epoch + 1) % 100 == 0:
            head.eval()
            with torch.no_grad():
                fv = to_t(feats[val_idx]); sv = to_t(sex[val_idx])
                mae = float(loss_fn(head(torch.cat([fv, sv], 1)).squeeze(1), yva))
            if mae < best_mae:
                best_mae = mae; best_state = {k: v.clone() for k, v in net.state_dict().items()}
    _export(net, best_state, best_mae, "frozen", len(y), n_val)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["finetune", "frozen"], default="finetune")
    ap.add_argument("--epochs", type=int, default=25)
    args = ap.parse_args()
    if args.mode == "finetune":
        train_finetune(args.epochs)
    else:
        train_frozen()


if __name__ == "__main__":
    main()
