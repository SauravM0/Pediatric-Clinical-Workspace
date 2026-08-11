# Growth Charts & TW3 Bone Age — Root-Cause Diagnosis and Roadmap

**Date:** 26 July 2026
**Scope:** The two accuracy problems you raised (growth-curve fidelity; TW3 bone age), plus what to add next
**Method:** Direct code reading, numeric probes run against your own engine, and external literature search
**Status:** Diagnosis only — no code was changed

> **Superseded in part — see `DELIVERY-STATUS-2026-08-10.md`.**
> This document is left as written on 26 July. Most of its roadmap is now built;
> six of its findings have since been measured and four of those were wrong.
> The two that change the clinical picture:
>
> - **Four of seven columns in the IAP height/weight CSVs are not published
>   values.** They were filled in by even z-spacing during transcription, so the
>   drawn 25th centile is the 26.5th. This document identifies the missing L,M,S
>   as *the* growth-chart problem; it is not the only one.
> - **"8.99 mo → ~4.8 mo" (§ digiBONE) is not a valid comparison.** Those are
>   two different models measured on two different test sets.

---

## 0. Executive summary

You have two problems that feel similar ("the numbers aren't accurate enough") but have
**completely different root causes and completely different difficulty**.

| | Growth charts | TW3 bone age |
|---|---|---|
| Root cause | The reference **data** is a hand-transcribed, unverified, rounded percentile table — and the LMS values that would fix it were never obtained | The method **isn't TW3**. It is a Chinese TW3-C table lifted from a deep-learning conference paper, with a score→age curve *digitized off a figure* in that same paper |
| Is 99%+ achievable? | **Yes.** This is pure engineering — exact reproduction of a published reference | **No, not as stated** — but the right target is achievable and I define it in §3 |
| Effort to fix properly | Days, mostly clerical | Months, and needs a licensed book plus local films |
| Biggest single action | Obtain the IAP 2015 L,M,S triplets from the authors | Stop calling it TW3; adopt an Indian-validated open model for the AI path |

**The most important finding in this whole review:** the IAP 2015 L,M,S values that your
code says were "never published" **do exist and were used by the IAP authors themselves**
in a 2021 paper. Getting them collapses most of the growth-chart problem to nothing. See §2.1.

**The second most important finding:** there is an **MIT-licensed, Indian-trained,
open-source bone age model** (digiBONE) built on 2,430 Indian children at Khadilkar's own
institute in Pune, reporting 4.7–4.9 months error *on its own Indian validation set*. Your
current model measures **8.99 months** *on a frozen RSNA split*. Those two numbers are not
comparable — see the correction at §4.4. See §4.4.

**One premise needs correcting up front:** you asked about "TW3, newest method, 20 bones."
TW3 (Tanner et al., 2001) does **not** have a 20-bone score. The 20-bone score was a *TW2*
construct and was **dropped** in TW3. TW3 publishes RUS (13 bones) and Carpal (7 bones) as
**two separate, non-additive** scoring systems, and RUS is the recommended one. There is no
legitimate "TW3 20-bone bone age" to compute. What you *can* legitimately do for all 20
bones is report per-bone stage, score and confidence — which is what your architecture
already anticipates. Never sum RUS and carpal points into one number.

---

## 1. What this product is (my read)

A locally-hosted FastAPI + single-page React workspace for Indian paediatric practice,
with four service lines:

1. **Growth assessment** — height/weight/BMI-for-age charts, z-scores, percentiles, IAP/IOTF
   obesity cut-offs, PDF report. WHO 2006/2007 below age 5, IAP 2015 (Khadilkar) from 5–18.
2. **Bone age / skeletal maturity** — X-ray upload, an ONNX screening model, a 13-bone
   TW3-C RUS manual staging workflow, a 20-bone letter-annotation stream, adjudication
   queue, drift monitoring, gated model releases.
3. **Adult height prediction** — currently mid-parental (Tanner) target height only.
4. **Adult CVD risk** — QRISK3-2017, reproducing the published test vectors.

**The engineering quality here is genuinely high, and unusually honest.** Uncalibrated
outputs are withheld rather than faked. Data files are checksum-locked. There is a locked
held-out test set with a leak guard. There is split-conformal uncertainty rather than a
fake ±MAE band. The `MASTER-CLINICAL-ACCURACY-AUDIT-2026-07-12.md` already identifies
several of the issues below and does not flinch from them. That culture is the reason
this product *can* get to where you want it — most projects at this stage are hiding
these problems, not documenting them.

What follows is therefore not "your code is bad." It is: **the code is ahead of the data,
and the data is the bottleneck.**

---

## 2. Problem 1 — Growth charts

### 2.1 Root cause: the reference data, not the maths

Your curve machinery is good. `hermite.py`, `blend.py` and `curve_builder.py` are careful,
well-reasoned, and use validated SciPy primitives (PCHIP, Brent root-finding) rather than
hand-rolled numerics. The monotonicity guarantees are real and the reasoning in the
docstrings is sound.

The problem is underneath it. Three stacked data limitations:

**(a) The IAP tables are an unverified single-person transcription.**
`backend/growth/data/iap_2015_published_reference.json` exists specifically to hold a
second, independent reading of the paper so the CSVs can be checked cell-by-cell. I checked it:

