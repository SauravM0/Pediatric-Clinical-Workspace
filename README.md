# Pediatric Clinical Workspace

Local FastAPI + static browser workspace for growth calculations and bone-age
image uploads.

## Important Medical Boundary

Decision support only — not a diagnostic device. A clinician must verify all
patient-facing results.

The included bone-age *image* estimator is a free local research baseline. It
verifies that the upload/inference pipeline works, but it is **not** a validated
FDA-cleared or CE-marked model. Use it only as a labelled suggestion for the
TW3 bone-age field; never as an authoritative reading.

## Bone Age & Adult Height (TW3 only)

Bayley–Pinneau and Greulich–Pyle have been **removed**. Bone age uses the
**Tanner–Whitehouse 3 (TW3) RUS** method only: stage the 13 RUS bones (A→I),
sum to the RUS maturity score, convert to bone age.

**Calibration required.** The TW3 per-stage point-scores and the
RUS-score→bone-age and %-of-adult-height tables are copyrighted (Tanner, Healy,
Goldstein & Cameron, 2001) and are **not** bundled — no values are invented. A
TW3-licensed clinician must enter them once into the `TW3_CONFIG` object near the
top of the `<script>` block in `frontend/index.html`:

- `stageScores[sex][boneKey][stage]` — RUS points per bone per stage.
- `scoreToAge[sex]` — ascending `[rusScore, boneAgeYears]` anchor points.
- `pctAdultHeight[sex]` — ascending `[boneAgeYears, %adultHeightAttained]` anchors.

Until populated, the app shows the RUS staging framework and a
"calibration required" notice instead of a fabricated bone age or skeletal
height prediction. **Adult-height prediction** works today via the open,
non-proprietary **mid-parental (Tanner) target height**; the TW3 skeletal
prediction activates once `pctAdultHeight` is supplied. All results are
contextualised against the Indian Khadilkar (WHO-IAP) 18-year reference.

## Cardiovascular Risk — QRISK3

The **QRISK3-2017** 10-year CVD risk calculator (Hippisley-Cox et al., BMJ 2017)
is implemented from the ClinRisk open-source coefficients (GNU LGPL, released for
faithful reimplementation). It defaults to **Indian** ethnicity and exposes the
South-Asian ethnicity terms. Validated for ages 25–84.

Correctness is checked against the algorithm's own published test vectors
(e.g. white male age 75 → 24.6%, Indian male age 75 → 31.1%, Indian female age
75 → 23.2%, and the multi-factor cases q1 = 64.8% / q4 = 81.9%); the
implementation reproduces all of them.

India caveat: QRISK3 is UK-derived. Its Indian ethnicity term raises risk vs
White but may still under-estimate true Indian risk — interpret alongside the
Lipid Association of India (LAI) stratification and ICMR guidance. Townsend
deprivation is fixed at 0 (a UK-only index).

## Project Structure

```text
backend/
  local_bone_age.py  local baseline inference and synthetic self-test image
  server.py          FastAPI app, API routes, static serving
frontend/
  index.html         HTML shell (no application logic)
  src/               React/JSX application source — EDIT HERE
  app.js             built bundle, COMMITTED (generated; do not edit)
  vendor/            React + Tailwind, vendored for offline use
build.mjs            esbuild build for the frontend
package.json         frontend build tooling (esbuild only)
bone_age_server.py   backward-compatible server entrypoint
requirements.txt     Python dependencies
```

## Frontend Build

The browser app is written in JSX under `frontend/src/` and compiled to
`frontend/app.js` by esbuild.

**Running the app needs no Node.** `frontend/app.js` is committed, so a fresh
clone starts with the single `uvicorn` command above and works fully offline.
Node is only needed to *change* the frontend.

```bash
npm install
npm run build
```

Other commands: `npm run watch` rebuilds on change; `npm run check` verifies the
committed bundle matches `frontend/src/` and is what CI enforces.

**After editing anything in `frontend/src/`, run `npm run build` and commit the
regenerated `frontend/app.js`.** The browser executes `app.js`, so a stale
bundle means the reviewed source is not what runs.
`tests/frontend/test_build_artefact.py` fails if the two have drifted.

This replaced in-browser Babel transpilation: the app previously shipped as
`<script type="text/babel">` alongside a 3.1 MB Babel bundle that re-compiled
~4,000 lines of JSX on every page load.

## Run Locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn backend.server:app --reload --port 8077
```

Open http://127.0.0.1:8077/.

No API key is required. Images are processed locally by the backend.

## Deploy Free On Render

1. Push this folder to a GitHub repository.
2. In Render, choose **New +** then **Blueprint** and select the repository.
3. Render will read `render.yaml` automatically.
4. After deploy, open:

```text
https://your-render-app.onrender.com/api/health
https://your-render-app.onrender.com/api/self-test
```

If you create a plain Web Service instead of a Blueprint, use:

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn backend.server:app --host 0.0.0.0 --port $PORT
```

Render free services may sleep when idle. Do not upload identifiable patient
X-rays to a public/free host.

## API

- `GET /api/health` checks backend availability and local model status.
- `GET /api/self-test` runs a synthetic hand-wrist image through inference.
- `POST /api/bone-age` accepts multipart form fields:
  - `file`: hand/wrist X-ray image
  - `sex`: `boys`, `girls`, or `unspecified`
  - `chronological_age`: optional decimal age in years

## Upgrading To A Real Local Model

The clean integration point is `backend/local_bone_age.py`. Replace the
`local-baseline-v1` path with an ONNX/PyTorch adapter once trained RSNA-style
bone-age weights are available. Validate against your own radiologist-read
cases before considering clinical use.
