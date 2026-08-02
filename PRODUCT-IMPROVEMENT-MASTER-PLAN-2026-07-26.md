# Product Improvement Master Plan

**Date:** 26 July 2026
**Companion to:** `GROWTH-AND-BONE-AGE-DIAGNOSIS-AND-ROADMAP-2026-07-26.md` (the diagnosis)
**This document:** the full improvement register, and the step-wise build plan
**Verified against:** live code, executed probes, 243 passing tests, hardware check

---

## 0. The direct answer: what is your next step

**Build the measurement history table.**

Not the growth charts. Not the bone age. Those are what you asked about, and they matter —
but I found something underneath both of them while auditing the data model, and it changes
the order of everything.

**Your product does not store a single growth measurement.** I checked the ORM: there are
nine tables, and none of them is an observation/measurement table. `/api/growth/point` takes
age and value as URL query parameters, returns a z-score, and throws it away. The `Patient`
table holds exactly four clinical facts: code, name, sex, date of birth.

This one gap blocks almost everything you asked me for:

| You asked for | Why it's blocked today |
|---|---|
| "doctor will know everything about the patient" | There is nothing to know — no measurement is ever saved |
| More accurate growth assessment | Velocity needs two measurements over time. You have zero |
| "more perfect predictions on his health" | Prediction needs a trajectory, not a single dot |
| Help the patient decide whether to see another doctor | Referral logic is driven by *change over time*, not one number |
| Save the doctor time | The doctor re-types everything at every visit |

**A single height measurement is nearly uninformative. The trajectory is the diagnosis.**
A child on the 3rd centile who has always been on the 3rd centile is probably a normal short
child. A child who has fallen from the 50th to the 3rd is a serious endocrine work-up. Your
product currently cannot tell those two apart, and that distinction is most of paediatric
growth medicine.

So: **Phase 0 is the data model.** It is 3–4 days of unglamorous work and it unlocks
Phases 1 through 6. Everything else in this plan assumes it exists.

---

## 1. The improvement register

You asked me to loop until I had found everything. I swept the codebase systematically by
area. **68 items.** Severity: 🔴 blocks accuracy or safety · 🟡 material · 🟢 polish.

### A. Data foundation — 7 items

| # | Item | Sev |
|---|---|---|
| A1 | **No measurement/observation table.** Growth is entirely stateless | 🔴 |
| A2 | `Patient` lacks parental heights, gestational age, birth weight, conditions, medications | 🔴 |
| A3 | No visit/encounter model — cannot group findings by consultation | 🟡 |
| A4 | No Tanner/pubertal staging capture (B/G, PH, testicular volume, menarche) | 🔴 |
| A5 | No lab-result storage (IGF-1, TSH, coeliac screen, karyotype) | 🟡 |
| A6 | **No authentication of any kind**, yet `render.yaml`/`Procfile` exist for public deploy, and `Patient.name` is stored in plaintext | 🔴 |
| A7 | Clinician identity is a free-text `reader_id` string — not a user account, so attribution is unverifiable | 🟡 |

### B. Growth chart accuracy — 17 items

| # | Item | Sev |
|---|---|---|
| B1 | **IAP 2015 L,M,S never obtained** — root cause of B3, B4, B7, B8 | 🔴 |
| B2 | **0 of 1,134 CSV cells verified** against the paper | 🔴 |
| B3 | Weight/BMI tail bias up to **0.8 SD**; true −3.0 SD reported as −2.6 | 🔴 |
| B4 | Unbounded linear extrapolation → z = −12.9 for a 40 cm 6-year-old | 🟡 |
| B5 | 3.0–5.0y is a **product-invented** quintic bridge, 2 full years | 🔴 |
| B6 | **No height-velocity reference at all** — the most sensitive growth indicator | 🔴 |
| B7 | BMI P75/P90/P97 fitted from lower-half-only published data | 🟡 |
| B8 | Height/weight L,S splines unsmoothed (`smooth_ls=False`); only BMI is smoothed | 🟡 |
| B9 | Stale docstrings say blend window is 4.0–5.0y; constant is 3.0 | 🟢 |
| B10 | WHO weight-for-age undefined >10y — silent fallback, not surfaced to user | 🟡 |
| B11 | **No head circumference.** Essential 0–3y (microcephaly, hydrocephalus) | 🔴 |
| B12 | No preterm/corrected age (Fenton / INTERGROWTH-21st) | 🟡 |
| B13 | No syndrome-specific charts (Turner, Down, achondroplasia) | 🟡 |
| B14 | No sitting height / US:LS ratio / arm span → cannot detect **disproportionate** short stature | 🔴 |
| B15 | Mid-parental height not stored, not drawn on the chart as a target corridor | 🟡 |
| B16 | `rcpchgrowth` is **AGPL-3.0** — network use triggers source-disclosure duty | 🟡 |
| B17 | Chart series rebuilt per (measure,sex) at 2–3s; `lru_cache`d, but cold start is slow | 🟢 |