```
"status": "AWAITING_DUAL_PERSON_VERIFICATION"
"values": { "boy_height_cm_IAP_5_18.csv": {}, ... all six empty }
```

**Zero of 1,134 numeric cells have been verified.** Your own `PROVENANCE.md` names this
as the top gap. Every downstream guarantee — the checksum lock, the exact-table
reproduction test, the validation suite — proves the *engine reproduces the CSVs*. None of
them prove the CSVs match the paper. A single mistyped digit anywhere in those 1,134 cells
is currently undetectable and would silently distort one centile at one age forever.

**(b) The published table is rounded to 1 decimal at 6-monthly steps — and you interpolate it monthly.**
Source rows look like `girl,5.0,97.2,100.5,103.9,107.5,...`. Rounding to 0.1 cm injects
up to ±0.05 cm of noise per knot. `curve_builder` then builds *monthly* anchors and PCHIPs
them. The result is a velocity ripple with no biological meaning. Measured on your engine,
boys P50 height:

| Age band | Velocity range implied by the rendered curve |
|---|---|
| 6–7y | 5.65 → 6.05 cm/yr (spread **0.40**) |
| 10–11y | 5.37 → 5.63 cm/yr (spread 0.26) |
| 13–14y | 5.01 → 5.87 cm/yr (spread **0.85**) |

A 0.85 cm/yr artefactual swing inside a single year is larger than many of the real
velocity differences a clinician is trying to detect.

> **Correction (10 Aug 2026):** (c) below is real and was fixed in M1.2, but it
> is not the largest defect in these tables. **Four of the seven height/weight
> columns — p10, p25, p75, p90 — are not published values at all.** They were
> filled in by dividing the p3–p97 z-range into six equal steps during
> transcription, so the line drawn as the 25th centile is the 26.5th and the
> 10th is the 10.5th: 0.27–0.48 cm and 0.30–0.77 kg of systematic error, present
> at every age, independent of the tail problem described here. Only p3, p50 and
> p97 carry independent information. See `backend/growth/iap_table_consistency.py`
> and correction 6 in `DELIVERY-STATUS-2026-08-10.md`.

**(c) The L,M,S triplets were never obtained — so the tails are extrapolated.**
Because only percentile *values* are available, `iap_reference.py` fits L and S per age row
and splines them, and — importantly — scores patient values by **linear interpolation in
value between the 7 drawn centiles**, extrapolating linearly beyond P3 and P97
(`_z_from_display_anchors`). For height this is fine, because height is nearly symmetric.
For **weight and BMI it is not**, because those distributions are strongly right-skewed.

I probed this directly. Taking the value that the engine's own LMS fit places at a given
z-score, then asking the engine to score that same value back:

| Sex | Measure | Age | Value | True z | App returns | Error |
|---|---|---|---|---|---|---|
| girls | weight | 6.0 | 43.62 kg | **+3.00** | **+3.81** | +0.81 |
| boys | weight | 6.0 | 38.69 kg | +3.00 | +3.56 | +0.56 |
| boys | weight | 10.0 | 76.10 kg | +3.00 | +3.54 | +0.54 |
| girls | weight | 6.0 | 11.99 kg | **−3.00** | **−2.61** | +0.39 |
| boys | weight | 10.0 | 17.16 kg | −3.00 | −2.64 | +0.36 |
| girls | height | 6.0 | 96.34 cm | −3.00 | −2.85 | +0.15 |

**Clinical consequence:** the lower tail is **systematically compressed toward the mean**.
A child whose weight is genuinely at −3.0 SD is reported at about −2.6 SD. WHO's
severe-underweight threshold is −3 SD, so **children who genuinely meet the severe
threshold are reported just above it** — a false-reassurance error, which is the worse
direction to fail in. The upper tail is inflated the same way, by up to +0.8 SD.

Two things this is *not*, which I checked rather than assumed:

- It is **not** a truncation. The engine will happily return z-scores far below −3 (I
  measured −6 to −8 for very low weights) — it extrapolates linearly without bound. The
  defect is bias near the threshold, not an inability to go past it.
- It is **not** a height problem. At height SDS −2.0 the engine is accurate to 0.02–0.04 SD
  at every age tested, so short-stature screening is safe.

A related smaller issue falls out of the same mechanism: because extrapolation beyond the
outermost centile is linear and unbounded, extreme inputs produce meaningless but
confident-looking numbers — a 40 cm height at age 6 scores as z = −12.9. Those should be
clipped or flagged as out-of-range rather than printed into a report.

Good news on the most-used threshold: I specifically checked height SDS = −2.0 (the short-stature
referral cut-off, which also sits in the extrapolated zone) and it is accurate to within
0.02–0.04 SD at every age. So **short-stature screening by height SDS is currently safe.**
The defect is confined to weight and BMI tails.

