# Plan 1 — Licensed TW3 Tables → Validated Per-Bone-Stage Bone Age

**Status:** Ready to implement · **Owner:** (assign) · **Created:** 2026-07-13
**Branch target:** `fix/clinical-accuracy-remediation` (or a dedicated `feat/licensed-tw3-tables`)
**Prerequisite asset (confirmed on hand):** a legally **licensed TW3 reference** (point tables + score→age curves).
**Product positioning (locked):** clinician-assist / decision support — a human confirms every result; the AI/engine output is a suggestion, never an autonomous diagnosis.
**Per-bone output (locked):** each of the 20 bones gets a **maturity stage + confidence + clinician confirmation**; ages come from the method's **group** RUS score and carpal score — *never* one age per bone.

> **How to use this document.** This is a self-contained implementation source. It states *what* to build, *how*, and *why*, plus the exact files, tests, and acceptance criteria. It does not depend on any other plan or on remembering this conversation. Read §3 (current state) before touching code — most of the engine already exists; this plan is mostly *activation, tamper-locking, and the lawful data-entry lifecycle*, not new math.

---

## 1. Purpose (why this plan, why now)

This is the **single highest-value accuracy lever that is currently unblocked.** Every other accuracy improvement (auto per-bone staging, screening-model retrain, external Indian validation) is blocked on data you do not yet have (per-bone annotators, a validation cohort, a GPU). The licensed TW3 tables are the one required asset you *do* have.

Today the original-TW3 letters pathway is deliberately **disabled**: it captures the doctor's 20-bone staging as annotation but shows `—` for every score and age, because the copyrighted Tanner–Whitehouse point tables and score→age curves are not — and must not be — bundled with the software. The moment those values are entered *lawfully and verifiably*, the product goes from "records what the doctor staged" to "computes a defensible RUS bone age and a separate carpal bone age from confirmed stages." That is the accuracy jump.

The risk this plan manages is not math — the engine is correct and tested. The risk is **provenance and transcription**: entering copyrighted values from an unlicensed source, or entering them with a typo that silently biases every future result. So the plan is built around *gates that refuse to score until the data is proven lawful and correct*, and a *tamper-lock so a verified table cannot be edited without detection.*

---

## 2. Scope

### In scope
- Lawful ingestion of licensed **RUS** (13-bone) point tables + **RUS score→age** curve(s) → activate a real, clinician-confirmed **RUS bone age**.
- Lawful ingestion of licensed **carpal** (7-bone) point tables + **carpal score→age** curve(s) → activate a **separate** carpal bone age (never averaged with RUS).
- A **tamper-lock (checksum)** on the licensed letters table, at parity with the existing RUS-C table.
- A **dual-transcription + reconciliation** workflow so no single typo reaches production.
- **Dynamic activation**: `/config`, the staging UI, and `/report` switch from annotation-only to real scores/ages the instant all gates pass — and revert automatically if any gate fails.
- **Report-schema alignment** and **export stamping** (method, edition, version, checksum, uncertainty) on every result.
- A written **operational SOP** the clinic's licensed clinician follows to enter and verify the tables.

### Out of scope (cross-referenced, not built here)
- **TWII′20** (the TW2 20-bone single-score method): the engine supports it (`tw20_*`), but it is optional and uses its own table; enable only if the clinic's licence covers it. Treated as an optional extension of WI-4/WI-5.
- **% predicted adult height** table: belongs to the *Adult-Height plan*, not this one — it converts bone age → % adult height attained. Cross-referenced only.
- **Auto per-bone stage prediction (AI)**: that is **Plan 4**. This plan wires the *manual_stage → score → age* path and leaves the AI `predicted_stage`/`confidence` fields present-but-null for Plan 4 to fill.
- External Indian clinical validation of the *resulting ages*: **Plan 5**.

---

## 3. Current state — precise gap analysis

**Read this before implementing.** The following already exists, is tested, and must be reused, not rebuilt:

