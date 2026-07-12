# Master Clinical Accuracy Audit

**Product:** Pediatric Clinical Workspace  
**Clinical domains:** Pediatric endocrinology, skeletal maturity, growth assessment, and adult cardiovascular risk  
**Date:** 12 July 2026  
**Deliverable:** Consolidated report only. No implementation or fixes were performed.  
**Evidence basis:** Current repository, supplied audit report, existing internal reports, targeted tests, and authoritative/published references listed below.

## 1. Executive conclusion

The product has a strong safety-oriented architecture: it separates several bone-age methods, withholds some uncalibrated outputs, stores structured assessments, and includes substantial growth-curve regression testing. However, it is **not yet ready to claim clinically validated bone-age accuracy, automatic examination of all 20 bones, or an official continuous Khadilkar/IAP chart across all displayed ages**.

Five findings block a clinical accuracy claim:

1. The active automatic X-ray model returns a whole-hand GP-style estimate. It does not identify, stage, and report all 20 bones. Its repository metadata reports a validation MAE of 8.6 months on RSNA data, without a locked external Indian clinical validation cohort.
2. The active TW3-C pathway scores 13 RUS bones, but its score-to-age curve is explicitly provisional and digitized from a published figure. The original-TW3 13 RUS + 7 carpal workflow cannot produce validated scores or ages until licensed tables are entered and verified.
3. Individual bones do not ordinarily receive 20 independent “bone ages” in TW3. The clinically defensible detailed report is per-bone visibility, maturity stage, score, confidence, and clinician confirmation, followed by method-defined group scores/ages.
4. The growth engine constructs a custom WHO–IAP curve between ages 3 and 5. IAP endorsement of WHO standards below five does **not** validate this product-created Hermite transition. It must be identified as a derived composite and clinically validated, or the references should be shown separately.
5. The interface labels mid-parental genetic target height as “Predicted Adult Height.” These are different clinical quantities and must be displayed independently.

The appropriate present positioning is:

> **Research and clinician-supervised decision support. AI findings are suggestions requiring qualified clinical confirmation; the product is not an autonomous diagnostic device.**

## 2. Review of the supplied audit report

The supplied report is useful and substantially consistent with the codebase. Its most valuable additions are:

- identification of the mid-parental-height versus predicted-adult-height labeling error;
- emphasis that CSV-to-engine reproduction does not prove CSV-to-publication accuracy;
- clear explanation that TW3 provides per-bone stages/scores and method-defined group ages, not 20 independent ages;
- appropriate prioritization of the provisional TW3-C conversion curve and QRISK3 parity testing.

The following statements required correction or qualification in this master report:

| Supplied statement | Master assessment |
|---|---|
| AI input is 160 px | Incorrect for the current checked-in model metadata, which states 224 px. |
| WHO–IAP Hermite blending is the IAP-recommended approach | Unsupported. IAP recommends WHO standards below five; the 3–5-year quintic bridge is a product-created mathematical construction. |
| Standard IAP curves match the paper exactly | Too strong until every CSV value is independently reconciled with the published tables. The engine reproduces its CSV inputs at tested published centiles. |
| Localizer and stage classifier exist and are blocked only on data | Inference/training scaffolding exists, but checked-in availability, integration, clinical accuracy, image-quality gating, and validation are separate blockers. |
| Add a transparent fixed Indian offset | Not recommended. Published bias varies by sex, age, puberty, method, and cohort. Any calibration must be learned and validated by subgroup, not applied as a universal offset. |
| Stage-to-score table is trustworthy because maximum scores sum to 1000 | The invariant supports transcription consistency but does not prove that every cell matches the source or that a Chinese TW3-C table is clinically valid for Indian children. |
| The current model is weak | Its 8.6-month MAE is insufficient for a definitive clinical claim, but “weak” is not a complete scientific assessment without external, subgroup, and comparator results. |

## 3. Bone-age system

### 3.1 Current pathways

| Path | Structures | Current capability | Required interpretation |
|---|---:|---|---|
| Whole-image AI | Entire hand image; no reported per-bone staging | GP-style scalar estimate; metadata: 224 px, RSNA, MAE 8.6 months | Screening suggestion only |
| TW3-C RUS | 13 RUS bones | Numeric grades and sex-specific scores; provisional score-to-age anchors | Research/clinician-supervised; not original TW3 |
| Original-TW3 letters | 13 RUS + 7 carpals | Staging/annotation structure | Scores/ages disabled until lawful licensed tables pass validation gates |
| TWII'20 | All 20 structures with its own points and curve | Engine structure exists | Must not reuse or sum RUS/carpal point systems; unavailable without its correct licensed tables |