### C. Bone age accuracy — 15 items

| # | Item | Sev |
|---|---|---|
| C1 | **It is not TW3.** TW3-C points lifted from a DL conference paper's Table 1 | 🔴 |
| C2 | score→age curve **digitized off Figure 8**; 10–11 anchors; piecewise linear | 🔴 |
| C3 | **Silent clamp**: any score below the first anchor returns exactly 6.00y | 🔴 |
| C4 | Licensed TW3 tables absent (correctly gated, but blocks the whole deterministic path) | 🔴 |
| C5 | AI model **MAE 8.99 mo**, gate FAIL (≤6.0), LoA **−23.8 to +22.1 mo** | 🔴 |
| C6 | No Indian validation cohort | 🔴 |
| C7 | No per-bone localizer or stager model actually installed — scaffolding only | 🟡 |
| C8 | Carpal scoring entirely absent | 🟡 |
| C9 | Letter stages offer A–I for every bone; real TW3 constrains stage sets per bone | 🟡 |
| C10 | Quality gate auto-detects only 2 of 16 flags; fracture/rotation/exposure rely on clinician declaration | 🟡 |
| C11 | No adult-height prediction from bone age (needs licensed %-adult-height tables) | 🟡 |
| C12 | **No prior-film comparison.** Bone age *velocity* is diagnostic and unavailable | 🟡 |
| C13 | **Preprocessing is min–max normalise only** — no CLAHE, no hand segmentation, no background masking. This is where image accuracy is won | 🔴 |
| C14 | Analysis image capped at 1024px then fed at 224px — too coarse for per-bone staging | 🟡 |
| C15 | Bone age reported without the **method's own error band** alongside the conformal band | 🟢 |

### D. Clinical intelligence — 12 items

| # | Item | Sev |
|---|---|---|
| D1 | No red-flag / differential engine | 🔴 |
| D2 | No referral logic (the thing you specifically asked for) | 🔴 |
| D3 | No treatment-response monitoring (GH therapy tracking) | 🟡 |
| D4 | No adult-height prediction at all (only mid-parental *target*, which is a different quantity) | 🔴 |
| D5 | No bone-age-conditioned growth interpretation (height-for-bone-age) | 🔴 |
| D6 | No BP centiles by height | 🟡 |
| D7 | No puberty-timing assessment (precocious / delayed) | 🟡 |
| D8 | No lab interpretation or suggested work-up panel | 🟡 |
| D9 | No obesity work-up prompts despite already computing IOTF 23/27 cut-offs | 🟡 |
| D10 | No nutrition/anaemia screening integration | 🟢 |
| D11 | No growth-prediction confidence communicated to the patient | 🟡 |
| D12 | No "what changed since last visit" summary | 🟡 |

### E. Workflow & doctor time — 9 items

