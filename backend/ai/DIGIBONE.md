# Adopting digiBONE (M4.3)

digiBONE is the strongest available upgrade to the screening path: MIT-licensed,
Indian-trained, and from the same institute as the IAP growth charts this product
already uses.

| | Incumbent | digiBONE |
|---|---|---|
| MAE | **8.99 mo** (locked RSNA test) | **4.75 mo** boys / **4.93 mo** girls (Indian validation) |
| Trained on | RSNA (US) only | RSNA + 2,430 Indian children (HCJMRI, Pune) |
| Method | whole-image Greulich–Pyle | **segmental** Greulich–Pyle (short bones / carpals / wrist) |
| Licence | — | MIT |

Source: `https://github.com/goellab/digiBONE` · Frontiers Endocrinol 2026,
doi 10.3389/fendo.2026.1757571.

**Not bundled.** The weights are a separate download and conversion, and the
model is not committed here. Everything else in M4 (registry, version binding,
preprocessing, gate) is in place so the adoption is a data step, not an
engineering one.

---

## Why this is not just `pip install torch`

digiBONE ships PyTorch weights. This project's inference path is **ONNX Runtime
only**, deliberately: adding `torch` to `requirements.txt` takes the deployable
from ~200 MB to over 2 GB and pulls a CUDA-less training framework into a
clinical inference path. `torch` stays in `requirements-dev.txt`.

So conversion happens **offline**, and only the `.onnx` plus a metadata JSON is
committed.

## Procedure

### 1. Obtain the weights (machine with network + torch)

```bash
git clone https://github.com/goellab/digiBONE
cd digiBONE && pip install -r requirements.txt && python3 download_models1.py
```

Verify the MIT LICENSE file travels with the artefact — attribution is required.

### 2. Convert to ONNX

```bash
python -m backend.ai.convert_digibone --weights /path/to/digibone_weights.pth \
                                      --out backend/ai/models/boneage_digibone.onnx
```

The converter asserts parity against the PyTorch model on ≥100 images
(max abs diff < 1e-4). **A conversion that silently changes the numbers is worse
than no conversion**, because everything downstream would be calibrated against
a model that is not the one that was validated.

### 3. Declare it in the registry

`backend/ai/models/boneage_digibone.json`:

```json
{
  "model_version": "digibone-sgp-<date>",
  "kind": "screening",
  "method_key": "segmental-greulich-pyle",
  "population": "Indian-HCJMRI + RSNA",
  "input_size": 224,
  "preprocessing_version": "<the pipeline used at conversion time>",
  "trained_on": "RSNA + HCJMRI (Pune)"
}
```

`preprocessing_version` is **not optional**. `registry.resolve_interval_policy`
refuses to serve conformal intervals when it does not match the active pipeline,
which is the check that stops a preprocessing change from silently invalidating
calibration.

### 4. Evaluate on the existing locked test set

```bash
python -m backend.ai.validation.baseline_report --model boneage_digibone
```

Same harness, same frozen 1,425 images, same leak guard — so the number is
directly comparable to the incumbent's 8.99 mo.

### 5. Re-calibrate conformal intervals

```bash
python -m backend.ai.calibrate_conformal --model boneage_digibone
```

Quantiles do not transfer between models. Serving the incumbent's would give an
interval whose stated coverage is not its real coverage.

### 6. Release through the gate — as a **cross-method adoption**

```python
evaluate_candidate(
    ..., comparison_basis=release_gate.CROSS_METHOD_ADOPTION,
    adoption_rationale="Indian-trained segmental GP; adopted for population "
                       "validity, not for a delta on the RSNA test set.",
)
```

This matters. digiBONE's claim is accuracy on **Indian** children; the incumbent
was measured on **RSNA**. Requiring it to beat the incumbent on RSNA would either
block a better model or force someone to loosen the gate — and a loosened gate is
a permanent loss of a safety property. Cross-method adoption is instead held to
absolute thresholds plus a written rationale, and is **never auto-deployed**.

---

## What adoption does and does not change

**Does not** replace TW3. digiBONE produces **Greulich–Pyle** bone age. GP and
TW3-RUS are different constructs against different reference populations, and
`BoneAgeFeedback.method` already keeps them apart. Never average them.

**Does not** remove the need for an Indian validation cohort of your own.
digiBONE was validated on HCJMRI patients; your clinic's films are a different
sample, and the locked-test discipline exists precisely so that claim can be
checked rather than assumed.

**Does** make the segmental output meaningful: separate short-bone, carpal and
wrist estimates map onto the per-bone UI that already exists, so a reader can see
*where* the maturity signal is coming from instead of one opaque number.