The represented structures are:

- **13 RUS:** radius, ulna; metacarpals 1, 3, 5; proximal phalanges 1, 3, 5; middle phalanges 3, 5; distal phalanges 1, 3, 5.
- **7 carpals:** capitate, hamate, triquetral, lunate, scaphoid, trapezium, trapezoid.

### 3.2 Confirmed problems

**BA-01 — Provisional TW3-C conversion is the largest deterministic accuracy risk (critical).** The sex-specific stage points may be internally consistent, but the final score-to-age anchors were digitized from a figure and are labeled approximately ±0.5 year. The final reported age cannot be more authoritative than this conversion.

**BA-02 — No validated automatic 20-bone assessment (critical).** The whole-image model produces only one scalar. The localizer targets 13 RUS bones if a model is installed. Per-bone staging code expects separate models and honestly returns no result if they are absent. Seven-carpal localization/staging and validated end-to-end 20-bone inference are not established.

**BA-03 — External Indian validation is absent (critical).** Internal RSNA validation does not establish clinical performance in Indian children or in endocrine/pathology populations. Published Indian comparisons show that method suitability and bias vary across sex and pubertal groups. A fixed population correction is therefore inappropriate.

**BA-04 — Multiple methods can create false equivalence (critical).** GP-style AI, Chinese TW3-C, original TW3 RUS, carpal TW3, and TWII'20 use different constructs and references. Never average them. Display method agreement as a cross-check and route material disagreement to re-review.

**BA-05 — Original 20-bone scoring remains calibration-gated (high).** Detailed 20-row staging can be recorded, but valid original-TW3/TWII'20 numerical results require the clinic’s licensed tables, dual transcription, checksums, and known reference cases.

**BA-06 — Patient-level uncertainty is not demonstrated (high).** Validation MAE is an average absolute error, not a patient confidence interval. Report subgroup errors and calibrated prediction intervals; define an abstention threshold.

**BA-07 — Image acceptability and out-of-distribution gating are incomplete (high).** Required checks include correct patient/study, left hand and wrist, complete field, orientation, rotation, exposure, sharpness, duplicates, and source compression. Fracture, implant, focal lesion, dysplasia, congenital anomaly, severe deformity, missing anatomy, and unfamiliar acquisition should trigger manual specialist review.

**BA-08 — “Accelerated/retarded” at ±1 year is a heuristic (medium).** Bone age minus chronological age is correct arithmetic, but a universal ±1-year diagnostic categorization ignores method error, age, sex, pubertal stage, and indication.

### 3.3 Correct detailed report for “all 20 bones”

The system should inspect and document every expected structure, but it must not invent an individual age where the chosen method defines only a stage/score.

Each of the 20 rows should contain:

1. Full anatomical name and method-specific code.
2. ROI overlay or coordinates proving which anatomy was assessed.
3. Visibility: complete, partial, absent, obscured, or not detected.
4. Image-quality warning specific to that ROI.
5. Method vocabulary and maturity stage; do not mix TW3-C numeric grades with original-TW3 letters.
6. Top stage plus the probability distribution/next-best stage when AI-assisted.
7. Method- and sex-specific points only when the correct validated table is active.
8. Expected maturity context only if supported by a validated reference; do not create an unvalidated “expected stage for age.”
9. Clinician confirmation, override, reason, identity, and timestamp.

The summary should report separately:

- completeness: RUS x/13 and carpals x/7;
- RUS maturity score and RUS bone age;
- carpal score and carpal bone age where the selected method defines and validates it;
- TWII'20 result only from its own 20-bone points and conversion;
- GP-style screening estimate as a separate cross-check;
- chronological age from exact birth and acquisition dates;
- disagreement flags, uncertainty, method/version/source, and approval status.

### 3.4 Validation requirements