| # | Item | Sev |
|---|---|---|
| E1 | No patient search / worklist in the growth flow | 🟡 |
| E2 | Everything re-typed each visit (parental heights, history) | 🟡 |
| E3 | No batch/bulk radiograph processing | 🟢 |
| E4 | No keyboard-first rapid staging for the 13/20 bones | 🟡 |
| E5 | No visit templates or common-case shortcuts | 🟢 |
| E6 | No copy-paste-ready clinical note output | 🟡 |
| E7 | No parent-facing summary (you have a bilingual Marathi skill unused here) | 🟡 |
| E8 | No offline/PWA mode for low-connectivity clinics | 🟢 |
| E9 | Cold-start chart build 2–3s per measure/sex — precompute at boot | 🟢 |

### F. Safety, privacy, compliance — 8 items

| # | Item | Sev |
|---|---|---|
| F1 | No auth, no RBAC | 🔴 |
| F2 | No encryption at rest; SQLite file with patient names | 🔴 |
| F3 | No India **DPDP Act 2023** alignment (consent, retention, breach duty) | 🔴 |
| F4 | Consent field exists on `Radiograph` but no consent workflow in UI | 🟡 |
| F5 | DICOM de-identification asserted but not verified against a tag allowlist | 🟡 |
| F6 | No data-retention or deletion policy | 🟡 |
| F7 | AGPL obligation (see B16) | 🟡 |
| F8 | No documented Intended Use / limitations statement as a product artefact | 🟡 |

**Strengths to preserve** — do not refactor these away: audit log, checksum locking,
gated model releases with human sign-off, split-conformal uncertainty, abstention on hard
image flags, adjudication queue, leak-guarded locked test set, 243 passing tests.

---

## 2. The step-wise plan

Sequenced so each phase unblocks the next. Estimates assume **one developer, no GPU, no
budget** — which is what you have (I checked: `torch 2.12.1+cpu`, no CUDA; the existing
model was trained on Colab).

---

### Phase 0 — Data foundation · ~1 week · 🔴 do this first

**Goal:** the product remembers patients.

| WI | Work item | Days |
|---|---|---|
| 0.1 | `Observation` table: patient_id, date, age_months, type (height/weight/hc/sitting_height/arm_span/BP), value, unit, measured_by, method, notes | 1.5 |
| 0.2 | Extend `Patient`: mother_height_cm, father_height_cm, gestational_age_weeks, birth_weight_g, birth_length_cm, ethnicity, conditions[], medications[] | 0.5 |
| 0.3 | `PubertyAssessment` table: date, breast/genital stage, pubic hair stage, testicular volume ml, menarche date | 0.5 |
| 0.4 | `Encounter` table to group observations + assessments per visit | 0.5 |
| 0.5 | Migration + schema version bump; backfill nothing (fresh) | 0.5 |
| 0.6 | `/api/patients/{id}/observations` CRUD; wire growth chart to plot **all** stored points | 1.5 |
| 0.7 | Duplicate-measurement guard and implausible-value guard (e.g. height decreasing >1 cm) | 0.5 |

**Acceptance:** enter a patient, record three visits six months apart, reload the app, see
all three points plotted on the chart with the trajectory joined.

**Why first:** Phases 1.4 (velocity), 3 (intelligence), 4 (referral), 5 (time-saving) are
all impossible without it.

---

### Phase 1 — Growth chart accuracy · ~2 weeks · 🔴

**Goal:** every displayed number traceable to a published reference, exactly.

