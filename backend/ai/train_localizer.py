"""Train the PEA bone localizer (center-point heatmaps) — PEARLS PEA module.

Predicts one center point per RUS bone (heatmap peak + sub-pixel offset), from
which localize.py derives ROI crops. Architecture follows the paper: ResNet18
encoder + up-conv decoder to stride 4, a focal heatmap loss (Eq. 2) and an L1
offset loss (Eq. 3).

Data = hand X-rays + per-bone keypoints. The annotation file is JSONL, one line
per image:

    {"image": "12345.png", "points": [[x0,y0], [x1,y1], ... 13 pairs ...]}

points are in ORIGINAL image pixels, in RUS_BONES order; use null for a bone whose
point is unknown (it is skipped in the loss). See LOCALIZE.md for turning the
public RSNA + BAAR/BoNet keypoint annotations into this format.

    python -m backend.ai.train_localizer --data <img_dir> --ann <ann.jsonl> \
        --img-size 512 --epochs 60

Train on a free Colab/Kaggle GPU; it exports ONNX for local CPU inference.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image

from backend.ai.localize import MODEL_PATH, META_PATH, STRIDE, DEFAULT_BOX_FRAC, _MEAN, _STD
from backend.tw3 import RUS_BONES

IMG_SIZE = 512


# ── model ────────────────────────────────────────────────────────────────────

def build_localizer(n_points: int, pretrained: bool = True):
    import torch
    from torch import nn
    from torchvision.models import ResNet18_Weights, resnet18

    r = resnet18(weights=ResNet18_Weights.DEFAULT if pretrained else None)
    encoder = nn.Sequential(r.conv1, r.bn1, r.relu, r.maxpool,
                            r.layer1, r.layer2, r.layer3, r.layer4)  # stride 32, 512ch

    def up(cin, cout):
        return nn.Sequential(
            nn.ConvTranspose2d(cin, cout, 4, stride=2, padding=1), nn.BatchNorm2d(cout), nn.ReLU(inplace=True))

    class PEA(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = encoder
            self.decoder = nn.Sequential(up(512, 256), up(256, 128), up(128, 64))  # stride 32→4
            self.hm = nn.Conv2d(64, n_points, 1)
            self.off = nn.Conv2d(64, 2, 1)
            self.hm.bias.data.fill_(-2.19)  # focal-loss prior (rare positives)

        def forward(self, x):
            f = self.decoder(self.encoder(x))
            return self.hm(f), self.off(f)

    return PEA()


# ── targets & losses ─────────────────────────────────────────────────────────

def _gaussian(radius: int, sigma: float | None = None) -> np.ndarray:
    sigma = sigma or (2 * radius + 1) / 6.0
    ax = np.arange(-radius, radius + 1)
    xx, yy = np.meshgrid(ax, ax)
    return np.exp(-(xx * xx + yy * yy) / (2 * sigma * sigma))


def render_targets(points_hm: np.ndarray, n_points: int, h: int, w: int, radius: int = 2):
    """points_hm: [C,2] (x,y) in heatmap coords, NaN where unknown.
    Returns heatmap[C,h,w], offset[2,h,w], offset_mask[2,h,w]."""
    hm = np.zeros((n_points, h, w), dtype=np.float32)
    off = np.zeros((2, h, w), dtype=np.float32)
    mask = np.zeros((2, h, w), dtype=np.float32)
    g = _gaussian(radius)
    for c in range(n_points):
        x, y = points_hm[c]
        if not (np.isfinite(x) and np.isfinite(y)):
            continue
        xi, yi = int(np.floor(x)), int(np.floor(y))
        if not (0 <= xi < w and 0 <= yi < h):
            continue
        # splat gaussian (clipped to bounds)
        x0, x1 = max(0, xi - radius), min(w, xi + radius + 1)
        y0, y1 = max(0, yi - radius), min(h, yi + radius + 1)
        gx0, gy0 = x0 - (xi - radius), y0 - (yi - radius)
        hm[c, y0:y1, x0:x1] = np.maximum(hm[c, y0:y1, x0:x1],
                                         g[gy0:gy0 + (y1 - y0), gx0:gx0 + (x1 - x0)])
        off[0, yi, xi] = x - xi
        off[1, yi, xi] = y - yi
        mask[:, yi, xi] = 1.0
    return hm, off, mask


def focal_loss(pred_logits, gt):
    """CenterNet penalty-reduced focal loss. pred_logits/gt: [B,C,h,w]."""
    import torch

    pred = torch.sigmoid(pred_logits).clamp(1e-6, 1 - 1e-6)
    pos = gt.eq(1).float()
    neg = gt.lt(1).float()
    neg_w = torch.pow(1 - gt, 4)
    pos_loss = torch.log(pred) * torch.pow(1 - pred, 2) * pos
    neg_loss = torch.log(1 - pred) * torch.pow(pred, 2) * neg_w * neg
    n_pos = pos.sum()
    if n_pos == 0:
        return -neg_loss.sum()
    return -(pos_loss.sum() + neg_loss.sum()) / n_pos


# ── dataset ──────────────────────────────────────────────────────────────────

class _KPDataset:
    def __init__(self, rows, img_dir, img_size, n_points):
        self.rows = rows; self.img_dir = Path(img_dir)
        self.img_size = img_size; self.n_points = n_points
        self.hm_size = img_size // STRIDE

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        import torch

        rec = self.rows[i]
        path = self.img_dir / rec["image"]
        img = Image.open(path).convert("L")
        ow, oh = img.size
        arr = np.asarray(img.resize((self.img_size, self.img_size)), dtype=np.float32) / 255.0
        arr = np.stack([arr, arr, arr], 0)
        arr = (arr - _MEAN[:, None, None]) / _STD[:, None, None]
        pts = np.full((self.n_points, 2), np.nan, dtype=np.float32)
        for c, p in enumerate(rec.get("points", [])[: self.n_points]):
            if p and p[0] is not None and p[1] is not None:
                pts[c, 0] = float(p[0]) / ow * self.hm_size
                pts[c, 1] = float(p[1]) / oh * self.hm_size
        hm, off, mask = render_targets(pts, self.n_points, self.hm_size, self.hm_size)
        return (torch.from_numpy(arr.astype(np.float32)), torch.from_numpy(hm),
                torch.from_numpy(off), torch.from_numpy(mask))


def _load_ann(ann_path: Path, limit=None) -> list[dict]:
    rows = []
    with open(ann_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
            if limit and len(rows) >= limit:
                break
    if not rows:
        raise SystemExit(f"no annotations in {ann_path}")
    return rows


# ── training ─────────────────────────────────────────────────────────────────

def train(rows, img_dir, *, img_size=IMG_SIZE, epochs=60, point_names=None,
          export=True, pretrained=True, log=print):
    import torch
    from torch.utils.data import DataLoader

    n_points = len(point_names or RUS_BONES)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ds = _KPDataset(rows, img_dir, img_size, n_points)
    n_val = max(1, int(0.1 * len(ds)))
    rng = np.random.default_rng(42)
    idx = rng.permutation(len(ds))
    tr_rows = [rows[i] for i in idx[n_val:]]
    va_rows = [rows[i] for i in idx[:n_val]]
    tr = DataLoader(_KPDataset(tr_rows, img_dir, img_size, n_points), batch_size=8, shuffle=True)
    va = DataLoader(_KPDataset(va_rows, img_dir, img_size, n_points), batch_size=8)

    net = build_localizer(n_points, pretrained=pretrained).to(device)
    opt = torch.optim.Adam(net.parameters(), lr=2e-4, weight_decay=1e-4)
    l1 = torch.nn.L1Loss(reduction="sum")
    best, best_state = float("inf"), None
    log(f"Localizer: {len(ds)} images · {n_points} points · {img_size}px · device {device}")

    for ep in range(epochs):
        net.train()
        for img, hm, off, mask in tr:
            img, hm, off, mask = img.to(device), hm.to(device), off.to(device), mask.to(device)
            phm, poff = net(img)
            loss = focal_loss(phm, hm) + l1(poff * mask, off * mask) / (mask.sum() + 1e-4)
            opt.zero_grad(); loss.backward(); opt.step()
        # val: mean heatmap-peak pixel error
        net.eval(); errs = []
        with torch.no_grad():
            for img, hm, off, mask in va:
                phm, _ = net(img.to(device))
                errs.append(_peak_err(phm.cpu().numpy(), hm.numpy()))
        vmae = float(np.mean(errs)) if errs else float("inf")
        if vmae < best:
            best = vmae; best_state = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
        log(f"  epoch {ep + 1:3d}/{epochs}  val peak-err {vmae:.2f} px  (best {best:.2f})")

    if best_state is not None:
        net.load_state_dict(best_state)
    if export:
        _export(net.to("cpu"), img_size, n_points, best, len(ds), point_names or list(RUS_BONES))
    return net, best


def _peak_err(pred_logits, gt) -> float:
    """Mean L2 (heatmap px) between predicted and GT peak, over labelled channels."""
    B, C, h, w = pred_logits.shape
    errs = []
    for b in range(B):
        for c in range(C):
            if gt[b, c].max() < 1.0:
                continue
            pp = np.unravel_index(int(np.argmax(pred_logits[b, c])), (h, w))
            gp = np.unravel_index(int(np.argmax(gt[b, c])), (h, w))
            errs.append(((pp[0] - gp[0]) ** 2 + (pp[1] - gp[1]) ** 2) ** 0.5)
    return float(np.mean(errs)) if errs else 0.0


def _export(net, img_size, n_points, peak_err, n_images, point_names) -> None:
    import torch

    net.eval()
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        net, torch.zeros(1, 3, img_size, img_size), str(MODEL_PATH),
        input_names=["image"], output_names=["heatmap", "offset"],
        opset_version=17, dynamo=False,
    )
    meta = {
        "model_version": f"localizer-pea-r18-{date.today().isoformat()}",
        "input_size": int(img_size), "stride": STRIDE, "box_frac": DEFAULT_BOX_FRAC,
        "n_points": int(n_points), "point_names": list(point_names),
        "val_peak_err_px": round(float(peak_err), 2), "n_images": int(n_images),
        "method": "PEA center-point localization (PEARLS)",
    }
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\nExported: {MODEL_PATH}\nMetadata: {meta}")


# ── synthetic data (for tests / smoke) ───────────────────────────────────────

def synth_dataset(out_dir: Path, n: int = 12, n_points: int = 4, size: int = 128, seed: int = 0):
    """Make tiny images with bright blobs at known points + a JSONL. Returns (img_dir, ann_path)."""
    out_dir = Path(out_dir); img_dir = out_dir / "img"; img_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    ann = out_dir / "ann.jsonl"
    with open(ann, "w", encoding="utf-8") as fh:
        for i in range(n):
            arr = rng.integers(20, 60, size=(size, size)).astype(np.uint8)
            pts = []
            for _ in range(n_points):
                x, y = int(rng.integers(12, size - 12)), int(rng.integers(12, size - 12))
                arr[max(0, y - 3):y + 4, max(0, x - 3):x + 4] = 230  # bright blob = the "bone"
                pts.append([x, y])
            Image.fromarray(arr, "L").save(img_dir / f"{i}.png")
            fh.write(json.dumps({"image": f"{i}.png", "points": pts}) + "\n")
    return img_dir, ann


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True, help="image directory")
    ap.add_argument("--ann", required=True, help="keypoints JSONL")
    ap.add_argument("--img-size", type=int, default=IMG_SIZE, dest="img_size")
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    rows = _load_ann(Path(args.ann), args.limit)
    train(rows, args.data, img_size=args.img_size, epochs=args.epochs)


if __name__ == "__main__":
    main()