- Pre-register a multi-centre Indian validation protocol with a frozen test set excluded from training and routine feedback.
- Use at least two blinded qualified readers, adjudication, and repeated reads to measure inter- and intra-reader variability.
- Report MAE, median absolute error, RMSE, signed bias with 95% confidence interval, Bland–Altman limits, percentage within 6/12 months, and clinically important worst cases.
- Stratify by sex, clinically relevant age bands, pubertal stage, normal/endocrine/pathology groups, site/device, and original DICOM versus compressed/photo acquisition.
- For localization/staging report detection completeness, landmark/ROI error, per-bone and per-stage confusion matrices, ordinal stage distance, macro/micro accuracy, weighted kappa, calibration, and abstention rate.
- Lock and identify preprocessing, model weights, scoring tables, conversion curves, software version, and report template. Every update must re-pass technical and clinical gates.

## 4. Khadilkar/IAP and WHO growth charts

### 4.1 Confirmed strengths

- Six sex/measure CSVs cover IAP height, weight, and BMI from 5–18 years at half-year rows.
- Height and weight include seven standard centiles. BMI correctly separates the published lower centiles from adult-equivalent BMI 23/27 cut-offs.
- Direct PCHIP interpolation of published columns is shape-preserving and reproduces the repository tables at their anchor ages.
- Cole LMS forward and inverse equations are standard.
- The code keeps IAP adult-equivalent BMI 23/27 curves distinct from fixed z-score percentiles.
- The test suite checks many useful software properties: table reproduction, centile ordering, age ordering, and transition behavior.

These are software-quality strengths, not proof of clinical equivalence to the publications.

### 4.2 Confirmed problems

**GC-01 — Source transcription has not been independently proven (critical).** Engine-to-CSV tests prove that the engine reproduces repository data. They do not prove that every CSV cell equals the original Khadilkar/IAP publication. Every cell needs dual-person reconciliation and permanent source/checksum documentation.

**GC-02 — The 3–5-year composite is not an official curve (critical).** Values within this window are generated by a custom quintic Hermite bridge, including backward evaluation of an IAP-side fitted model. It modifies pure WHO output before age five. Describe it as a product-derived composite, not “the Khadilkar curve” or “the WHO curve.”

**GC-03 — Some cases can produce a deliberate value step (critical).** If the IAP endpoint is not above the WHO start for a monotonic measure/centile, the bridge returns the IAP endpoint throughout the transition. This avoids a declining segment but can shift abruptly at the lower boundary. Marking this non-gating is not a clinical validation. Quantify every affected sex/measure/centile and resolve the reference-policy decision.

**GC-04 — Displayed curves and patient scoring are not always one inverse model (high).** Published displayed centiles normally use direct PCHIP columns, while arbitrary IAP z-scores use fitted LMS. A measurement lying on a displayed centile may therefore not receive exactly that centile. Full-grid forward/inverse consistency must be measured and bounded.

**GC-05 — BMI upper curves are model-derived (high).** IAP BMI P75/P90/P97 are not present in the repository source table and are produced by the fitted distribution. They must not be labeled as published Khadilkar/IAP centiles. The published adult-equivalent 23/27 curves should drive Indian overweight/obesity interpretation.

**GC-06 — The LMS fit is reconstructed, not author-supplied (high).** L and S are estimated from rounded percentile values; BMI uses limited lower-tail points and smoothing. Obtain official distribution parameters from the authors if available and verify their permitted clinical use.

**GC-07 — WHO dependency/data version is insufficiently locked (high).** An open-ended `rcpchgrowth>=4.5.0` dependency can change outputs. Pin the validated version and store reference data/package checksums in generated reports.

**GC-08 — Measurement conventions need explicit clinical treatment (high).** Calculate age from dates with the reference’s required precision. Distinguish recumbent length and standing height; validate units and plausible ranges; handle prematurity correction only where appropriate. A smoothed visual seam must not conceal a change in measurement convention.

**GC-09 — Cross-sectional curves do not measure an individual child’s velocity (medium).** Longitudinal growth velocity requires serial measurements, exact elapsed time, consistent technique, error review, and an appropriate velocity reference.

### 4.3 Required curve-validation matrix

1. Reconcile every IAP CSV value against the primary published table and record reviewer, source page/table, timestamp, and checksum.
2. Compare WHO outputs against official WHO 2006/2007 tables and official software cases, including sex, age precision, units, and boundary ages.
3. At every sex × measure × age × displayed centile, test displayed value → inverse z-score → percentile against the advertised line.
4. Quantify value and slope continuity, centile ordering, and forward/inverse consistency at the 2-year measurement seam, 3-year blend entry, 5-year IAP handoff, exact-table guard, 10-year weight-for-age boundary, and 18-year IAP boundary.
5. List every product-derived curve separately from published curves in the legend and exported report.
6. Have pediatric endocrinologists compare screen and PDF renderings with official boys’ and girls’ references, including axes, units, grid geometry, labels, and BMI cut-offs.
7. Validate longitudinal plotting and velocity calculations with hand-calculated cases and clinically meaningful measurement intervals.