| WI | Work item | Days | Fixes |
|---|---|---|---|
| 1.1 | **Email IAP Growth Charts Committee / HCJMRI for the IAP 2015 L,M,S triplets.** Cite Khadilkar 2021 JPEM (doi 10.1515/jpem-2020-0573), which states it used them | 0.1 | B1 |
| 1.2 | If LMS arrives: replace the fit-and-interpolate layer with direct Cole LMS. Delete `_z_from_display_anchors`, `_EXACT_TABLE_GUARD`, `table_fns`, the L/S smoothing debate | 2 | B1,B3,B7,B8 |
| 1.3 | If LMS does *not* arrive: fix the tails anyway — LMS-based extrapolation beyond P3/P97, and clip/flag z outside ±5 | 1 | B3,B4 |
| 1.4 | **Add Indian height-velocity chart** (Khadilkar, Indian Pediatr 2019;56:23–8). Enforce ≥6-month interval; show velocity SDS | 2.5 | B6 |
| 1.5 | **Add head circumference** 0–3y (WHO) | 1 | B11 |
| 1.6 | **Add sitting height / US:LS ratio / arm span** with Indian references (Khadilkar multicentre sitting-height percentiles 3–17y; Pune US:LS birth–18y). Flag disproportion | 2 | B14 |
| 1.7 | Decide the 3–5y policy: **recommend switching at 5.0y to match official IAP**, and disclosing the step. If keeping the bridge, shade + label the band and exclude it from threshold decisions | 1 | B5 |
| 1.8 | Mid-parental height stored, and drawn as a target corridor on the chart | 0.5 | B15 |
| 1.9 | Complete the 1,134-cell dual verification (skip if 1.2 lands) | 3 | B2 |
| 1.10 | Vendor WHO LMS tables; drop `rcpchgrowth`; removes AGPL *and* both internal WHO seams | 2 | B16,B10 |
| 1.11 | Fix stale docstrings; precompute chart series at boot | 0.5 | B9,B17 |

**Acceptance:** a regression test asserts every displayed centile equals the published
reference to 1e-9; z-score round-trips exactly at ±3 SD for all measures.

---

### Phase 2 — Bone age: honesty and image accuracy · ~3 weeks · 🔴

Split deliberately into *stop overstating* (days) and *get more accurate* (weeks).

#### 2A — Truth in labelling (do in the first 2 days)

| WI | Work item | Days | Fixes |
|---|---|---|---|
| 2.1 | Relabel every bone-age surface: *"TW3-C (Chinese) RUS — provisional research curve, ±0.5y, digitized. Not Tanner TW3."* UI, PDF, API response | 1 | C1 |
| 2.2 | **Clamp guard**: refuse a bone age when RUS score is below the first anchor; return `status: "outside_curve_domain"` instead of a silent 6.00y | 0.5 | C3 |
| 2.3 | Constrain letter stages per bone once the licensed source arrives; until then mark unverified in the UI, not just in a constant's docstring | 0.5 | C9 |

#### 2B — Image accuracy (the real win)

| WI | Work item | Days | Fixes |
|---|---|---|---|
| 2.4 | **Adopt digiBONE** (MIT, `github.com/goellab/digiBONE`) — Indian-trained on 2,430 HCJMRI Pune films, 4.75/4.93 mo. Run against your existing locked RSNA test first for an apples-to-apples number vs your 8.99 mo | 4 | C5 |
| 2.5 | **Preprocessing pipeline**: CLAHE, hand segmentation + background masking, rotation normalisation. ~~Buys 1–2 months of MAE~~ — **measured: only with retraining; retro-fitting it to the incumbent made MAE 3.7× worse.** Built and versioned in M4, inactive pending a model that declares it | 3 | C13 |
| 2.6 | Raise analysis resolution: keep a 2048px derivative for per-bone crops; 224px whole-hand is fine for screening but not for staging | 1 | C14 |
| 2.7 | Integrate **BoNet** (`BCV-Uniandes/Bonet`) for per-bone ROI localisation → feeds the per-bone UI you already built | 4 | C7 |
| 2.8 | Re-calibrate conformal intervals on the new model; keep the release gate and human sign-off | 1 | C5 |
| 2.9 | **Bone-age velocity**: compare against the patient's prior film (needs Phase 0) | 1 | C12 |
| 2.10 | Auto-detect more quality flags (rotation, exposure, clipping) — classical CV first, not ML | 2 | C10 |

#### 2C — Deterministic path (blocked on external inputs, start the clock now)

| WI | Work item | Days | Fixes |
|---|---|---|---|
| 2.11 | **Buy one licensed copy of Tanner et al. 2001 (TW3).** Unblocks real RUS points, real score→age, carpal, and %-adult-height. Your transcription gates are already built to receive it | — | C4,C8,C11 |
| 2.12 | Dual-transcribe TW3 RUS + Carpal into `letters_tables.json`; fill `provenance`; enter 3+ reference cases; let `validate_curve()` clear the provisional flag on evidence | 4 | C2,C4 |
| 2.13 | **Build the Indian validation cohort**: 200–300 local films, two independent expert reads each, frozen, stratified by sex × pubertal status | ongoing | C6 |