**The fix for all three of (a), (b) and (c) is the same one thing.** Khadilkar et al.,
*Extended growth charts for Indian children*, J Pediatr Endocrinol Metab 2021
(doi 10.1515/jpem-2020-0573) states that it used **"LMS values from IAP 2015 growth charts
(5–18 years) and WHO 2006 MGRS charts (<5 years)"** to construct −2.25, −2.5 and −3 SD
height lines. The IAP LMS values therefore exist in the authors' hands and have been used
in a peer-reviewed publication. Your `iap_reference.py` docstring currently says they
"were never published (available only on request from the authors)" — that is nearly right,
and the actionable half is *"available on request."*

With the real L,M,S in hand: the CSV transcription risk disappears, the rounding ripple
disappears, the tail extrapolation disappears, exact z at any value becomes a closed-form
Cole computation, and the `_z_from_display_anchors` workaround can be deleted entirely.
**One email to the HCJMRI / IAP Growth Charts Committee is the highest-leverage action in
this entire report.**

### 2.2 The 3.0–5.0y bridge is a two-year invented curve

`BLEND_LO = 3.0`, `BLEND_HI = 5.0`. Between those ages the displayed curve comes from
**neither WHO nor IAP** — it is a monotone quintic Hermite bridge fitted between them.
That is two full years of a child's chart, covering a heavily-used age band, showing
numbers that appear in no published reference.

And the bridge does not always preserve the true reference slopes. Measured, girls weight P3:

```
true WHO slope at 3.0y = 1.64 kg/yr  →  bridge uses 1.05  (−36%)
true IAP slope at 5.0y = 1.58 kg/yr  →  bridge uses 1.01  (−36%)
```

That damping is *deliberate and correctly reasoned* — it is what stops the curve from
visibly dipping when the two references disagree. The engineering is right. The problem is
the framing: a curve that is 36% off the published gradient is being presented to a
clinician as if it were reference data.

**Also note:** the official IAP position, and what the IAP's own 0–18y pediatrician-friendly
charts do, is a **hard switch at age 5** — WHO 2006 below, IAP above. There is no smoothing
in the published approach. Your bridge is a product invention, as the July audit already said.

Two defensible options, and I recommend the first:

1. **Switch at 5.0y, disclose the step.** Match the published Indian standard exactly.
   Render the discontinuity honestly (or draw both references as separate lines through the
   overlap) and label it. Clinicians already understand reference switches; they do not
   expect a vendor to invent a spline through one.
2. Keep the bridge, but shade the 3.0–5.0y band on the chart, label it "derived composite —
   not a published reference," and exclude it from any z-score used for a clinical
   threshold decision.

Also: the docstrings in `blend.py` and `unified_value_at_z` still say the window is
**4.0–5.0y** while the constant is **3.0**. Stale comments on a clinically-relevant
constant — worth a quick pass.

### 2.3 The charts show no pubertal growth spurt

This is almost certainly what you are actually seeing when you say the curves "aren't right."
Look at `_chart_preview_girls.png`: a smooth sigmoid that flattens after ~14y, with no
adolescent acceleration anywhere.

Differentiating your rendered P50 height curve:

| | Your chart's peak velocity | Khadilkar's published Indian velocity reference |
|---|---|---|
| Boys | 6.05 cm/yr at **12.2y** | 6.8 cm/yr at **13.5y** |
| Girls | 6.03 cm/yr at 10.1y | 6.6 cm/yr at 10.5y |

The *magnitude* is roughly defensible. The **timing in boys is 1.3 years early**, which is
clinically material — it is the difference between "this boy's spurt is late" and "this
boy's spurt is on time."

But the deeper issue is structural and worth being precise about, because it is widely
misunderstood: **a cross-sectional distance chart's P50 line is not any individual child's
growth trajectory.** Children enter puberty at different ages, so averaging across children
at each age smears the spurt out. A real, healthy child has a peak height velocity of
roughly 8–10 cm/yr; the reference median velocity is 6.6–6.8; your curve implies 6.0. All
three numbers are "correct" for different questions. The consequence is that a perfectly
normal child will appear to **cross centiles upward** during their spurt and downward
afterwards, and a doctor with only a distance chart cannot tell that apart from pathology.

**No amount of curve-fitting fixes this.** The fix is to add references the chart currently
lacks — see §5.1. This is a *missing feature*, not a bug, and it is the single biggest
clinical improvement available to you on the growth side.

### 2.4 Smaller growth findings

- **BMI upper centiles are unsupported.** IAP's published BMI table only goes up to the
  median (P3/P5/P10/P25/P50). P75/P90/P97 come from an L,S fit to lower-half-only data —
  extrapolating a skewed distribution's upper tail from its lower half. Either suppress
  those lines or mark them model-derived. (The IOTF adult-equivalent 23/27 cut-offs *are*
  published and correctly used — that part is right.)
- **Height/weight L,S series are unsmoothed.** `_build_series(..., smooth_ls=False)` for
  height and weight, `True` only for BMI. Per-row independent fitting gives jagged L(age)
  and S(age). This is currently masked for the 7 standard centiles by the exact-table path,
  but it leaks into the 3–5y bridge and any non-standard centile.
- **`rcpchgrowth` is AGPL-3.0** and is a hard dependency for your whole WHO layer. Network
  use triggers AGPL §13 — if doctors access this over a network you owe them the complete
  corresponding source of the combined work. You said licensing isn't a concern, and for a
  personal project it isn't; but the moment this reaches real doctors it is a live
  obligation. **Clean escape:** WHO publishes its LMS tables freely. Vendoring them as
  a handful of CSVs and computing Cole LMS yourself (you already have `lms_core.py`)
  removes the dependency, removes the AGPL question, and removes the two internal WHO
  seams you currently have to bridge around in `who_reference.py`. Worth doing anyway.

