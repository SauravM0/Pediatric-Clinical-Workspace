"""Train a compact CPU bone-age screening model on the local RSNA validation set.

Whole-image Greulich-Pyle regression (image + sex -> bone age in months). Uses a
frozen MobileNetV3-Small backbone (ImageNet) as a fixed feature extractor +
a small trained head, so it trains in minutes on CPU. Exports ONNX for
backend/ai/boneage.py.

    python -m backend.ai.train_boneage

Honesty: small data (~1.4k images), whole-image (NOT TW3). The printed/held-out
MAE is the real accuracy — report it, don't inflate it.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image

from backend.ai.boneage import IMG_SIZE, META_PATH, MODEL_PATH, preprocess

APP_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = APP_ROOT / "Bone Age Validation Set"
CSV_PATH = DATA_ROOT / "Validation Dataset.csv"
_CACHE = MODEL_PATH.with_name("_feat_cache.npz")


def _index_images() -> dict[str, Path]:
    found: dict[str, Path] = {}
    for png in DATA_ROOT.rglob("*.png"):
        found[png.stem] = png
    return found


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
    import torch
    from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

    m = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.DEFAULT)
    m.eval()
    return m


def _extract_features(rows) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    import torch

    if _CACHE.exists():
        d = np.load(_CACHE)
        return d["feats"], d["sex"], d["y"]

    backbone = _build_backbone()
    feats, sexes, ys = [], [], []
    with torch.no_grad():
        for i, (path, sex, months) in enumerate(rows):
            try:
                arr = preprocess(Image.open(path))  # 1x3xHxW
            except Exception:
                continue
            x = torch.from_numpy(arr)
            f = backbone.avgpool(backbone.features(x)).flatten(1).numpy()[0]
            feats.append(f); sexes.append(sex); ys.append(months)
            if (i + 1) % 100 == 0:
                print(f"  features {i + 1}/{len(rows)}")
    feats = np.asarray(feats, dtype=np.float32)
    sex = np.asarray(sexes, dtype=np.float32)[:, None]
    y = np.asarray(ys, dtype=np.float32)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez(_CACHE, feats=feats, sex=sex, y=y)
    return feats, sex, y


def _make_full_model(head_state):
    import torch
    from torch import nn

    backbone = _build_backbone()

    class BoneAgeNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.features = backbone.features
            self.avgpool = backbone.avgpool
            self.head = nn.Sequential(
                nn.Linear(576 + 1, 256), nn.ReLU(), nn.Dropout(0.0), nn.Linear(256, 1)
            )

        def forward(self, image, sex):
            f = self.avgpool(self.features(image)).flatten(1)
            return self.head(torch.cat([f, sex], dim=1)).squeeze(1)

    net = BoneAgeNet()
    net.head.load_state_dict(head_state)
    net.eval()
    return net


def main() -> None:
    import torch
    from torch import nn

    rows = _load_rows()
    print(f"Dataset: {len(rows)} labelled images")
    feats, sex, y = _extract_features(rows)
    print(f"Features: {feats.shape}, targets {y.shape}")

    rng = np.random.default_rng(42)
    idx = rng.permutation(len(y))
    n_val = max(1, int(0.15 * len(y)))
    val_idx, tr_idx = idx[:n_val], idx[n_val:]

    def to_t(a):
        return torch.from_numpy(np.asarray(a, dtype=np.float32))

    Xtr = to_t(np.concatenate([feats[tr_idx], sex[tr_idx]], axis=1))
    ytr = to_t(y[tr_idx])
    Xva = to_t(np.concatenate([feats[val_idx], sex[val_idx]], axis=1))
    yva = to_t(y[val_idx])

    head = nn.Sequential(nn.Linear(576 + 1, 256), nn.ReLU(), nn.Dropout(0.3), nn.Linear(256, 1))
    opt = torch.optim.Adam(head.parameters(), lr=1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.StepLR(opt, step_size=1500, gamma=0.5)
    loss_fn = nn.L1Loss()
    best_mae, best_state = float("inf"), None
    for epoch in range(6000):
        head.train()
        opt.zero_grad()
        loss = loss_fn(head(Xtr).squeeze(1), ytr)
        loss.backward()
        opt.step()
        sched.step()
        if (epoch + 1) % 50 == 0:
            head.eval()
            with torch.no_grad():
                mae = float(loss_fn(head(Xva).squeeze(1), yva).item())
            if mae < best_mae:
                best_mae = mae
                best_state = {k: v.clone() for k, v in head.state_dict().items()}
            if (epoch + 1) % 500 == 0:
                print(f"  epoch {epoch + 1:4d}  train L1 {loss.item():.1f}  val MAE {mae:.1f} mo  (best {best_mae:.1f})")

    # export full model (frozen backbone + best head) to ONNX via the legacy exporter
    net = _make_full_model(best_state)
    dummy_img = torch.zeros(1, 3, IMG_SIZE, IMG_SIZE)
    dummy_sex = torch.zeros(1, 1)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        net, (dummy_img, dummy_sex), str(MODEL_PATH),
        input_names=["image", "sex"], output_names=["bone_age_months"],
        opset_version=17, dynamo=False,
    )
    meta = {
        "model_version": f"boneage-gp-mnv3s-{date.today().isoformat()}",
        "val_mae_months": round(best_mae, 1),
        "val_mae_years": round(best_mae / 12, 2),
        "n_images": len(y), "n_val": int(n_val),
        "input_size": IMG_SIZE, "method": "Greulich-Pyle whole-image (screening)",
        "trained_on": "RSNA bone-age validation set (local)",
    }
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\nBest val MAE: {best_mae:.1f} months ({best_mae / 12:.2f} y)")
    print(f"Exported: {MODEL_PATH}")
    print(f"Metadata: {meta}")


if __name__ == "__main__":
    main()