> **On C2:** once real TW3 tables exist, replace the 10-anchor linear curve with the
> published table at native resolution and monotone interpolation. Until then, 2.1 + 2.2
> keep it honest.

---

### Phase 3 — Clinical intelligence · ~2 weeks · 🟡

**Goal:** the doctor sees interpretation, not just numbers.

| WI | Work item | Days |
|---|---|---|
| 3.1 | **Khamis–Roche adult height prediction** — no X-ray needed, ~90% within ±5.3 cm, coefficients freely published. Present as clearly distinct from mid-parental *target* height | 2 |
| 3.2 | **Height-for-bone-age** overlay: plot the child at their bone age, not just chronological age. Distinguishes constitutional delay from true pathology | 2 |
| 3.3 | **Conditional SDS** (Cole method): the statistically correct "has this child's growth actually changed?", correcting for regression to the mean | 2 |
| 3.4 | **Red-flag engine** (rules, transparent, each citing its source) | 3 |
| 3.5 | **Visit delta summary**: what changed since last visit, in one paragraph | 1 |
| 3.6 | BP centiles by height (you already have the height-z machinery) | 1.5 |
| 3.7 | Puberty timing assessment: precocious / delayed / on-track vs Indian norms | 1.5 |
| 3.8 | Obesity work-up prompts off the IOTF 23/27 cut-offs you already compute | 1 |

**Red-flag rules to ship in 3.4** (all published, all explainable):

- Height SDS < −2 → short stature; < −3 → severe, high probability of pathology
- Height velocity < 25th centile sustained over ≥1 year
- Crossing centiles **downward** after age 3
- Height SDS more than 2 SD below mid-parental target
- IUGR/SGA without catch-up by age 2
- **Disproportion** (abnormal US:LS or arm-span−height) → skeletal dysplasia, not endocrine
- BMI ≥ IOTF-23 equivalent with acanthosis → metabolic work-up
- Bone age − chronological age > 2 years in either direction
- Girls: no breast development by 13, or menarche by 8 → endocrine referral
- Boys: no testicular enlargement by 14 → endocrine referral

Every fired rule must show **why it fired, with the number and the source**. A silent score
is not decision support; a stated reason is.

---

### Phase 4 — Referral intelligence (patient-facing) · ~1 week · 🟡

This is the part you described as *"help him decide to go to a different doctor to check if
the problem is serious or minor."* Handle it carefully — this is the highest-risk feature in
the whole product.

| WI | Work item | Days |
|---|---|---|
| 4.1 | **Triage output**, three levels only: *routine monitoring* / *discuss with your paediatrician* / *see a specialist soon* | 2 |
| 4.2 | Specialty routing: endocrinology, genetics, orthopaedics, gastroenterology (coeliac), nutrition — with the reason | 1.5 |
| 4.3 | Parent-facing plain-language summary, Hindi/Marathi/English | 2 |
| 4.4 | "Questions to ask your doctor" generated from the fired flags | 0.5 |

**Design rules — non-negotiable:**

1. **Never output a diagnosis to a patient.** Output *observations* and *a suggested
   conversation*. "Your child's height is below the 3rd centile and has been falling — this
   is worth discussing with a paediatrician" — not "your child may have growth hormone
   deficiency."
2. **Never say "this is minor."** You can say something needs *routine monitoring*; you
   cannot rule out seriousness from anthropometry. Under-triage is the failure mode that
   harms patients and destroys trust.
3. **Always route toward a clinician, never away from one.**
4. Gate patient-facing output behind clinician release, at least at first.

---

### Phase 5 — Doctor time · ~1 week · 🟡