---

## 3. What "99% correct" can and cannot mean

You asked for 99% correct answers. I want to be straight with you, because getting this
target wrong is how good clinical products lose credibility.

**Split your system into two layers, and hold them to different standards.**

**Layer 1 — deterministic computation. Target: 100%, and it is testable.**
Given a reference table and an input, the z-score, percentile, table lookup, score sum and
interpolation must be exactly right. No uncertainty is involved. This covers the growth
charts, the RUS score arithmetic, the score→age lookup, QRISK3. **Here, 99% is not
ambitious enough — you should demand 100% against published test vectors, and you already
do this successfully for QRISK3.** That is the model to copy: QRISK3 reproduces its
published vectors exactly, so you can state its correctness as a fact. Do the same for
growth (needs the LMS values) and for TW3 (needs the licensed book).

**Layer 2 — bone age from an image. Target: 99% is not attainable, and not definable.**
This is not pessimism, it is what the ground truth is made of. Bone age *has no true value*
— the reference standard is itself an expert's reading, and two expert radiologists
routinely disagree by 0.5–1.0 year on the same film. A model that agreed with one reader
"99% of the time" would disagree with the next reader constantly. **You cannot be more
accurate than the definition of the thing you are measuring.**

What you should promise instead — all of which *are* measurable, and three of which your
architecture already supports:

1. **Agreement**: ≥95% of cases within ±1 year of expert consensus; report mean absolute
   difference and Bland–Altman limits of agreement, by sex and age band.
2. **Calibrated uncertainty**: a stated 90% interval that actually contains the truth 90%
   of the time. You already do split-conformal — currently measuring 89.47% empirical
   coverage against a 0.90 target, which is close and honestly reported.
3. **Abstention**: refuse to answer on films outside the validated distribution — poor
   image quality, fractures, implants, dysplasia, unusual acquisition. **A product that
   knows when to stay silent is what earns clinician trust; one that always answers loses
   it on the first embarrassing case.**
4. **Clinician-in-the-loop by construction**: the AI proposes, the doctor confirms, the
   record stores who confirmed what and when. You already have the adjudication queue and
   approval lifecycle for this.

Say this on the interface, in these words or similar: *"AI suggestion — requires
qualified clinical confirmation. Not an autonomous diagnostic device."* Your README and
audit already take this line. Hold it.

---

## 4. Problem 2 — TW3 bone age

### 4.1 The headline: what you are computing is not TW3

From `backend/tw3/tw3_tables.json`:

```
method:  TW3-C-RUS
source:  stage_to_score: Jing Gu, Yongming Meng, Haoxin Meng, "Deep Learning Approach for
         Bone Age Assessment Based on Improved TW3 Scoring Method", AIPR 2023, Table 1
         score_to_age: digitized from the same paper's Figure 8 "Standard" bone-maturity
         curve (PROVISIONAL, approximate +/- ~0.5y)
```

So the bone age currently produced rests on:

- **Per-stage point values** transcribed from *Table 1 of a deep-learning conference paper* —
  not from Tanner's TW3 book, and not from the Chinese TW3-C standard document either.
- **The score→age conversion digitized from a plotted figure** in that same paper — i.e.
  read off pixel positions on a graph.

That is a chain of two secondary sources for the two numbers that entirely determine the
output. The `is_calibrated()` check returns `True` and the app produces bone ages, so from
the outside this looks like a working TW3 implementation. It isn't one. **This is the single
most serious clinical accuracy issue in the product** — more serious than the growth charts,
because it is not a precision problem, it is a provenance problem.

The transcription self-check you have — that maximum grades sum to exactly 1000 — is a
genuinely clever invariant and worth keeping. But as your own July audit correctly noted,
it proves internal consistency, not that any individual cell is right, and certainly not
that a Chinese reference population is valid for Indian children.

Your own file records the smoking gun:

> *"Bone ages diverge from this centre's historical original-TWIII reports: e.g. the case-001
> films score 880 here vs the reported original-TW3 RUS 681."*

Running both scores through your curve:

| | Score 880 | Score 681 | Disagreement |
|---|---|---|---|
| boys | 14.83y | 13.92y | **0.92 years** |
| girls | 12.75y | 11.50y | **1.25 years** |

A one-year bone-age discrepancy changes management. It is the difference between reassurance
and a GH work-up.

### 4.2 The score→age curve is too coarse, and unusable below age 6

I probed the curve directly. It has **11 anchor points for boys and 10 for girls**, all at
integer years, connected by **straight lines**:

```
boys:  score 150–1000  →  bone age 6.0–16.0y
girls: score 270–1000  →  bone age 6.0–15.0y
```

Consequences, all measured:

- **Everything below the first anchor clamps to exactly 6.00y.** Scores of 50, 100 and 150
  all return 6.00y for boys; girls clamp below a score of 270. Any child with a bone age
  under 6 is silently reported as exactly 6.0, with no indication that the answer is a
  clamp rather than a computation — and paediatric endocrinology cares enormously about
  the 2–6y range. **This is the most serious defect in the curve.**
