# Pediatric Clinical Workspace

Local FastAPI + static browser workspace for growth calculations and bone-age
image uploads.

## Intended use and known limitations (read before clinical use)

**Clinician-supervised decision support for paediatric practice in India. Not a
diagnostic device;** not FDA-cleared, CE-marked or CDSCO-registered. Every
patient-facing result must be verified by a qualified clinician. Not for use by
patients or parents.

Known limitations, measured rather than assumed:

- **Bone age is not Tanner TW3.** The active TW3-C curve comes from a conference
  paper (points from its Table 1, score→age digitised from a figure, ±0.5 y) and
  differs from this centre's historical TW3 reports by ~0.9–1.25 y. The licensed
  TW3 book fixes this (`backend/tw3/TW3-BOOK-REQUEST.md`).
- **The AI bone-age estimate is a Greulich–Pyle screening cross-check**, below
  its own release gate (locked RSNA test MAE 8.99 months; limits of agreement
  about ±2 years), trained on US data, never validated on Indian children. It can
  never be entered as the TW3 bone age.
- **Reference data:** see the Overview tab → "Reference data behind these
  numbers" (live) and `validation/REFERENCE-DATA-ACTION-PACK.md`. Anything missing is
  refused, not approximated — e.g. no BP category under 13, no velocity centiles.
- **QRISK3 is UK-derived** and may under-estimate risk in Indian adults.
- **FRAX is not calculated here**; the official calculator's result is entered.

Where things stand and what needs a person: `validation/REFERENCE-DATA-ACTION-PACK.md`.

## Security (read before any real patient data)

**Authentication is OFF by default** — a deliberate product decision: the
workspace has no sign-in screen. Approvals are therefore attributed to
`dev-no-auth`, and anyone using this computer can read and change records.
Because of that, the network boundary is the security boundary, and the app
enforces it itself (`backend/security/network_guard.py`):

- **This computer only.** With authentication off, any request that does not
  come from this machine is refused — whatever address the server was started on.
- **Known hosts only.** Requests must be addressed to `localhost`, `127.0.0.1` or
  `::1`, which defeats DNS-rebinding attacks from a web page the clinician visits.
- **No cross-site writes.** State-changing requests from another web origin (or
  that the browser marks cross-site) are refused.
- **Browser hardening.** Content-Security-Policy (no third-party scripts, no
  framing), `nosniff`, no referrer, and `no-store` on every API response so
  patient data is not left in the browser cache.
- **No patient identifiers in URLs.** PDF export and patient lookup send the
  name/MRN in the request body, so they never reach access logs or history.

To serve a clinic network you must turn authentication back on
(`PCW_AUTH_ENABLED=1`), add a sign-in screen, create accounts
(`python -m backend.security.bootstrap --username drname --role doctor`), put TLS
in front, and list the LAN host name in `PCW_ALLOWED_HOSTS`.

**Encrypt patient names at rest.** Generate a key and keep it **outside the app
folder** (another drive, a USB key, an admin-only folder), then point the app at
it — otherwise a copied folder carries both the database and its key:

```bash
python -m backend.security.crypto > D:/pcw-secret/pcw.key
# in .env:  PCW_ENCRYPTION_KEY_FILE=D:/pcw-secret/pcw.key
```

`GET /api/health` reports the posture (`auth_enabled`, `encryption_at_rest`,
`encryption_key_source`) and lists every warning, including a key stored inside
the app folder. Back up the key separately from the database: without it the
names cannot be decrypted.

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
  server.py          FastAPI app, API routes, static serving
  api_*.py           route modules, one per clinical domain
  ai/                screening model, training and validation harness
  growth/            WHO/IAP growth engine and reference data
  tw3/               TW3-RUS scoring, tables, report pipeline
  clinical/  cvd/  security/  monitoring/
frontend/
  index.html         HTML shell (no application logic)
  src/               React/JSX application source — EDIT HERE
  app.js             built bundle, COMMITTED (generated; do not edit)
  app.css            Tailwind 3.4.16 output, COMMITTED (generated by build.mjs)
  vendor/            React + ReactDOM, vendored for offline use
validation/          clinical vignettes, validation protocol, release checklist,
                     reference-data request pack
datasets/            local image corpora — gitignored, never committed
build.mjs            esbuild + Tailwind build for the frontend
package.json         frontend build tooling (esbuild, Tailwind)
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
python -m backend.server
```

Open http://127.0.0.1:8077/. No API key is required, and every image is
processed locally by the backend.

Two optional extras, neither needed to see the app work:

```powershell
python -m playwright install chromium     # only for the printable PDF report
python -m pip install -r requirements-dev.txt ; python -m pytest
```

### What gets installed, and why that is all

| File | Packages | Size | For |
|---|---|---|---|
| `requirements.txt` | 29 | 456 MB | running the workspace |
| `+ requirements-dev.txt` | 40 | 488 MB | running the tests |
| `requirements-ml.txt` | +620 MB | separate env | RETRAINING the bone-age model only |

Every runtime package is exactly pinned, and every one of them is imported by
code the server can reach: `tests/test_dependency_closure.py` fails the build if
something is declared but unused, or imported but undeclared. PyTorch is not a
runtime dependency -- the shipped model runs through `onnxruntime`, and a clean
install answers every endpoint, AI bone-age estimate included.

**The end user needs no Node.js.** `frontend/app.js` and `app.css` are committed,
and `package.json` has zero production dependencies; esbuild and Tailwind are
build tools for developers changing `frontend/src/`.

## Deployment

**This application is local-first and is not supported on a public host.** The
old `render.yaml` / `Procfile` / `runtime.txt` (a free public host, bound to
0.0.0.0) were removed in step 6; with authentication off, the network guard would
refuse every remote request anyway.

The blockers are specific rather than theoretical:

- the server binds `127.0.0.1` by design and has no TLS of its own;
- session cookies are only marked `Secure` when the request is not plain
  localhost, so a public deployment must terminate TLS in front of the app;
- the encryption key would sit on the same host as the database, which protects
  a copied database but not a compromised host;
- a public instance is exposed to credential stuffing, and the lockout here is
  per-account rather than per-IP.

For a single clinic, run it on the clinic machine. If a networked deployment is
ever needed, it requires TLS, a reverse proxy with rate limiting, key management
separate from the database, authentication turned back on, and a fresh security
review.

### Release readiness

Before installing a copy for clinical use:

```bash
python -m backend.release_check --tests
```

It reports PASS / WARN / FAIL for the bundle, growth validation, reference data,
the golden clinical vignettes and their clinician sign-off, encryption at rest,
authentication, runtime licences, the AI model and source control, and exits 1
on any blocker. It only reads state. The human steps it cannot do are in
`validation/RELEASE-CHECKLIST.md`, and the per-module evidence is in
`validation/VALIDATION-PROTOCOL.md`.

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