| WI | Work item | Days |
|---|---|---|
| 5.1 | Patient worklist + search; open a patient and see everything on one screen | 2 |
| 5.2 | Keyboard-first bone staging (number keys 1–8, auto-advance) — turns a 3-minute task into 40 seconds | 1.5 |
| 5.3 | Copy-paste-ready clinical note (structured text) | 1 |
| 5.4 | One-click combined PDF: growth + bone age + interpretation + red flags | 1.5 |
| 5.5 | Pre-fill from last visit; only deltas need typing | 1 |

**The realistic time claim:** a growth consultation that takes 8–10 minutes of measuring,
plotting, calculating and writing should drop to 2–3 minutes. Say that. Do not claim more.

---

### Phase 6 — Multi-specialty expansion · ~2 weeks · 🟢 (after accuracy is solved)

Bone age is genuinely multi-specialty — this is your strongest expansion path, and it needs
**no new imaging**, just different outputs from the same film.

| Specialty | What they need | Build |
|---|---|---|
| **Paediatric orthopaedics** | Remaining growth, surgical timing for scoliosis, epiphysiodesis timing for limb-length discrepancy | Remaining-growth estimate from bone age; Sanders/Risser staging |
| **Orthodontics** | Timing of growth-modification appliances (functional appliances only work near peak velocity) | Cervical vertebral maturation, or hand-wrist maturity → "peak growth window: now / passed / not yet" |
| **Sports medicine** | Biological vs chronological maturity; injury risk; fair-play age banding | Maturity offset, % of predicted adult height attained |
| **Paediatric surgery / gastro / nephro** | Growth failure as a disease marker | The Phase 3 red-flag engine already covers this |
| **Neonatology** | Preterm corrected-age growth | B12 (Fenton / INTERGROWTH-21st) |

**Do not start Phase 6 before Phases 1 and 2 are done.** Selling an inaccurate bone age to
three more specialties multiplies the problem instead of the product.

---

### Continuous — safety and compliance · 🔴 before any real patient data

| WI | Work item |
|---|---|
| C.1 | Authentication + roles (doctor / assistant / admin). Currently there is none |
| C.2 | Encryption at rest; separate identifiers from clinical data |
| C.3 | **DPDP Act 2023** alignment: consent capture, purpose limitation, retention, deletion, breach process |
| C.4 | DICOM de-identification verified against an explicit tag allowlist |
| C.5 | Written Intended Use + limitations statement as a shipped artefact |
| C.6 | Keep the 243 tests green; every phase adds its own regression tests |

**Hard rule:** do not deploy to Render, or any public host, until C.1–C.3 are done. The
`Patient` table stores names and there is no login.

---

## 3. Accuracy deep-dive: the two features you care most about

### 3.1 How the growth chart actually becomes accurate

Four layers, in order. Each is verifiable.

1. **Source truth** — the LMS values, or a dual-verified table. *Verify:* engine output
   equals published value to 1e-9 at every published (age, centile).
2. **Correct maths** — Cole LMS transform. You already use a tested implementation.
   *Verify:* z→value→z round-trips to 1e-9 across −4…+4 SD.
3. **Honest interpolation** — no invented segments; monotone interpolation only between
   real anchors. *Verify:* no rendered point comes from a synthetic construction, or if it
   does, it is visually and textually labelled.
4. **Correct clinical framing** — distance chart *and* velocity chart; SDS *and* conditional
   SDS; chronological age *and* bone age. *Verify:* review against Indian reference values.

**This layer can reach 100%, and you should hold it to 100%, not 99%.** It is deterministic
arithmetic on a published table. You have already proved you can do this — QRISK3 reproduces
its published test vectors exactly. Copy that pattern.

### 3.2 How the bone age actually becomes accurate

Two independent paths. **Keep them separate and never average them** — they are different
constructs measured against different reference populations.

**Path A — deterministic (manual staging → score → age)**

Accuracy ceiling is set entirely by (i) the table's correctness and (ii) inter-observer
staging agreement. Actions: 2.11 → 2.12 → validate with local reference films. With real
TW3 tables and a trained reader, expect ±0.5y. **Currently uncapped** because the curve is
a digitized figure.

**Path B — AI screening (image → age)**