- **The top end is actually about right.** The curve maps score 1000 → 16.0y (boys) /
  15.0y (girls). Published TW3 RUS maturity is attained at **16.5y in males and 15.0y in
  females**, so girls are exact and boys are ~0.5y short. Credit where due: the digitization
  landed close here. (Note for anyone comparing against older literature: 18.2y/16.0y are
  the **TW2** maturity ages — TW3 deliberately rescaled adolescent skeletal ages downward
  by roughly a year, which is also why TW3 and TW2 bone ages are not interchangeable.)
- **Piecewise-linear between integer years** puts a kink at every anchor. The true TW3
  score→age relation is smooth and sigmoid.
- **Sensitivity is wildly non-uniform.** With all 13 bones at one grade, bumping the radius
  by a single grade moves bone age by:

| All bones at grade | Boys | Girls |
|---|---|---|
| 3 → radius 4 | 2 months | 0 months *(clamped)* |
| 4 → radius 5 | 6 months | 6 months |
| 5 → radius 6 | 5 months | 6 months |
| 6 → radius 7 | 3 months | 4 months |
| 7 → radius 8 | 4 months | 5 months |

One grade misread on one of thirteen bones costs up to half a year, and how much it costs
depends on where you are on a curve that was read off a JPEG. Real inter-observer staging
disagreement is far more than one grade on one bone.

### 4.3 The letters / 20-bone path is correctly gated — leave it that way

`letters_tables.json` is empty, `provenance` fields are blank, scoring is disabled, and
every value shows "—". **This is exactly right and you should resist the temptation to
fill it with anything but the real licensed tables.** The gate design here — dual
transcription, checksums, provenance fields, and reference cases that must reproduce before
scoring turns on — is better than what most commercial products do.

Two corrections to how it's framed, though:

- As established in §0, **there is no TW3 20-bone score.** `letters_tables.json` should
  hold *TW3 RUS (13)* and *TW3 Carpal (7)* as two independent systems with two independent
  score→age curves, never summed. If you want a genuine 20-bone score you must use **TW2**,
  which is a different, older standard with its own curve, and should be labelled as such.
- `LETTER_STAGES` offers A–I for every bone. In real TW3, **each bone has its own valid
  stage set** — most bones do not use all nine letters, and the radius/ulna differ from the
  phalanges. Offering all nine everywhere lets a doctor record a stage that does not exist
  for that bone. `constants.py` already flags this honestly; it should become a hard
  per-bone constraint once the licensed source is in hand.

### 4.4 The AI screening model, and the open-source answer

Your locked-test baseline (`baseline_screening_20260714.json`) is honest and it fails its
own gate:

| Metric | Measured | Your gate | Verdict |
|---|---|---|---|
| MAE | **8.99 months** | ≤6.0 | **FAIL** |
| Within ±12 mo | 75.65% | ≥90% | FAIL |
| Within ±6 mo | 45.05% | — | — |
| Bland–Altman LoA | **−23.8 to +22.1 months** | — | — |
| Conformal coverage | 89.47% | 0.90 | marginal |
| External Indian validation | none | — | — |

Those limits of agreement are the number to internalise: **for an individual child, this
model's output can be nearly two years off in either direction.** MAE of 9 months sounds
tolerable; ±23 months on a real patient is not.

The cause is not your pipeline, it is model capacity — a MobileNetV3-Small at 224px is a
small backbone for this task. And you do not need to close that gap yourself:

| Option | Population | Reported accuracy | Licence | Notes |
|---|---|---|---|---|
| **digiBONE** | RSNA + **2,430 Indian children (HCJMRI, Pune)** | **4.7 mo male / 4.9 mo female (segmental); 5.7 / 5.9 full-hand** — on *its own* Indian validation | **MIT** | Segmental GP: separate networks for short bones, carpals, wrist. Weights downloadable. <5s inference |
| **Deeplasia** | RSNA + dysplasia cohorts | 3.87 mo RSNA; 5.84 mo dysplastic | open | Prior-free; validated on skeletal dysplasias; beat all individual human raters in one study |
| Your current model | RSNA only | 8.99 mo — on the *frozen RSNA split* | yours | — |
| BoneXpert (commercial) | — | 6.36→4.68 mo on Indian validation | commercial | CE-marked; useful as a comparator benchmark |

> **Correction (10 Aug 2026):** the figures in this table are **not mutually
> comparable** and the original row for digiBONE misquoted them (4.75/4.93; the
> paper says 4.7/4.9 segmental and 5.7/5.9 full-hand, which was omitted). Each
> number is a different model on a different test set in a different population.
> Producing the comparable figure — digiBONE on *this* product's locked RSNA
> test — is step 4 of `backend/ai/DIGIBONE.md`, and the release gate treats the
> adoption as `CROSS_METHOD_ADOPTION` precisely so a like-for-like improvement is
> never claimed from numbers like these.

