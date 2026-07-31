# Intended Use and Limitations

**Product:** Pediatric Clinical Workspace
**Version:** 1.5.0 · **Statement date:** 26 July 2026
**Status:** Research and clinician-supervised decision support. **Not a diagnostic device.**

This is a shipped artefact, not marketing copy. It is the document a clinician,
an ethics committee, or a regulator should be handed when they ask what this
software claims to do. Every limitation below is one this project has measured
in its own code, not a generic disclaimer.

---

## 1. Intended use

Assist a **qualified clinician** in India with:

- plotting and scoring paediatric growth (height, weight, BMI) against WHO 2006/2007 and IAP 2015 (Khadilkar) references;
- recording a **manual, clinician-performed** TW3-C RUS skeletal maturity assessment from a hand–wrist radiograph;
- computing QRISK3-2017 ten-year cardiovascular risk in adults;
- keeping an attributable, audited record of the above.

## 2. Intended users

Qualified clinicians (paediatricians, paediatric endocrinologists) and clinical
staff working under their supervision. **Not for use by patients or parents to
self-assess**, and no output is written for a lay reader.

## 3. What this product is NOT

- **Not a diagnostic device.** It does not diagnose, and no output should be acted on without independent clinical judgement.
- **Not FDA-cleared, CE-marked, or CDSCO-registered.**
- **Not an autonomous AI.** The AI bone-age estimate is a *suggestion* requiring confirmation by a qualified reader.
- **Not a patient-facing triage tool.** It does not tell anyone whether a problem is serious or minor.
- **Not validated on Indian children.** See §4.

---

## 4. Known limitations — measured, not hypothetical

### 4.1 Bone age

| Limitation | Detail |
|---|---|
| **The method is not Tanner–Whitehouse TW3** | Per-stage points come from Table 1 of a deep-learning conference paper (AIPR 2023); the score→age curve was **digitized from Figure 8** of that same paper. Self-declared ±0.5 y. |
| **It disagrees with original TW3** | On this centre's own films, TW3-C scored 880 where the reported original-TW3 RUS was 681 — about **0.9–1.25 years** of bone age. |
| **Curve domain is limited** | Defined only for RUS 150–1000 (boys) / 270–1000 (girls). Scores outside that return **no age**, with a reason. It does not extrapolate. |
| **AI screening model is below its own gate** | Locked-test MAE **8.99 months** against a 6.0-month target; limits of agreement **−23.8 to +22.1 months**. For an individual child the estimate can be ~2 years out. |
| **No Indian validation cohort** | Trained and validated on RSNA (US) data. Published work shows method bias varies by sex and pubertal status in Indian children. |
| **TW3 defines no 20-bone score** | RUS (13) and carpal (7) are separate, non-additive systems. The 20-bone score is a *TW2* construct. Staging all 20 is for per-bone visibility only. |

### 4.2 Growth charts

| Limitation | Detail |
|---|---|
| **IAP source table is not independently verified** | Transcribed by one person; **0 of 1,134 cells** have been second-read against the publication. |
| **Ages 3.0–5.0 y are a product-derived composite** | Neither WHO nor IAP — a fitted bridge between them. Labelled as such in the API. |
| **Tail z-scores carry residual error** | Now ≤0.07 SD (was up to 0.81 SD). The remainder is the LMS *fit's* own error and requires the published L,M,S values to remove. |
| **No growth-velocity reference** | The most sensitive indicator of growth pathology is not implemented. |
| **No head circumference, body proportions, or preterm correction** | Disproportionate short stature cannot be screened for here. |
| **Charts are cross-sectional** | A distance chart's median is not any individual child's trajectory; it cannot show a normal pubertal spurt. |

### 4.3 Cardiovascular risk

QRISK3-2017 reproduces its published test vectors exactly, but is **UK-derived**.
Its Indian ethnicity term may still under-estimate true Indian risk. Townsend
deprivation is fixed at 0 (a UK-only index).

---

## 5. Security and privacy posture

- Authentication is **required by default**; roles are `admin`, `doctor`, `assistant`. An **admin cannot approve clinical results** — that is deliberate.
- Patient **names are encrypted at rest** (AES-256-GCM) when `PCW_ENCRYPTION_KEY` is set. `patient_code` is stored in clear as a lookup key.
- `GET /api/health` reports `auth_enabled`, `encryption_at_rest` and `safe_for_patient_data`. **If `safe_for_patient_data` is false, the instance must not hold real patient data.**
- Uploaded DICOM working copies retain only an allowlisted set of technical tags; all identifying tags and all private blocks are dropped, and this is enforced by test.
- **Burned-in identifiers in pixel data cannot be detected automatically** and require a human check.
- The original upload is retained byte-for-byte as the medico-legal record and is never served to a browser.
- No data leaves the machine. There are no external network calls.

## 6. Conditions of safe use

1. A qualified clinician reviews and approves **every** patient-facing result.
2. Bone age is treated as **provisional research output** until licensed TW3 tables are entered and validated against local films.
3. The deployment reports `safe_for_patient_data: true` before any real patient data is entered.
4. Growth results near a clinical threshold are confirmed against the published chart.
5. The instance is not exposed to a public network.

## 7. Known-unsafe configurations

| Configuration | Consequence |
|---|---|
| `PCW_AUTH_DISABLED=1` | Every endpoint is open. Development only. |
| `PCW_ENCRYPTION_KEY` unset | Patient names are stored in clear in `tw3.db`. |
| Deploying to a public host (e.g. Render) | Not supported. `render.yaml` exists from earlier development and **must not** be used with real patient data. |
| Encryption key stored beside the database | Protects a copied *database*, not a copied *directory*. Back the key up separately. |

## 8. Reporting a problem

Suspected clinical inaccuracy, security issue, or data breach: stop using the
affected feature, preserve the database and logs, and record the event via the
security log (`GET /api/auth/security-events`). Under India's DPDP Act 2023 a
personal-data breach carries a notification obligation to the Data Protection
Board and to affected data principals.

---

*This statement is maintained alongside the code. When a limitation is fixed,
it is removed here in the same commit — a stale limitations list is worse than
none, because it is read as current.*