| Step | Expected MAE | Cost |
|---|---|---|
| Today (MobileNetV3-S, 224px, RSNA) | 8.99 mo | — |
| + preprocessing: CLAHE, segmentation, masking (2.5) | ~~~7–7.5 mo~~ **corrected — see below** | free, 3 days |
| + digiBONE, Indian-trained (2.4) | **~4.8 mo** | free, 4 days |
| + fine-tune on your own Indian films (2.13) | ~4–4.5 mo | needs the cohort |
| + ensemble digiBONE ⊕ Deeplasia | ~3.8–4.2 mo | free, more compute |

> **CORRECTION (measured during M4).** The 7–7.5 mo estimate was wrong. Applying
> the new preprocessing to the *existing* model, measured on 200 images of the
> locked RSNA test set (seed 42):
>
> | pipeline | MAE | within 12 mo |
> |---|---|---|
> | `prep-1.0-minmax` (incumbent) | **8.92 mo** | 75.5% |
> | `prep-2.0-clahe-seg` | **33.34 mo** | 18.0% |
>
> A 3.7× degradation, not a 1–2 month gain. The estimate implicitly assumed a
> model *trained* under the new pipeline. The incumbent learned its features
> under global min/max on unsegmented, unrotated images, so CLAHE + segmentation
> + rotation is a large distribution shift at inference time. **Preprocessing
> gains are real but arrive with retraining, or with a model that declares the
> pipeline — they cannot be bolted onto an already-trained model.** The pipeline
> is built, versioned and tested; the active version stays v1 and a test fails if
> that changes.

**The MAE number is the wrong one to optimise alone.** Your current limits of agreement are
−23.8 to +22.1 months: for an individual child this model can be two years wrong. Track
**LoA and per-subgroup MAE**, not just the mean. A model with MAE 5 months and LoA ±12 is
far more clinically usable than one with MAE 4.5 and LoA ±20.

**Compute reality:** you have no GPU. Everything above is inference-only or transfer
learning that fits comfortably in a free Colab/Kaggle session, which is how your current
model was trained.

---

## 4. What "every detail about the patient" actually means

You want the doctor to open a patient and know everything. Concretely, one screen:

**Identity & context** — age, sex, DOB, parental heights, mid-parental target, gestational
age, birth weight, known conditions, current medications.

**Growth** — height/weight/BMI/HC trajectory with all historical points; current SDS for
each; **velocity** and velocity SDS; conditional SDS since last visit; **proportions**
(US:LS, arm span) and whether disproportionate.

**Maturity** — bone age, method used, uncertainty interval, bone-age minus chronological
age, bone-age velocity vs the prior film, Tanner stages, % of adult height attained.

**Prediction** — predicted adult height with a stated interval, mid-parental target range,
and whether prediction and target agree.

**Interpretation** — fired red flags with reasons and sources; trajectory in words;
suggested work-up; suggested referral with specialty and urgency.

**Provenance** — every number tagged with its reference, version, and verified/provisional
status.

That last row is what turns a calculator into a clinical instrument. **You already have the
data model for provenance (`table_version`, `calculation_version`, `checksum_verified`) —
it just isn't surfaced.**

---

## 5. Sequencing and honest timelines

Solo developer, part-time, no budget:

| Phase | Duration | Cumulative | Gate to pass before moving on |
|---|---|---|---|
| 0 · Data foundation | 1 wk | 1 wk | Three visits persist and plot |
| 1 · Chart accuracy | 2 wk | 3 wk | Exact reproduction test green |
| 2A · Bone age honesty | 2 days | 3.5 wk | No surface says plain "TW3" |
| 2B · Image accuracy | 2 wk | 5.5 wk | MAE < 6 mo on the locked test — your own gate |
| 3 · Clinical intelligence | 2 wk | 7.5 wk | Red flags reviewed by a real endocrinologist |
| 5 · Doctor time | 1 wk | 8.5 wk | Consultation under 3 minutes, timed |
| 4 · Referral output | 1 wk | 9.5 wk | Clinician-reviewed wording |
| 2C · Licensed TW3 | parallel | — | `validate_curve()` passes on local films |
| 6 · Multi-specialty | 2 wk | 11.5 wk | Only after 1 and 2 are done |
| Continuous · Safety | throughout | — | Before any real patient data |

