# Pediatric Clinical Workspace

Local FastAPI + static browser workspace for growth calculations and bone-age
image uploads.

## Important Medical Boundary

The included bone-age estimator is a free local research baseline. It verifies
that the upload and inference pipeline works, but it is not a validated
Greulich-Pyle, TW3, FDA-cleared, or CE-marked model. Use it for prototype and
workflow testing only. A clinician must verify all patient-facing results.

## Project Structure

```text
backend/
  local_bone_age.py  local baseline inference and synthetic self-test image
  server.py          FastAPI app, API routes, static serving
frontend/
  index.html         Browser UI
bone_age_server.py   backward-compatible server entrypoint
requirements.txt     Python dependencies
```

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