| Capability | Where | State |
|---|---|---|
| Letters engine: 13 RUS + 7 carpal + TWII′20, independent RUS/carpal/tw20 scores & ages | `backend/tw3/letters_scoring.py` | ✅ built, never averages groups |
| Piecewise-linear score→age interpolation with endpoint clamp | `scoring.py::_interp_months` (reused by letters) | ✅ built |
| Calibration gates (points present per bone; curve ≥2 anchors) | `letters_scoring.py` `*_calibrated()` | ✅ built |
| **Provenance gate** (6 required fields) | `letters_scoring.py` `REQUIRED_PROVENANCE_FIELDS`, `provenance_complete()` | ✅ built |
| **Reference-case gate** (re-score the clinic's own films, must reproduce within tolerance) | `letters_scoring.py::validate_reference_cases` | ✅ built |
| 3-gate `scoring_ready = calibrated ∧ reference-cases-pass ∧ provenance-complete` | `letters_scoring.py::letters_status` | ✅ built |
| Validated save endpoint (never writes malformed file) | `letters_scoring.py::save_letter_tables` | ✅ built |
| Structured 20-bone report composer (per-bone stage/visibility/points/%max; separate RUS & carpal summaries; mandatory disclaimer) | `backend/tw3/report.py` | ✅ built |
| API: `/letters-score`, `/report`, provenance editor tab | `backend/api_bone_age.py`, `frontend/index.html` | ✅ built |
| Empty, well-documented table template + provenance block | `backend/tw3/letters_tables.json` | ✅ built |
| Starter-pack contracts | `bone_age_product_starter_pack/{licensed_reference_loader,report_output_schema}.json` | ✅ reference |

**The real gaps this plan closes:**

1. **No tamper-lock on the licensed table.** `tw3_tables.json` (RUS-C) is checksum-verified in `tables.py` (a mismatch *disables* scoring). `letters_tables.json` has **no checksum** — once a licensed clinician enters and verifies the values, nothing detects a later accidental or unauthorized edit. This is the most important gap: a licensed clinical table must be immutable-by-detection. → **WI-1**
2. **No dual-transcription safeguard.** Provenance and reference-cases catch *some* errors, but a systematic two-person independent transcription + cell-level diff is the standard control for copyrighted numeric tables and is absent. → **WI-2**
3. **Activation is hardcoded off.** `/config` returns `scoring_enabled: False` and `letter_stages_unverified: True` for the letters stream as constants (`api_bone_age.py:141`, `:143`). They must be driven by `letters_status()` so the UI lights up only when the gates pass, and per-bone allowed letters must be derived from which letters actually have point values (as `tables.py::_derive_allowed_stages` already does for RUS). → **WI-4**
4. **Report ↔ schema divergence.** `report.py` `per_bone_results` fields (`stage`, `points`, `pct_of_bone_max`) don't match `report_output_schema.json` (`predicted_stage`, `manual_stage`, `confidence_0_to_1`, `accepted_by_clinician`). Reconcile so Plan 4's AI fields have a home and clinician-acceptance is captured per bone. → **WI-5**
5. **No green-path activation test.** Every existing test runs against the *empty* table (scoring off). There is no test proving the whole chain *lights up* once values exist. → **WI-7**
6. **No export stamping / curve-edition policy / SOP doc.** → **WI-6, WI-8, WI-9**

---

## 4. Target architecture (end-to-end)

```
                          LICENSED SOURCE (clinic's own TW3 book)
                                        │  (paper, legally owned)
              ┌─────────────────────────┴─────────────────────────┐
      transcriber A                                        transcriber B      ← WI-2 dual entry
   letters_tables.A.json                                letters_tables.B.json
              └───────────────┬───────────────────────────┘
                              ▼  cell-by-cell diff (verify_transcription.py)
                    clean? ──no──▶ reconcile against book, re-enter
                              │yes
                              ▼
                    letters_tables.json  ── save_letter_tables() validates structure
                              │
                              ▼  compute + store SHA-256          ← WI-1 tamper-lock
                    checksum written; provenance block filled     ← existing provenance gate
                              │
                              ▼
            ┌──────────────── GATES (letters_status) ───────────────┐
            │ G1 calibrated:  every bone has points, curve ≥2 anchors│
            │ G2 reference:   clinic's own films reproduce ≤ tol     │
            │ G3 provenance:  6 required fields present              │
            │ G4 checksum:    stored == recomputed   (NEW, WI-1)     │
            └───────────────────────────┬───────────────────────────┘
                        scoring_ready = G1 ∧ G2 ∧ G3 ∧ G4
                              │
             ┌────────────────┴─────────────────┐
             ▼ false                              ▼ true
   /config: annotation-only,           /config: scoring_enabled=true,
   scores/ages show "—"                 per-bone allowed letters derived     ← WI-4
             │                                    │
             ▼                                    ▼
   doctor stages 20 bones  ───────────▶  letters_scoring.compute_letters()
   (each: stage + confidence +                    │  (pure, deterministic)
    clinician confirm)                            ▼
                                    ┌── RUS score → RUS bone age (TWIII curve) ──┐
                                    ├── carpal score → carpal bone age (separate)─┤   never averaged
                                    └── [optional] TWII′20 score → one age ───────┘
                                                   │
                                                   ▼
                        report.py::build_report → structured 20-bone report   ← WI-5 schema-aligned
                        (per-bone stage/points/%max/confidence/accepted;
                         RUS & carpal summaries SEPARATE; maturation vs
                         chronological age; mandatory clinician sign-off)
                                                   │
                                                   ▼
                        Export (PDF/print) stamped: method, edition, table
                        version, checksum, curve edition, uncertainty       ← WI-8
```

**Invariants the architecture must preserve (do not weaken):**
- Nothing is ever guessed. Missing/absent values ⇒ withhold the age, never interpolate a substitute.
- RUS age and carpal age are **always separate outputs**. No code path averages them.
- Chronological age never influences staging or scoring — it is only compared *after* the bone age is computed.
- A failed gate (including a checksum mismatch) **disables scoring** and reverts the UI to annotation-only; it never downgrades to a caveat on a live number.

---

## 5. The lawful data-entry lifecycle (the human SOP this plan enables)

This is a clinical-software control, not a nice-to-have. It ships as `backend/tw3/LICENSED_TABLES_SOP.md` (WI-9) and is enforced by WI-1/WI-2 tooling.

1. **Confirm the licence.** Record book title, edition/year, ISBN, licensed owner, page numbers of the exact tables. No values are typed until this is written into the `provenance` block.
2. **Two independent transcriptions.** Transcriber A and Transcriber B each enter the full point tables + curves into *separate* files, from the licensed book, without seeing each other's work.
3. **Cell-level reconciliation.** Run `verify_transcription.py A.json B.json`. Every mismatch is printed with bone/sex/stage and both values; each is resolved against the book. Iterate until the diff is empty.
4. **Enter reference cases.** Add 2–3 of the clinic's own historically-reported films (stages + the age that was clinically reported). These are the ground truth the software must reproduce.
5. **Verify + sign.** `entered_by`, `verified_by`, `verification_date` are filled. The reconciled file is saved via `save_letter_tables` (structural validation) and the checksum is computed and stored (WI-1).
6. **Gate check.** `letters_status()` must return `scoring_ready: true` (all four gates). If not, it names exactly which gate failed. Only then does scoring activate.
7. **Re-verification on any change.** Any future edit invalidates the checksum → scoring auto-disables until steps 3–6 are repeated. This is the point of the lock.

---

## 6. Data model & contract alignment

**Canonical file:** `backend/tw3/letters_tables.json` (already the source of truth; loader in `letters_scoring.py`).

Add one field for WI-1:
```jsonc
{
  "method": "TW3-letters",
  "version": "letters-1.0",          // bump from letters-0-uncalibrated on first real entry
  "checksum": "sha256-hex…",         // NEW — SHA-256 over canonical content excluding this field
  "provenance": { … six required fields … },
  "rus_stage_to_score":  { "boys": {…}, "girls": {…} },
  "carpal_stage_to_score": { "boys": {…}, "girls": {…} },
  "rus_score_to_age":  { "twii": {…}, "twiii": {…} },
  "carpal_score_to_age": { "twii": {…}, "twiii": {…} },
  "reference_cases": [ … clinic's own films … ]
}
```
Checksum algorithm **must mirror** `tables.py::compute_checksum` exactly (canonical JSON, `sort_keys=True`, `separators=(",",":")`, excluding the `checksum` key) so both tables behave identically.

**Report-output alignment (WI-5).** Reconcile `report.py` `per_bone_results[]` to carry both the current rich fields and the starter-pack contract fields:
```jsonc
{
  "bone_id": "RADIUS", "bone_code": "radius", "system": "RUS",
  "anatomical_name": "Radius", "display_order": 1,
  "manual_stage": "H",            // the clinician-confirmed stage (was: "stage")
  "predicted_stage": null,        // Plan 4 (AI) fills this; null until then
  "confidence_0_to_1": null,      // Plan 4 fills; clinician confidence may seed it
  "accepted_by_clinician": false, // NEW — per-bone confirmation flag
  "visibility": "STAGED", "scored": true,
  "points": 82.0, "bone_max_points": 90.0, "pct_of_bone_max": 91.1
}
```
Keep the two group summaries (`rus`, `carpal`) and `definitive_bone_age_years` exactly as they are — they already honour the "never average" rule.

---

## 7. Work items

Each item is one reversible commit with its own test, leaving the suite green (matching the repo's existing discipline in `IMPLEMENTATION-PLAN.md`).

### WI-1 — Checksum tamper-lock for the licensed letters table  *(critical)*
- **Why:** a verified licensed clinical table must be immutable-by-detection, at parity with `tw3_tables.json`. Today it isn't.
- **How:** in `letters_scoring.py`, add `compute_checksum()`/`_canonical_bytes()` (import or mirror `tables.py`). In `load_letter_tables`/`build_from_dict`, if a `checksum` is present and mismatches → raise `LetterTablesError` (⇒ scoring disabled). Add `checksum_verified: bool` to `LetterTables` and a **G4** term to `scoring_ready` in `letters_status()`. `save_letter_tables` recomputes and writes the checksum on every save.
- **Files:** `backend/tw3/letters_scoring.py`, `backend/tw3/letters_tables.json` (add `checksum` slot).
- **Tests (`tests/bone_age/test_licensed_checksum.py`):** save writes a matching checksum; a hand-edited value → mismatch → load raises → `scoring_ready:false`; CRLF/whitespace reformat does **not** trip the lock (canonicalization); parity with `tables.compute_checksum` on shared content.
- **Acceptance:** editing any point value after verification disables scoring until re-verified.

### WI-2 — Dual-transcription reconciliation tool  *(critical)*
- **Why:** the standard control for copyrighted numeric tables; catches single-person typos the other gates can miss.
- **How:** new `backend/tw3/verify_transcription.py` (pure, CLI). Loads two table dicts, deep-compares every `[table][sex][bone][stage]` cell and every curve anchor, prints a structured mismatch report, exits non-zero if any differ. On a clean match, optionally writes the merged canonical file + checksum. Mirrors the philosophy of `consensus.py`.
- **Files:** `backend/tw3/verify_transcription.py`.
- **Tests (`tests/bone_age/test_transcription_verify.py`):** identical files → clean, exit 0, checksum written; one differing cell → reported with exact path + both values, exit non-zero; missing bone/stage in one file → reported as a gap.
- **Acceptance:** two synthetic transcriptions differing in one cell are caught and located precisely.

### WI-3 — Provenance completeness on the licensed loader path  *(confirm/harden)*
- **Why:** provenance gate exists; ensure it is enforced on *every* entry path (file load and save endpoint) and that ISBN/pages are recorded even though not gated.
- **How:** verify `provenance_complete()` is consulted by `scoring_ready` (it is) and that the save endpoint returns `missing_provenance` to the UI. Add a regression test pinning the six required fields so nobody loosens the gate silently.
- **Files:** `backend/tw3/letters_scoring.py` (guard only), test.
- **Tests:** removing any one required field flips `scoring_ready` to false with that field named.

### WI-4 — Dynamic activation in `/config` and the staging UI  *(critical)*
- **Why:** the UI currently can never leave annotation-only because activation is hardcoded.
- **How:** in `api_bone_age.py::config`, replace the constant `scoring_enabled: False` / `letter_stages_unverified: True` for the `TW3_LETTERS` stream with values from `letters_status()`. When calibrated, derive per-bone allowed letters from which letters have point values (add a `letters_scoring` helper mirroring `tables.py::_derive_allowed_stages`); otherwise offer A–I with the "unverified" flag. Expose `scoring_ready` and the per-gate breakdown so the frontend can show *which* gate is outstanding.
- **Files:** `backend/api_bone_age.py`, `backend/tw3/letters_scoring.py`, `frontend/index.html` (consume the flag; flip score/age cells from `—` to live values).
- **Tests:** `/config` with empty table → `scoring_enabled:false`, letters A–I, unverified; `/config` with the WI-7 fixture table → `scoring_enabled:true`, restricted letters, gate breakdown all-pass.
- **Acceptance:** with no licensed data the UI is annotation-only; with a passing fixture table the UI shows real ages — and reverts if the checksum is broken.

### WI-5 — Report ↔ schema alignment + per-bone acceptance  *(high)*
- **Why:** align to `report_output_schema.json`, give Plan 4's AI fields a home, and capture per-bone clinician confirmation (the "confidence + confirm" half of the locked per-bone output).
- **How:** in `report.py`, rename `stage`→`manual_stage`, add `predicted_stage:null`, `confidence_0_to_1:null`, `accepted_by_clinician:false` per bone; keep points/%max. Preserve group summaries and `definitive_bone_age_years`. Add `prediction_interval` placeholder consistent with the whole-image conformal interval field naming.
- **Files:** `backend/tw3/report.py`, `backend/api_bone_age.py::report` (request may accept per-bone `accepted` map), tests.
- **Tests (`tests/bone_age/test_report.py` extend):** field names match the schema; AI fields null pre-Plan-4; acceptance flag round-trips; RUS & carpal never merged.
- **Acceptance:** report validates against `report_output_schema.json` field set; no averaging.

### WI-6 — Curve edition selection + endpoint/clamp policy  *(high)*
- **Why:** the clinic's licence is a specific edition; the definitive age must come from the correct curve, and terminal-stage extrapolation must be documented, not accidental.
- **How:** make the curve driving `definitive_bone_age_years` explicit (config value `preferred_curve: "twiii"|"twii"`; `report.py` already prefers TWIII, formalize it). Document `_interp_months` clamping as the intended terminal-stage behaviour and add boundary tests (score below min anchor, above max anchor, exactly on an anchor).
- **Files:** `backend/tw3/report.py`, `backend/tw3/letters_scoring.py`, tests.
- **Acceptance:** boundary scores map to documented ages; the report states which curve edition produced the age.

### WI-7 — Green-path fixture + end-to-end activation test  *(critical — the plan's acceptance test)*
- **Why:** prove the entire chain lights up, without shipping real copyrighted values.
- **How:** create `tests/bone_age/fixtures/letters_tables.synthetic.json` — structurally complete, **clearly marked NON-CLINICAL / illustrative** monotonic values, full provenance, valid checksum, 2 reference cases whose expected ages equal what the synthetic curve produces. Point the loader at it via the existing `TW3_LETTERS_TABLES_PATH` env override. Test the whole flow: load → all four gates pass → `scoring_ready:true` → `/config` shows scoring on → stage 13 RUS → `/report` returns a real RUS age + separate carpal age + maturation vs chronological → break one cell → checksum fails → scoring reverts.
- **Files:** fixture + `tests/bone_age/test_licensed_activation.py`.
- **Acceptance:** the end-to-end green path passes; tampering reverts to disabled.

### WI-8 — Export stamping  *(medium)*
- **Why:** every printed/exported result must carry its provenance so a reader can trust and audit it (cross-cutting requirement 6.1).
- **How:** in `reports.py`/report export, stamp method, table edition + `version`, `checksum` (short), curve edition, and the uncertainty/interval on the PDF/printable output.
- **Files:** `backend/reports.py`, `backend/tw3/report.py`.
- **Acceptance:** exported report shows edition + checksum + uncertainty; a report from an unverified table cannot be exported as "final".

### WI-9 — Operational SOP document  *(medium)*
- **Why:** the lawful lifecycle in §5 must be a checklist the clinic actually follows.
- **How:** write `backend/tw3/LICENSED_TABLES_SOP.md` from §5, with the exact commands (dual entry, `verify_transcription.py`, save, gate check) and the "any edit re-triggers verification" rule.
- **Files:** `backend/tw3/LICENSED_TABLES_SOP.md`.
- **Acceptance:** a licensed clinician can enter and activate tables using only this doc.

---

## 8. Sequencing

```
WI-1 (checksum) ─┬─▶ WI-4 (activation) ─┬─▶ WI-7 (green-path E2E test)
WI-3 (provenance)┘                      │
WI-2 (dual-entry) ──────────────────────┘   (independent; land any time before go-live)
WI-5 (report schema) ─▶ WI-8 (export stamping)
WI-6 (curve policy) ─▶ (feeds WI-5/WI-7)
WI-9 (SOP) — write alongside WI-1/WI-2; finalize before the clinic enters real data
```
Recommended order: **WI-1 → WI-3 → WI-6 → WI-4 → WI-5 → WI-7 → WI-2 → WI-8 → WI-9.** WI-7 is the acceptance gate for the code; WI-2 and WI-9 are the acceptance gate for the *process* before real values are entered.

---

## 9. Test & verification plan

- **Unit:** every WI ships its own pytest (paths above). Keep the existing suite green (`tests/bone_age/*`).
- **Golden/green-path:** WI-7 synthetic fixture is the release proof for activation.
- **Negative controls (must stay red-when-broken):** checksum tamper disables scoring; missing provenance field disables scoring; a reference case that no longer reproduces disables scoring; a single dual-transcription mismatch blocks the merge.
- **Browser verification:** with the synthetic fixture loaded via `TW3_LETTERS_TABLES_PATH`, run the app and confirm the letters stream flips from `—` to live RUS + carpal ages, that they are shown separately, and that the mandatory clinician-sign-off block is present. (Never verify with real patient films on a shared host — README constraint.)

---

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Unlicensed values entered | Provenance gate (6 fields) + SOP step 1 + `warning` in the loader; scoring refuses without documented ownership. |
| Transcription typo biases every result | Dual entry + `verify_transcription.py` (WI-2) + reference-case reproduction gate. |
| Verified table silently edited later | Checksum tamper-lock (WI-1) auto-disables scoring on any change. |
| RUS and carpal accidentally combined | Architecture invariant + tests assert separate outputs; no averaging code path exists. |
| Wrong curve edition used | Explicit `preferred_curve` + export stamping (WI-6/WI-8). |
| Reference cases too few / too easy | `curve_min_cases` (default 3) + tolerance; SOP requires clinic's own historically-reported films spanning the working age range. |
| Users read the age as validated for Indian children | This plan makes the *engine* correct; it does **not** establish external accuracy — that is Plan 5. Report wording stays "clinician-supervised decision support" until Plan 5 completes. |

---

## 11. Definition of Done

- [ ] Licensed letters table carries a stored checksum; any post-verification edit disables scoring (WI-1).
- [ ] `scoring_ready` is the conjunction of **four** gates: calibrated ∧ reference-cases ∧ provenance ∧ checksum.
- [ ] Dual-transcription tool catches and locates a single-cell mismatch (WI-2).
- [ ] `/config` and the UI activate scoring **only** when all gates pass, and revert otherwise (WI-4).
- [ ] `/report` output matches `report_output_schema.json`, carries per-bone acceptance + null AI fields, and keeps RUS/carpal ages separate (WI-5).
- [ ] Curve edition is explicit and stamped; boundary behaviour tested (WI-6).
- [ ] End-to-end green-path test passes on a clearly-non-clinical synthetic fixture (WI-7).
- [ ] Exports stamp edition + checksum + uncertainty; unverified tables cannot export a "final" report (WI-8).
- [ ] `LICENSED_TABLES_SOP.md` lets a licensed clinician enter and activate tables unaided (WI-9).
- [ ] Full test suite green; app browser-verified with the fixture.

---

## 12. Open decisions to confirm before entering real data

These do not block writing the code, but the clinic must answer them before step 2 of the SOP:

1. **Which licensed edition?** Original TW3 (2001, RUS grades) vs TW2 — this fixes whether the primary curve is `twiii` (TW3) or `twii`, and which point tables are legal to enter.
2. **RUS-only or RUS + carpal?** Carpal activation needs a licensed carpal table; if the licence is RUS-only, carpals stay annotation-only (the engine already supports this split).
3. **TWII′20 in or out?** Enable only if the licence covers the TW2 20-bone method; otherwise leave `tw20_*` empty.
4. **Reference films:** which 3+ historically-reported cases (with the clinically reported age) will serve as the reproduction ground truth, and what tolerance (default ±0.3 yr)?
5. **Preferred definitive curve** when both TWII and TWIII are entered (default: TWIII).

---

*This plan is an engineering + process design. It makes the scoring engine lawful, tamper-proof, and correct; it does not by itself constitute clinical validation or regulatory clearance of the resulting ages (see Plan 5).*