**Roughly three months to a genuinely strong product.** Two external dependencies sit on the
critical path and should be started today because they have lead times you don't control:
the **IAP LMS request** (1.1) and the **TW3 book** (2.11).

---

## 6. If you do only five things

1. **Build the `Observation` table** (Phase 0). Nothing else you want is possible without it.
2. **Email for the IAP 2015 LMS values** (1.1). One email, fixes most of the chart accuracy.
3. **Relabel the bone age and clamp-guard the curve** (2.1, 2.2). Two days. Stops the product
   overstating itself.
4. **Add the Indian height-velocity chart** (1.4). Biggest single clinical gain available.
5. **Swap in digiBONE** (2.4). 8.99 mo → ~4.8 mo, with Indian provenance you can defend.

---

## 7. Closing judgement

Two things I want to say plainly, because you asked me to think beyond the medical expert.

**First — you are closer than you think, but the bottleneck is not where you were looking.**
You have been improving the *maths* of the growth charts (quintic Hermite bridges, curvature
matching, monotonicity proofs) — genuinely sophisticated work. But the maths was never the
limit; the source table was. And you have been building bone-age *infrastructure* (release
gates, conformal intervals, adjudication) — which is excellent and rare — around a curve read
off a JPEG. **In both cases the engineering is ahead of the inputs.** The next phase of this
project is mostly acquisition and persistence, not more clever code.

**Second — the feature you want most is the one to build most carefully.** Telling a parent
whether their child's problem is serious or minor is the highest-value thing this product
could do, and the most dangerous. Anthropometry can tell you something *needs looking at*.
It can almost never tell you something is *fine*. Build it to escalate, never to reassure.
A product that occasionally over-refers is a good product. One that once told a family "this
looks minor" about a child with a brain tumour causing growth failure would be the end of it.

Get the trajectory stored, get the references exact, get the bone age honest, and *then*
make it smart. In that order.

---

### Sources

- [Child with Suspected Short Stature — Pediatric Endocrine Society](https://pedsendo.org/clinical-resource/child-with-suspected-short-stature/)
- [Optimizing paediatric specialist referrals for short stature (Paediatr Child Health 2024)](https://academic.oup.com/pch/article/29/5/306/7688794)
- [Growth Failure referral criteria — Children's Mercy](https://www.childrensmercy.org/health-care-providers/pediatrician-guides/endocrinology/growth-failure/)
- [Bone age: assessment methods and clinical applications](https://pmc.ncbi.nlm.nih.gov/articles/PMC4628949/)
- [Enhancing Pediatric Bone Age Assessment Using AI: Implications for Orthopedic Surgery](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11847569/)
- [Bone Age — StatPearls](https://www.ncbi.nlm.nih.gov/books/NBK537051/)
- [digiBONE (MIT) — Indian-trained segmental bone age](https://github.com/goellab/digiBONE)
- [BoNet — per-bone ROI localisation](https://github.com/BCV-Uniandes/Bonet)
- [Height Velocity Percentiles in Indian Children 5–17y (Indian Pediatr 2019)](https://pubmed.ncbi.nlm.nih.gov/30806356/)
- [Sitting Height Percentiles in 3–17-year-old Indian Children: A Multicentre Study](https://www.researchgate.net/publication/334136242_Sitting_Height_Percentiles_in_3_to_17-year-old_Indian_Children_A_Multicentre_Study)
- [Upper and Lower Body Segment Ratios from Birth to 18 years, Western Maharashtra (Indian J Pediatr)](https://link.springer.com/article/10.1007/s12098-019-02883-x)
- [Evaluation and prediction of individual growth trajectories (conditional SDS)](https://www.tandfonline.com/doi/full/10.1080/03014460.2023.2190619)
- [Variation in methods of predicting adult height (Khamis–Roche context)](https://pubmed.ncbi.nlm.nih.gov/20974789/)