**digiBONE is close to a perfect fit for you** and I would treat adopting it as the
highest-priority bone-age action. It is MIT-licensed with downloadable weights; it is
trained on Indian children; it comes from **Khadilkar's own institute** — the same group
behind the IAP growth charts you already use, which makes it defensible to Indian
clinicians in a way an RSNA-only model never will be; and its **segmental** design (short
bones / carpals / wrist scored separately) maps naturally onto the per-bone reporting your
UI is already built for. Repo: `https://github.com/goellab/digiBONE`.

Note honestly what it is and isn't: digiBONE produces **Greulich–Pyle** bone age, not TW3
RUS. It replaces and greatly improves your *screening* path. It does not substitute for
licensed TW3 tables in the deterministic path. Keep the two clearly separate and never
average them.

### 4.5 Population bias is real, and a fixed offset is the wrong fix

851 Indian children aged 2–16.5y, four observers, three methods (Indian J Endocrinol Metab
2021), RMS deviation from chronological age:

| Group | GP | GR | TW3 |
|---|---|---|---|
| All | 1.21y | 1.18y | **1.11y** |
| Boys | 1.26 | 1.21 | **1.14** |
| Girls | 1.16 | 1.14 | **1.00** |
| Prepubertal boys | 1.28 | 1.29 | **1.06** |
| **Pubertal boys** | 1.21 | **1.09** | **1.37** ← TW3 is *worst* here |

Bone age was **underestimated in Indian boys at all ages regardless of method**; in girls
underestimated until the spurt then rapidly over-estimated after it.

So: TW3 is the best overall choice for Indian children — which validates your method
selection — **but it is the worst of the three in pubertal boys.** The direction and size of
the bias flip with sex and pubertal status. Your July audit already rejected the "transparent
fixed Indian offset" idea; **that judgement was correct and this data confirms it.** Any
calibration must be learned per subgroup (sex × age band × pubertal status) and validated
per subgroup, and each subgroup needs its own reported error. Your `monitoring/priors.py`
and subgroup reporting in the validation harness are the right places for this.

---

## 5. What to add — prioritised

### 5.1 P0 — do these first (highest clinical value per unit effort)

**1. Email the IAP Growth Charts Committee / HCJMRI for the IAP 2015 L,M,S triplets.**
Cite the 2021 extended-charts paper as evidence they exist. Zero code, unblocks everything
in §2.1. Do this today.

**2. Add a height-velocity chart.** Khadilkar et al., *Height Velocity Percentiles in
Indian Children Aged 5–17 Years*, Indian Pediatr 2019;56(1):23–8 — LMS-based P3–P97 Indian
velocity centiles, free at `indianpediatrics.net/jan2019/23.pdf`. **Height velocity is the
most sensitive single indicator of growth pathology and your product currently has no
velocity reference at all.** This directly answers §2.3. Requires two measurements ≥6 months
apart (enforce that interval — velocity computed over short intervals is dominated by
measurement error).

**3. Complete the 1,134-cell dual verification** of the IAP CSVs. Tedious, but it is the
only thing standing between you and being able to *state* that the growth charts are
correct. If the LMS values arrive first, this becomes largely moot — so do (1) before (3).

**4. Fix the weight/BMI tail scoring.** Until LMS arrives, replace linear-in-value
extrapolation beyond P3/P97 with an LMS-based tail, so that a child at a true −3.0 SD
weight is reported as −3.0 and not −2.6. Also clip or flag absurd out-of-range z-scores
rather than printing them (§2.1).

**5. Relabel the bone-age method honestly in the UI.** It currently reads as TW3. It should
say *"TW3-C (Chinese) RUS — provisional research curve, ±0.5y, digitized"* wherever a bone
age is shown, and the report should carry it too. This is a one-day change and it is the
difference between a defensible research tool and a misleading one.

**6. Clamp-guard the score→age curve.** Refuse to return a bone age when the RUS score
falls below the curve's first anchor, instead of silently returning the endpoint. Right
now scores of 50 and 150 both return "6.00y" with no indication that the answer is a clamp
— so the product is at its least reliable precisely where it looks most confident. The top
end is close enough to leave alone for now.

**7. Fix stale docstrings** in `blend.py` that say the blend window is 4.0–5.0y when
`BLEND_LO = 3.0`.

### 5.2 P1 — the substantial next tier

**8. Adopt digiBONE for the screening path.** MIT, Indian-trained, 4.7–4.9 mo segmental
(5.7–5.9 full-hand) on its own validation set. Run it
against your existing locked RSNA test set first so you have an apples-to-apples number
versus your 8.99 mo, then keep your release gate, conformal calibration and abstention
logic around it. Your gated-release harness means you can do this safely.

**9. Add Khamis–Roche adult height prediction.** Uses only child height, weight and
mid-parental height — **no X-ray, no licensed table** — and achieves ~90% within ±5.3 cm
for ages 4–17.5. Coefficients are freely published. This gives you a real adult-height
prediction *today*, which you currently lack (you have mid-parental target height only,
and the July audit correctly flagged that mislabelling these as the same thing is an error).
Present target height and predicted height as two distinct quantities, always.

**10. Build the Indian validation cohort.** 200–300 local films with two independent
expert readings each, frozen as an external test set, stratified by sex and pubertal
status. **This is the asset that makes everything else claimable.** Nothing you do with
models substitutes for it. Your `carve_locked_test.py` / `leak_guard.py` infrastructure
already handles the mechanics.