## 5. Formula audit

### 5.1 Confirmed formula inventory

| Formula/output | Assessment | Required disposition |
|---|---|---|
| BMI = kg / m² | Algebraically correct | Validate units, dates, zero/implausible inputs, and rounding |
| Cole LMS z-score/value | Standard equations | Validate parameter source/domain, tails, and forward/inverse consistency |
| z-score to percentile | Standard normal-CDF approximation | Golden-test against a trusted library over the supported range and disclose clipping |
| Bone age − chronological age | Correct subtraction | Use exact dates and uncertainty; avoid universal diagnostic labels |
| TW score interpolation | Linear interpolation is deterministic | Accuracy depends entirely on correct licensed points/conversion anchors and endpoint policy |
| Mid-parental target height | Sex-specific equations are conventional | Treat as genetic target with an explicitly sourced target range, not a child-specific prediction |
| Skeletal predicted adult height | Current-height / fraction-attained form is mathematically coherent | Keep disabled until correct method/sex tables and prediction uncertainty are licensed and validated |
| Height/weight age from P50 crossing | Descriptive inverse lookup | Label descriptive only; address non-unique/out-of-range values |
| Growth velocity | Requires longitudinal data | Use exact day interval, consistent measurement method, minimum interval, and a suitable reference |
| QRISK3-2017 | Structure resembles source implementation | Requires authoritative parity tests, eligibility enforcement, and missing-input review before clinical use |

### 5.2 Confirmed adult-height labeling defect

The current logic chooses mid-parental height first and assigns it to a variable displayed under **“Predicted Adult Height.”** The status badge later calls it a genetic target, but the headline remains conceptually wrong.

These must be separate:

- **Mid-parental target height:** parental genetic target and target channel.
- **Skeletal predicted adult height:** child-specific estimate derived from current height and a validated skeletal-maturity prediction method.
- **Difference between predicted and target:** the clinically useful comparison, with uncertainty from both quantities.

Do not introduce Bayley–Pinneau or any alternative simply to fill the empty output. Select a method based on licensing, target population, indication, and external validation. Every prediction needs an interval and known limitations, not only a point estimate.

The existing auxiliary adult-height centile also uses `(P75 − P25)/2` as an SD approximation. For a normal distribution, the interquartile relationship does not make that expression one SD. It should not be used to produce a precise z-score/percentile unless validated or replaced with the actual reference distribution.

### 5.3 QRISK3 safety review

QRISK3 is an adult UK cardiovascular-risk model, not a pediatric growth formula or an India-specific national model. The frontend allows defaults/centering for absent variables, which can create a precise risk number from incomplete information.

Before any clinical use:

1. Compare a broad golden-case set against the exact authorized ClinRisk implementation, including both sexes, ethnicity, smoking, interactions, boundary ages, and every binary condition.
2. Confirm coefficients, fractional-polynomial transforms, centering, survivor value, clamping, and missing-data behavior against the same source/version.
3. Enforce intended eligibility and make ineligible cases unavailable, not merely caveated.
4. Display every imputed/defaulted field and prohibit an apparently complete risk when required clinical data are missing.
5. Separate the adult cardiovascular module visibly from pediatric bone-age/growth workflows and state its population limitations.

### 5.4 Formula governance required for the whole product

Every clinical output should have:

- exact source, edition/year, population, and licensing status;
- supported age/sex/clinical domain and contraindications;
- required inputs, units, date precision, and missing-input policy;
- formula/reference-data version and checksum;
- documented interpolation, extrapolation, clamping, and rounding;
- independent golden cases and boundary tests;
- uncertainty/prediction interval and subgroup validation;
- visible provenance and “not validated for” conditions in the report.

## 6. Prioritized program

### P0 — must complete before clinical accuracy claims

1. Do not claim the automatic model checks all 20 bones.
2. Prevent the provisional TW3-C conversion from appearing definitive; replace or validate it with an authoritative source and independent known cases.
3. Obtain lawful original-TW3/TWII'20 tables, double-transcribe them, checksum them, and validate complete reference cases before enabling scores.
4. Establish an expert-consensus, multi-centre Indian external bone-age validation set and predefined acceptance criteria.
5. Reconcile all six IAP CSVs with primary publications and official source files.
6. Label or redesign the custom WHO–IAP transition; quantify and eliminate/unambiguously disclose discontinuities and scoring/display mismatch.
7. Separate mid-parental target height from skeletal predicted adult height.
8. Golden-test QRISK3 and all high-impact formulas against their authoritative implementations; restrict eligibility.

