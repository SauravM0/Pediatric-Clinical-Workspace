# Clinical validation protocol

How each module is shown to give the right answer before clinic use. Automated
evidence is necessary but not sufficient: every module also needs a named
clinician's sign-off, and `python -m backend.release_check` fails until it has one.

## Principles

1. **Expected values come from the source, never from the code.** Each vignette's
   expected value is derived by hand from the published equation or table, with
   the arithmetic written in its `derivation` field.
2. **A failure is investigated, never "fixed" by editing the expectation.**
   Establish from the source whether the code or the vignette is wrong.
3. **Refusal is a correct output.** Outside a method's validated population
   (eGFR under 1 year, FIB-4 under 18, BP under 13 without the AAP tables), the
   right answer is "not computed, and why". Vignettes test refusals as well as numbers.
4. **Missing reference data is refused, not approximated.** See the reference-data
   status on the Overview tab (`/api/reference-data`).

## Evidence per module

| Module | Method | Automated evidence | Clinician check |
|---|---|---|---|
| Growth z-scores / centiles | WHO 2006/2007 LMS (Cole), IAP 2015 once installed, blend 3–5 y | WHO tables vs rcpchgrowth: 11,046 points, worst 0.006 z; sealed by SHA-256. Local LMS bit-identical on 290 cases. Growth validation `all_pass` (continuity, monotonicity, centile ordering, source reproduction). Vignettes GROWTH-01..03 vs published WHO medians. | Plot 5 known patients; compare with a paper WHO/IAP chart |
| eGFR | Bedside Schwartz (<18), CKD-EPI 2021 (≥18), CKiD U25, CG, MDRD; KDIGO G/A | `tests/renal`; vignettes RENAL-01..05 | Compare 10 lab reports with eGFR printed |
| FIB-4 | Sterling 2006; age ≥65 low cut-off 2.0 | `tests/hepatic`; vignettes LIVER-01..04 | Review the paediatric refusal wording |
| Blood pressure | AAP 2017 (≥13 static; 1–12 centile tables, gated); ACC/AHA 2017 adults | `tests/vitals`; vignettes BP-01..03 | Confirm the Indian 140/90 note is wanted |
| QRISK3 | Hippisley-Cox 2017 (backend only) | `tests/cvd`; browser/backend parity max 0.05 % on 300 patients | Check 5 patients against qrisk.org |
| FRAX | Official calculator result recorded, never computed | Guard tests: no invented formula | Enter 3 known results |
| TW3 bone age | Licensed tables, accuracy gate against reference cases | Lifecycle tests; approval-only snapshot input; UI approval tests | Blocked until the licensed tables are entered and the reference cases pass |
| AI bone age (GP) | ONNX MobileNetV3, conformal intervals | Locked test MAE 8.99 months; range warning outside training labels | Screening only; can never be entered as the TW3 bone age |
| Clinical rules / triage | `backend/clinical/rules.py`, thresholds in `thresholds.json` | `tests/clinical` | Review every threshold in `thresholds.json` against the cited guideline |

## Sign-off procedure

1. The clinician reviews each vignette in `clinical_vignettes.json`: inputs,
   expected value, derivation and source.
2. They record `"agrees": true|false`, their name, the date (YYYY-MM-DD) and
   any comment in `signoff`.
3. A `false` blocks release until resolved. Record the resolution in `comment`.
4. New vignettes are added when a module changes, or when a clinician reports a
   case where the workspace disagreed with them.
5. Re-run `python -m backend.release_check --tests`.