**11. Bone-age-conditioned growth interpretation.** You compute bone age *and* plot growth
charts and currently don't connect them. Plot **height-for-bone-age** alongside
height-for-chronological-age. A short child whose height is normal for their bone age is a
constitutional delay; one who is short for both is a different problem. This is the kind of
integration that makes a doctor prefer your tool over two separate ones — and it is the
clinically correct way to handle the tempo problem from §2.3.

**12. Tanner pubertal staging capture (B/G and PH stages, testicular volume, menarche).**
Cheap to build, and it is the missing variable that makes velocity, bone age and height
prediction interpretable. Also required to stratify the §4.5 subgroup bias correctly.

### 5.3 P2 — differentiators, once the foundation is solid

- **Mid-parental height + target range** on the chart itself, with the ±2 SD genetic corridor drawn.
- **Longitudinal tracking with conditional SDS** — the statistically correct way to ask
  "has this child's growth *changed*", as opposed to comparing two independent z-scores.
- **Specialist charts**: Turner, Down syndrome, achondroplasia, and preterm/corrected-age
  (Fenton or INTERGROWTH-21st). Indian paediatricians currently have to leave the app for these.
- **BMI → obesity work-up prompts** using the IAP/IOTF 23/27 cut-offs you already compute
  (acanthosis, BP centile, lipids, HbA1c).
- **Blood-pressure centiles by height** — height-indexed BP percentiles are tedious by hand
  and you already have the height z-score infrastructure.
- **Bilingual output.** You already have a Marathi-bilingual clinical-summary skill in your
  toolchain; parent-facing Hindi/Marathi summaries would materially help adherence.
- **DICOM ingestion and anonymisation on upload** — `pydicom` is already a dependency.
- **ABDM / ABHA alignment** for India (FHIR-shaped records) if you ever want interoperability.

---

## 6. Open source you can integrate directly

| Project | Use | Licence | Verdict |
|---|---|---|---|
| **digiBONE** (`goellab/digiBONE`) | Indian-trained segmental GP bone age, pretrained weights | **MIT** | **Integrate.** Best available fit |
| **Deeplasia** | Prior-free bone age; robust to dysplasia | open | Use as a second opinion / cross-check model |
| **BoNet** (`BCV-Uniandes/Bonet`) | Hand pose + per-bone ROI localisation | open | Solves your per-bone localiser gap |
| **RHPE** dataset (6,288 films, Colombian) | **External** validation on a non-RSNA population | research use | Your `baar_to_jsonl.py` already anticipates this |
| Digital Hand Atlas | Additional multi-ethnic validation films | research use | Supplementary |
| **WHO LMS tables** (published directly by WHO) | Replace the AGPL `rcpchgrowth` dependency | free | Removes both the licence issue and two internal seams |
| `gamlss` / `scipy` | Refit LMS properly if you must fit rather than obtain | GPL / BSD | Only needed if the IAP LMS request fails |
| **SITAR** (R, `sitar`) | Size/tempo/velocity decomposition of individual growth | GPL | The rigorous answer to the tempo problem in §2.3 |
| `pydicom`, `onnxruntime` | Already in use | permissive | Keep |
| `rcpchgrowth` | Currently your WHO layer | **AGPL-3.0** | **Plan to replace** — see §2.4 |

---

## 7. Earning trust with Indian doctors

You said you want authenticity, starting from yourself, aimed specifically at Indian
clinicians. Concretely, what earns that:

1. **Show provenance on every number.** Next to each output: which reference, which
   version, verified or provisional. You already have the data model for this
   (`table_version`, `calculation_version`, `checksum_verified`) — surface it in the UI
   rather than keeping it in the backend.
2. **Publish your validation report.** Your `baseline_screening_20260714.html` is a real
   validation artefact with subgroups and Bland–Altman. Make it a public page. A tool that
   publishes "MAE 8.99 months, gate FAIL, working on it" is more credible than one claiming
   99% with no evidence. **Doctors are trained to distrust unsourced confidence.**
3. **Cite Indian references by name** — Khadilkar, IAP 2015, IOTF Asian cut-offs, LAI for
   lipids, ICMR. Indian clinicians know these names and notice when a tool uses WHO defaults
   for Indian children.
4. **Show disagreement rather than hiding it.** When the AI and the doctor's staging differ,
   or two methods differ by more than a threshold, surface it and route to re-review. Your
   adjudication queue already does this — it is a feature to advertise, not an
   embarrassment.
5. **Keep the abstention behaviour.** Refusing hard films is a trust-builder.
6. **Recruit 3–5 paediatric endocrinologists as design partners early**, ideally including
   someone from a centre that already reports TW3. They can supply the historically-reported
   reference films that let you validate the score→age curve — which is exactly what your
   `curve_validation.reference_cases` block is waiting for.
7. **Get the licensed TW3 book.** One legally-purchased copy of Tanner et al. 2001 unblocks
   the entire deterministic path, and your transcription gates are already built to receive
   it safely.

---

## 8. If I could do only five things