### P1 — required for trustworthy clinical workflow

1. Produce the auditable 20-row anatomy/stage report with visibility, overlay, uncertainty, abstention, and clinician confirmation.
2. Add acquisition-quality, pathology, and out-of-distribution gates.
3. Add method/version/source/checksum and uncertainty to every result and export.
4. Pin all validated clinical-data dependencies.
5. Implement valid longitudinal velocity assessment and distinguish it from cross-sectional curve slope.
6. Create clinician review dashboards for method disagreement, overrides, subgroup error, and drift.

### P2 — accuracy improvement after governance is in place

1. Train and validate 13-bone RUS localization and ordinal staging on diverse, multi-reader Indian data, then extend deliberately to seven carpals.
2. Calibrate patient-level uncertainty and abstention by subgroup and image domain.
3. Evaluate segmental ensembles prospectively against whole-image and expert baselines.
4. Pursue official IAP distribution parameters if available; otherwise clearly constrain claims to published tabular centiles and validated reconstructed outputs.

## 7. Clinical-release acceptance criteria

A release should not be described as clinically accurate until all applicable conditions are met:

- no provisional conversion source drives a definitive result;
- every active reference table has lawful provenance, checksum, and independent transcription/reference-case verification;
- external Indian performance meets pre-specified overall and subgroup thresholds;
- per-bone staging and localization meet pre-specified accuracy, agreement, calibration, and completeness thresholds;
- out-of-distribution and poor-quality cases abstain safely;
- growth curves reproduce verified source data and pass forward/inverse and boundary consistency tests;
- derived composite curves are identified and clinically reviewed;
- adult-height target and prediction are separate and uncertainty-aware;
- QRISK3/formula golden cases match authoritative implementations;
- every report identifies patient/study, method, source, model, tables, versions, uncertainty, overrides, and approving clinician.

## 8. Audit evidence and limitations

- The supplied report and the current repository were reviewed directly.
- Current model metadata reports `input_size: 224`, `n_images: 12611`, `n_val: 1891`, and `val_mae_months: 8.6`.
- The ordinary Python environment could not collect the full test suite because FastAPI was missing.
- The repository virtual environment displayed 34 passing growth/frontend tests before the audit command reached its 60-second timeout; no failure was shown before timeout.
- Passing software tests do not constitute clinical validation, regulatory clearance, or proof of generalization.
- Copyrighted TW3 tables were not available for independent numerical verification.
- This report is a clinical/technical risk assessment, not a substitute for formal medical-device quality management, biostatistical review, cybersecurity/privacy assessment, or regulatory advice.

## 9. Key references

1. Indian Academy of Pediatrics Growth Charts Committee. Revised IAP growth charts for 5–18 years (2015): https://www.indianpediatrics.net/jan2015/47.pdf
2. WHO Child Growth Standards: https://www.who.int/tools/child-growth-standards/standards
3. WHO AnthroPlus 5–19 years manual: https://www.who.int/docs/default-source/child-growth/growth-reference-5-19-years/who-anthroplus-manual.pdf
4. Shah et al. Comparison of GP, Gilsanz–Ratib, and TW3 in healthy Indian children: https://pmc.ncbi.nlm.nih.gov/articles/PMC8547392/
5. Patil et al. Applicability of GP standards to Indian children: https://pubmed.ncbi.nlm.nih.gov/22014975/
6. Chakladar et al. digiBONE segmental assessment in Indian children: https://pubmed.ncbi.nlm.nih.gov/41890183/

## Final recommendation

The supplied report materially improves the earlier audit, but it should not be adopted unchanged. This master version retains its valid findings, corrects unsupported claims, and adds explicit validation and release gates.

The product will earn clinician trust by demonstrating exactly what anatomy was assessed, using lawful and verified references, showing uncertainty and abstention, separating incompatible clinical quantities, and proving performance on representative Indian children. More displayed numbers alone will not increase accuracy or trust.

**Final status: suitable for controlled research and clinician-supervised development; not yet suitable for an autonomous or definitive clinical accuracy claim.**
