# Bone-age product validation protocol

## 1. Intended first release

Start with a **research/clinician-assist whole-hand bone-age estimate**, not an autonomous
TW3 diagnosis. Keep the official TW3 scoring module disabled until the licensed point
tables, score-to-age curves, and official stage criteria have been installed and independently verified.

## 2. Reference standard

For every validation image:

1. Use a left posteroanterior hand/wrist radiograph.
2. Have two trained readers assess the image independently.
3. Adjudicate disagreements with a third experienced pediatric radiologist or pediatric endocrinologist.
4. Store the final reference age in months and the method used.
5. For per-bone staging, readers must use a legally licensed TW manual.

Chronological age is not the ground truth for bone age. It is a comparison variable.

## 3. Data splitting

- Split by patient, never by image.
- Keep training, tuning, internal test, and external test patients separate.
- Keep all serial radiographs from one patient in one split.
- Preserve sex and age distributions.
- Maintain a fully external test set from a different hospital/scanner.
- Report results separately by sex, age band, site, scanner, and major diagnosis group.

Suggested age bands:
- 0–5 years
- >5–8 years
- >8–12 years
- >12–15 years
- >15–18 years

## 4. Required image quality gate

Automatically reject or require manual review for:

- wrong laterality;
- non-PA positioning or marked rotation;
- motion or severe exposure error;
- clipped digits or distal radius/ulna;
- fracture, cast, fixation hardware, severe deformity, or suspected skeletal dysplasia;
- missing sex reference;
- age outside the validated range;
- model confidence below the validated threshold;
- excessive disagreement among individual bones.

Do not silently generate a normal report after a quality failure.

## 5. Metrics

Whole-hand age:
- mean absolute error in months;
- median absolute error;
- signed bias;
- root mean square error;
- Bland–Altman limits of agreement;
- percentage within ±3, ±6, ±9, and ±12 months;
- calibration of uncertainty;
- failure/abstention rate.

Per-bone staging:
- exact-stage accuracy;
- within-one-stage accuracy;
- weighted kappa;
- confusion matrix for every bone;
- inter-reader and model-reader agreement;
- confidence calibration.

Clinical workflow:
- change in reporting time;
- percentage of AI outputs changed by the clinician;
- serious error rate;
- subgroup failure analysis.

## 6. Provisional engineering gates

These are product-development targets, not regulatory acceptance criteria:

- whole-hand mean absolute error no worse than 6 months on the locked internal test set;
- no prespecified sex/age/site subgroup with mean absolute error above 9 months;
- at least 90% of accepted cases within ±12 months;
- weighted kappa at least 0.80 for overall per-bone staging;
- no individual bone subgroup below 0.70 without mandatory manual review;
- zero report release when the image-quality gate fails;
- 100% clinician review during pilot deployment.

The RSNA challenge's best test performance was 4.2 months mean absolute difference,
so a six-month internal target is achievable but must be reproduced locally.

## 7. Local clinical validation

Before patient-facing use, validate on an Indian clinical cohort that includes:

- normal variants;
- growth hormone deficiency;
- constitutional delay;
- precocious puberty;
- hypothyroidism;
- Turner syndrome;
- chronic disease;
- treated and untreated follow-up images.

A practical pilot can begin with at least 200 independently read radiographs, but a larger
external test cohort is preferable, especially for subgroup analysis. Do not claim accuracy
for diagnoses or age ranges with inadequate sample sizes.

## 8. Reporting rule

The system may propose an estimate, confidence, quality status, and per-bone findings.
Only the clinician-reviewed value should be printed as the final bone age.

Do not state “TW3 bone age” unless:
- the official licensed stage criteria were used;
- the official sex-specific point values were used;
- the official score-to-age conversion was used;
- the calculation engine passed unit tests against manually verified examples.
