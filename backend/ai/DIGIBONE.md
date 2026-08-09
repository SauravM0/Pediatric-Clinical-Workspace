# Adopting digiBONE (M4.3)

digiBONE is the strongest available upgrade to the screening path: MIT-licensed,
Indian-trained, and from the same institute as the IAP growth charts this product
already uses.

| | Incumbent | digiBONE |
|---|---|---|
| MAE | **8.99 mo** (locked RSNA test) | **4.7 mo** male / **4.9 mo** female, SGP (Indian validation) |
| | | full-hand: 5.7 mo male / 5.9 mo female |
| Trained on | RSNA (US) only | RSNA + 2,430 Indian children (HCJMRI, Pune) |
| Method | whole-image Greulich–Pyle | **segmental** Greulich–Pyle (short bones / carpals / wrist) |
| Licence | — | MIT |

Source: `https://github.com/goellab/digiBONE` · Frontiers Endocrinol 2026,
doi 10.3389/fendo.2026.1757571. Inference entry point in that repo is
`SGP_bone_age.py`; weights come from `download_models1.py` or the Releases page.

**Those two columns are not comparable and the table must not be read as if they
were.** 8.99 mo is this product's model on a frozen RSNA split; 4.7/4.9 is
digiBONE's own number on its own Indian validation set. Step 4 below exists to
produce the comparable figure, and the release gate refuses to treat a
cross-method adoption as if it were a like-for-like improvement.

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

Inspect the checkpoint first — digiBONE's architecture, input size and
normalisation are **not** documented in its README, and this converter refuses to
guess them:

```bash
python -m backend.ai.convert_digibone --weights digibone.pth --dry-run
```

That prints the tensor count and leading keys. Confirm the architecture and input
size against `SGP_bone_age.py` in the digiBONE repo, then:

```bash
python -m backend.ai.convert_digibone --weights digibone.pth --arch <name> --input-size <n> --parity-images /path/to/radiographs --out backend/ai/models/boneage_digibone.onnx
```

The converter asserts parity against the PyTorch model on ≥100 **real
radiographs** (max abs diff < 1e-3 months, i.e. an arithmetic-equivalence check,
not a clinical-agreement one). **A conversion that silently changes the numbers
is worse than no conversion**: the published accuracy, the conformal calibration
and the release-gate decision would all be attached to a model that is not the
one that ran. Synthetic noise is rejected — it exercises a different part of the
input distribution than hands do, and a bug in an interpolation or padding op can
be invisible on noise and material on radiographs.

The state dict is loaded strictly; a key mismatch is refused rather than
tolerated, because silently-ignored keys leave layers randomly initialised and
still produce plausible-looking bone ages.

**On unpickling:** torch checkpoints are pickles, and loading one executes
whatever it contains — here, a file from a third-party release page, on a machine
holding patient data. The converter uses `weights_only=True`. If digiBONE's
checkpoint needs the unsafe loader, verify the download against the published
checksum first and pass `--allow-arbitrary-pickle` deliberately.

### 3. Registry metadata — written for you

The converter writes `boneage_digibone.json` beside the ONNX, carrying
`method_key`, `population`, `input_size`, the `preprocessing_version` used at
conversion time, the MIT licence and citation, the measured parity result, and
digiBONE's published MAD figures (so a later reader can tell the *claimed*
accuracy from the *measured* one).

It deliberately writes **no** `conformal` block. Quantiles do not transfer
between models, and `registry.resolve_interval_policy` withholds intervals for
an uncalibrated model — the correct state until step 5.

`preprocessing_version` is **not optional**: that same function refuses to serve
conformal intervals when it does not match the active pipeline, which is the
check that stops a preprocessing change from silently invalidating calibration.

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

### 7. Switch inference to it

```bash
PCW_BONEAGE_MODEL=boneage_digibone
```

A deployment variable, not an in-app setting: which model reads a radiograph
must be identical for every user of an installation and must not be changeable
by someone who has not run the release gate.

Selection is validated. An id that is not registered, or whose `.onnx` is
missing, **falls back to the incumbent and says so** — visible on
`GET /api/bone-age/config` under `active_model.fell_back`. A typo must not
silently disable screening, nor silently promote something nobody validated.

Confirm the switch took effect there rather than assuming it: `active_model`
reports `model_id`, `method`, `population` and the reason for the current
selection.

#### What step 7 had to fix first

`boneage.py` hardcoded `models/boneage_gp.onnx` and the registry's default id, so
steps 1–6 could all be completed and **the incumbent would still have answered
every request**. The response's `method` and `population_note` were constants
too — an Indian-trained segmental model would have been labelled a US-trained
whole-image one, and the note telling a clinician how far to trust the number
would have described a different model. Both now come from the model's own spec.

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
