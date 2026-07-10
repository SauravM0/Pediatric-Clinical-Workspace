"""Train per-bone TW3 stage classifiers — PEARLS RL ordinal cumulative-link module.

One model per bone. Input = a crop of that bone (128px); output = maturity-stage
probabilities from an ORDINAL cumulative-link model (respects A<B<...<I — the
paper's Eq. 8-9), not plain classification. Trains from the dataset exporter:

    <dataset>/annotations.jsonl   (rows with bone_code, confirmed_stage, crop_path)
    <dataset>/crops/...

    python -m backend.ai.train_stager --dataset dataset --img-size 128 --epochs 40
    python -m backend.ai.train_stager --dataset dataset --bones radius,ulna

Exports backend/ai/models/stager/<bone>.onnx (+ .json) for stage_classifier.py.
Run on a free Colab/Kaggle GPU. IMPORTANT: needs stage-LABELLED crops, which the
box-editor + dataset exporter collect from doctor-graded films — no public dataset
has per-bone TW3 stage labels (the PEARLS authors hand-labelled 1,200 films).
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image

from backend.ai.stage_classifier import IMG_SIZE, _DIR, _MEAN, _STD
from backend.tw3 import LETTER_STAGES


# ── data ─────────────────────────────────────────────────────────────────────

def load_annotations(dataset: Path) -> list[dict]:
    rows: list[dict] = []
    with open(dataset / "annotations.jsonl", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("crop_path") and r.get("confirmed_stage") and r.get("bone_code"):
                rows.append(r)
    return rows


def _stage_order(s: str) -> int:
    return LETTER_STAGES.index(s) if s in LETTER_STAGES else 99


# ── ordinal model (cumulative link) ──────────────────────────────────────────

def build_ordinal(K: int, pretrained: bool = True):
    import torch
    from torch import nn
    from torchvision.models import MobileNet_V2_Weights, mobilenet_v2

    backbone = mobilenet_v2(weights=MobileNet_V2_Weights.DEFAULT if pretrained else None)

    class Ordinal(nn.Module):
        def __init__(self):
            super().__init__()
            self.features = backbone.features
            self.pool = nn.AdaptiveAvgPool2d(1)
            self.fc = nn.Linear(1280, 1)                       # single latent score y*
            self.theta0 = nn.Parameter(torch.zeros(1))         # first cut point
            self.deltas = nn.Parameter(torch.zeros(max(K - 2, 0)))  # positive gaps → K-1 cuts
            self.K = K

        def cutpoints(self):
            import torch.nn.functional as F
            if self.deltas.numel() == 0:
                return self.theta0
            return torch.cat([self.theta0, self.theta0 + torch.cumsum(F.softplus(self.deltas), 0)])

        def forward(self, x):
            logit = self.fc(self.pool(self.features(x)).flatten(1)).squeeze(1)  # [B]
            theta = self.cutpoints()                                             # [K-1]
            cum = torch.sigmoid(theta.unsqueeze(0) - logit.unsqueeze(1))         # [B,K-1] = P(y<=k)
            B = cum.size(0)
            z = torch.zeros(B, 1, device=cum.device); o = torch.ones(B, 1, device=cum.device)
            left = torch.cat([z, cum], 1); right = torch.cat([cum, o], 1)
            return (right - left).clamp(1e-6, 1.0)                               # [B,K] probs

    return Ordinal()


def train_bone(bone: str, rows: list[dict], dataset: Path, *, img_size=IMG_SIZE,
               epochs=40, pretrained=True, export=True, log=print):
    import torch
    from torch.utils.data import DataLoader, Dataset

    present = sorted({r["confirmed_stage"] for r in rows}, key=_stage_order)
    if len(present) < 2:
        log(f"  {bone}: {len(present)} distinct stage(s) — need ≥2, skipped"); return None
    idxmap = {s: i for i, s in enumerate(present)}; K = len(present)

    imgs, ys = [], []
    for r in rows:
        p = dataset / r["crop_path"]
        if not p.exists():
            continue
        imgs.append(np.asarray(Image.open(p).convert("L").resize((img_size, img_size)), np.uint8))
        ys.append(idxmap[r["confirmed_stage"]])
    if len(imgs) < 8:
        log(f"  {bone}: only {len(imgs)} crops — too few, skipped"); return None
    X = np.asarray(imgs, np.uint8); Y = np.asarray(ys, np.int64)
    mean = torch.tensor(_MEAN).view(3, 1, 1); std = torch.tensor(_STD).view(3, 1, 1)

    rng = np.random.default_rng(42); order = rng.permutation(len(Y))
    nv = max(1, int(0.2 * len(Y))); vi, ti = order[:nv], order[nv:]

    class DS(Dataset):
        def __init__(self, ix, train): self.ix = ix; self.train = train
        def __len__(self): return len(self.ix)
        def __getitem__(self, k):
            j = self.ix[k]
            img = torch.from_numpy(X[j].astype(np.float32) / 255.0)[None].repeat(3, 1, 1)
            if self.train:
                from torchvision.transforms.v2 import functional as TF
                img = TF.rotate(img, float(rng.uniform(-8, 8)))
                img = torch.clamp(img * float(rng.uniform(0.9, 1.1)), 0, 1)
            return (img - mean) / std, torch.tensor(Y[j])

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tr = DataLoader(DS(ti, True), batch_size=32, shuffle=True)
    va = DataLoader(DS(vi, False), batch_size=64)
    net = build_ordinal(K, pretrained).to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=5e-4, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
    best, best_state, best_adj = 0.0, None, 0.0

    for ep in range(epochs):
        net.train()
        for img, y in tr:
            img, y = img.to(dev), y.to(dev)
            probs = net(img)
            loss = -torch.log(probs.gather(1, y[:, None]).squeeze(1)).mean()  # ordinal NLL
            opt.zero_grad(); loss.backward(); opt.step()
        sched.step()
        net.eval(); correct = adj = tot = 0
        with torch.no_grad():
            for img, y in va:
                pred = net(img.to(dev)).argmax(1).cpu()
                correct += int((pred == y).sum()); adj += int((torch.abs(pred - y) <= 1).sum()); tot += len(y)
        acc = correct / max(tot, 1); adjacc = adj / max(tot, 1)
        if acc >= best:
            best, best_adj = acc, adjacc
            best_state = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
    log(f"  {bone}: K={K} ({''.join(present)}) crops={len(Y)}  val acc {best:.2f}  within-1 {best_adj:.2f}")

    if export and best_state is not None:
        net.load_state_dict(best_state); net.to("cpu").eval()
        _DIR.mkdir(parents=True, exist_ok=True)
        torch.onnx.export(net, torch.zeros(1, 3, img_size, img_size), str(_DIR / f"{bone}.onnx"),
                          input_names=["crop"], output_names=["probabilities"],
                          opset_version=17, dynamo=False)
        (_DIR / f"{bone}.json").write_text(json.dumps({
            "model_version": f"stager-{bone}-mnv2-{date.today().isoformat()}",
            "bone_code": bone, "stages": present, "input_size": int(img_size),
            "n_train": int(len(Y)), "val_accuracy": round(best, 3),
            "val_within1": round(best_adj, 3), "method": "PEARLS RL ordinal cumulative-link",
        }, indent=2), encoding="utf-8")
    return {"bone": bone, "K": K, "acc": best, "within1": best_adj, "n": len(Y)}


# ── synthetic data (for tests) ───────────────────────────────────────────────

def synth_dataset(out_dir: Path, bones=("radius", "ulna"), stages="ABCDE",
                  per_stage=12, size=64, seed=0):
    """Crops whose brightness encodes the stage → an ordinal signal. Returns dataset dir."""
    out_dir = Path(out_dir); crops = out_dir / "crops"; crops.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed); ann = out_dir / "annotations.jsonl"
    with open(ann, "w", encoding="utf-8") as fh:
        for bone in bones:
            for si, st in enumerate(stages):
                for k in range(per_stage):
                    base = 30 + si * (200 // max(len(stages) - 1, 1))
                    arr = np.clip(rng.normal(base, 10, (size, size)), 0, 255).astype(np.uint8)
                    rel = f"crops/{bone}_{st}_{k}.png"
                    Image.fromarray(arr, "L").save(out_dir / rel)
                    fh.write(json.dumps({"bone_code": bone, "confirmed_stage": st, "crop_path": rel}) + "\n")
    return out_dir


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dataset", required=True, help="dataset dir from the exporter")
    ap.add_argument("--bones", default=None, help="comma list, else all bones present")
    ap.add_argument("--img-size", type=int, default=IMG_SIZE, dest="img_size")
    ap.add_argument("--epochs", type=int, default=40)
    args = ap.parse_args()

    dataset = Path(args.dataset)
    rows = load_annotations(dataset)
    by_bone: dict[str, list] = defaultdict(list)
    for r in rows:
        by_bone[r["bone_code"]].append(r)
    wanted = args.bones.split(",") if args.bones else sorted(by_bone)
    print(f"Bones with crops: {sorted(by_bone)}")
    for bone in wanted:
        if bone in by_bone:
            train_bone(bone, by_bone[bone], dataset, img_size=args.img_size, epochs=args.epochs)
        else:
            print(f"  {bone}: no crops")


if __name__ == "__main__":
    main()