1. **Email for the IAP 2015 L,M,S triplets.** Free, today, fixes most of §2.
2. **Add the Indian height-velocity chart** (Khadilkar 2019). Biggest clinical gain available.
3. **Relabel the bone age as provisional TW3-C, and clamp-guard the curve.** Stops the
   product overstating itself. One day of work.
4. **Swap in digiBONE** behind your existing release gate. (Corrected 10 Aug 2026: do NOT
   read this as "8.99 mo → ~4.8 mo" — that compares two models on two different test sets.
   Measure digiBONE on the locked RSNA split first; §5.2 item 8 says so correctly.) With Indian
   provenance.
5. **Start the 200-film dual-read Indian validation set.** The only thing that ever lets you
   make an accuracy claim at all.

---

## 9. Closing assessment

The growth-chart problem is a **data-acquisition problem wearing a numerical-methods
costume**. You have been fixing it with increasingly sophisticated splines — quintic
Hermite bridges, curvature matching, monotonicity guarantees — and that work is genuinely
good, but it is compensating for a rounded, unverified, LMS-less source table. One email
does more than another spline will.

The bone-age problem is more serious than you framed it. It is not that TW3 needs better
data; it is that **the current output is not TW3 at all**, and rests on a figure digitized
from a conference paper. The honest short-term move is to relabel it and gate it. The
honest medium-term move is to buy the book and build a local validation set.

And the premise to drop is the 20-bone TW3 method — it does not exist. What you can build
instead is better: per-bone visibility and staging across all 20 structures for
interpretability, TW3 RUS as the scored standard, carpals reported separately, and an
Indian-calibrated AI screening layer with calibrated uncertainty and the good sense to
abstain.

Aim for **100% on the deterministic layer** — provable, and you have already done it once
with QRISK3. Aim for **calibrated, subgroup-reported, abstention-capable agreement** on the
image layer. That combination is what a paediatric endocrinologist will actually trust, and
it is more valuable than a 99% claim nobody can verify.

---

### Sources

- [Comparison of Bone Age Assessments by Greulich-Pyle, Gilsanz-Ratib, and Tanner Whitehouse Methods in Healthy Indian Children (Indian J Endocrinol Metab 2021)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8547392/)
- [digiBONE: an automated tool for segmental Greulich-Pyle bone age assessment of Indian children and adolescents (Frontiers Endocrinol 2026)](https://www.frontiersin.org/journals/endocrinology/articles/10.3389/fendo.2026.1757571/full)
- [digiBONE source repository (MIT)](https://github.com/goellab/digiBONE)
- [Deeplasia: prior-free deep learning for pediatric bone age assessment robust to skeletal dysplasias (medRxiv)](https://www.medrxiv.org/content/10.1101/2023.03.07.23286906v2.full)
- [Automated bone age assessment in rare pediatric growth disorders: a comparative study using Deeplasia](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12921578/)
- [Extended growth charts for Indian children (J Pediatr Endocrinol Metab 2021)](https://www.degruyterbrill.com/document/doi/10.1515/jpem-2020-0573/html?lang=en)
- [Height Velocity Percentiles in Indian Children Aged 5–17 Years (Indian Pediatr 2019)](https://pubmed.ncbi.nlm.nih.gov/30806356/)
- [Growth Velocity in South Indian Children Between Three and 18 Years of Age](https://pmc.ncbi.nlm.nih.gov/articles/PMC10799202/)
- [Pediatrician-friendly IAP Growth Charts for 0–18 years (IAP)](https://iapindia.org/pdf/4422_Pediatrician-friendly-growth-charts-for-0-18-year-old-Indian-children-Dr-Bakul-Parekh-and-Dr-Vaman-khadilkar.pdf)
- [Tanner–Whitehouse Skeletal Ages: TW2 or TW3? (Sports Medicine)](https://link.springer.com/article/10.1007/s40279-017-0799-7)
- [Skeletal age assessed by TW2 using 20-bone, carpal and RUS score systems (PLOS One)](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0271386) — source for TW3 RUS maturity being attained at 16.5y (males) / 15.0y (females)
- [Comparison of TW2 and TW3 skeletal age differences in a Brazilian population](https://pmc.ncbi.nlm.nih.gov/articles/PMC4327457/) — TW2 vs TW3 rescaling
- [TW3 bone age: RUS/CB and gender differences of percentiles (Ann Hum Biol)](https://pubmed.ncbi.nlm.nih.gov/15513693/)
- [The RSNA Pediatric Bone Age Machine Learning Challenge (Radiology)](https://pubs.rsna.org/doi/abs/10.1148/radiol.2018180736)
- [Bone Age Assessment Resources / RHPE dataset (Uniandes)](https://bcv-uniandes.github.io/baar-wp/)
- [BoNet: Hand Pose Estimation for Pediatric Bone Age Assessment](https://github.com/BCV-Uniandes/Bonet)
- [rcpchgrowth-python (AGPL-3.0)](https://github.com/rcpch/rcpchgrowth-python)
- [SITAR growth curve analysis (CRAN)](https://cran.r-project.org/web/packages/sitar/sitar.pdf)
- [Variation in methods of predicting adult height for children with idiopathic short stature](https://pubmed.ncbi.nlm.nih.gov/20974789/)
