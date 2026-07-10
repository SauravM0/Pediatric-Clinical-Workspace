# Bone Age — Accuracy, Feedback & Self-Improvement Report

**Prepared as:** senior engineer + ML lead + pediatric-endocrinology-aware clinical reviewer
**Scope:** The bone-age subsystem only — `backend/tw3/`, `backend/ai/`, `backend/api_bone_age.py`, and the Bone Age panel in `frontend/index.html`.
**Date:** 2026-07-10
**Deliverable:** Findings + recommendations. No code changed in this pass.

---

## 0. Read this first — the one thing that will save you months

You asked for an AI that "goes on the internet every day and researches X-rays to become smarter." I need to be honest with you as your engineer, because getting this wrong is expensive: **a bone-age model does not get more accurate by browsing the internet.** Reading web pages is not how a neural network learns skeletal maturity. A model only improves when it is *retrained on more correctly-labelled hand X-rays* and then *re-validated against known-correct cases before the new version is allowed to go live.*

The good news is that the *spirit* of what you want — a system that gets measurably better every week from real use — is completely achievable, and your codebase is already 70% built for it. The mechanism is a **data flywheel**, not a web crawler:

> Every X-ray a doctor grades → becomes a labelled training example → periodically retrains the model → the new model is tested against a locked validation set → only if it beats the current model does it ship.

The **suggestion box you described is the single most valuable piece of that flywheel.** It is exactly the right instinct. This report shows how to build it so the corrections actually make the model smarter instead of quietly poisoning it.

There is also a real, useful role for "research the internet every day" — just not for changing the model's numbers. I cover that in §7.4.

---

## 1. How bone age works in the product today

There are **two completely different bone-age numbers** in the system right now, and understanding the split is the key to everything else:

**(A) The AI screening estimate** — `backend/ai/boneage.py`, model `boneage-gp-mnv3s-ft-colab-2026-07-05`.
A MobileNetV3-Small ONNX model takes the *whole* hand image + sex and regresses a single bone-age number. It is a **Greulich–Pyle-style** estimate, trained on the **RSNA (US) dataset**, held-out **MAE ≈ 8.6 months (0.72 yr)**. The code is admirably honest about this: it labels the number "screening, not TW3," attaches a ±1-MAE uncertainty band, gates low-trust images (WhatsApp/photo-of-film), and prints the Indian-population caveat. This is the "instant number when you attach an X-ray."

**(B) The TW3-RUS clinical result** — `backend/tw3/scoring.py`.
The authoritative path. A clinician stages the 13 RUS bones (A–I / grades 1–8); the deterministic engine sums the licensed per-stage points → RUS maturity score → bone age. Pure, reproducible, never guesses. **But it is dark until someone enters the licensed TW3 conversion tables** — the point-scores and the score→age curve are copyrighted (Tanner et al., 2001) and are not bundled. Today `score_to_age.girls` has only **two real anchor points** (681→12.1 yr, 713→12.4 yr) derived from two of Dr. Rathod's reports. That is not a curve; it is two dots.

**The staging itself is still manual.** The automatic staging models (PEARLS-style: PEA to find the bones, RL to classify each bone's stage) are **designed but not built** — `backend/tw3/README.md` is explicit that this needs a wide-age, stage-annotated archive of Indian films that does not exist yet.

So the honest status of the product today: **a very well-engineered skeleton with an under-powered screening model bolted on top, and the accurate method (TW3) waiting on two things it doesn't have — licensed tables and labelled Indian training data.**

---

## 2. The current problems, ranked

I'm criticising hard because you asked me to. Note that much of this is *deliberate honesty* in the current design, not sloppiness — I've flagged which is which.

| # | Problem | Severity | Nature |
|---|---------|----------|--------|
| B0-1 | Two bone ages (GP screening vs TW3) can confuse the reader; the "instant" number is the *less* accurate one | 🔴 | Design/UX |
| B0-2 | Screening model MAE ≈ 8.6 mo, US-trained, not India-calibrated | 🔴 | Data/accuracy |
| B0-3 | TW3 score→age curve is 2 anchor points for girls, none for boys — the accurate path is effectively offline | 🔴 | Data/licensing |
| B0-4 | **No feedback capture loop exists** — when a doctor overrides the AI, that correction is thrown away | 🔴 | Missing flywheel |
| B1-1 | No automatic staging (PEA/RL unbuilt); needs stage-annotated Indian films | 🟠 | Data/ML |
| B1-2 | Single-rater labels carry 25–40% stage noise (your own `consensus.py` says so) | 🟠 | Label quality |
| B1-3 | Only one "other method" (GP) exists, and it's the screening model; no true multi-method cross-check | 🟠 | Feature gap |
| B1-4 | No drift / accuracy monitoring over time; you can't currently prove the model is improving | 🟠 | MLOps |
| B2-1 | Image-domain trust is user-declared / inferred, not measured from pixels | 🟡 | Robustness |
| B2-2 | No patient identity on the assessment (carried over from the UI/UX report) — corrupts any audit trail the flywheel depends on | 🟡 | Safety/data |

### The details that matter

**B0-2 — the screening model is the weak link.** MAE 8.6 months means the "instant" number is routinely off by two-thirds of a year, and it was trained on American children. Published data are clear that Greulich–Pyle **overestimates** skeletal age in Indian children — Indian boys run ~0.7 yr and girls ~0.33 yr *behind* the GP/US standard, worst in mid-to-late childhood. So the screening number carries **two stacked errors**: model error (±8.6 mo) *plus* a systematic population bias (~4–8 mo) in the same direction for boys. The code's caveat text is correct; the number underneath it is just not good enough to lead with. For reference, the RSNA-challenge winner reached MAE ≈ 4.3 months and modern models sit below 6 — so **~2× accuracy is available from data and training alone**, before any India calibration.

**B0-4 — you are currently burning your most valuable asset.** Every time a doctor looks at the AI's "12.1 yr," disagrees, and types the real value, that is a *free, expert-labelled, India-specific training signal* — and right now it evaporates. The `Radiograph` and `TW3Assessment` tables persist the *final* assessment, but there is no record of "AI said X, human corrected to Y, on this image." This is the gap your suggestion box closes, and it's why your instinct is correct.

**B1-2 — label noise caps everything.** Your own `consensus.py` header states it: a single rater agrees with a second expert only 58–76% of the time on hard bones, so single-rater labels carry 25–40% noise, and majority-vote across three raters drops it below 8%. **A model can never be more accurate than the labels it learns from.** If the suggestion box collects one number per image with no consensus mechanism, you'll build a fast pipeline for teaching the model one person's mistakes.

---

## 3. The suggestion box — designed properly

Your idea: **beside the attached X-ray image, add a box where a clinician enters the bone age they believe is correct.** Yes. Build it. Here is the design that turns it from a comment field into a learning engine.

### 3.1 Where it goes
Directly under the AI screening card in the top upload row (`frontend/index.html` around line 2515–2549, right after the "Use as bone age" button). The AI shows its estimate; immediately below sits the correction box. The visual story becomes: *"AI thinks 12.1 yr — do you agree? If not, tell us the right answer."*

### 3.2 What it must capture (this is the important part)
A bare number is weak training data. Capture the minimum that makes a correction *trustworthy and reusable*:

- **Corrected bone age** (the number the clinician enters).
- **Method they used to decide it** — a small dropdown: `TW3-RUS`, `Greulich–Pyle`, `Clinical judgement`, `Other`. Without this, you can't compare like with like, and you'd mix incompatible scales.
- **Confidence** — a 3-point selector (low / medium / high). Low-confidence corrections should be weighted down, not treated as ground truth.
- **The image reference + image quality domain** (you already track `source_domain`). A correction on a blurry WhatsApp photo is not the same evidence as one on a clean DICOM.
- **Rater identity** (even just an initials/ID field). This is the *precondition* for multi-rater consensus (B1-2). Without knowing *who* said what, you can never de-noise labels.
- **Timestamp + app/model version** (you already have the audit-event pattern in `assessment_service.py` — reuse it).

### 3.3 Data model
Add one table, don't overload the existing ones:

```
bone_age_feedback
  id, radiograph_id (FK), assessment_id (FK, nullable),
  ai_estimate_months, ai_model_version,
  corrected_age_months, method, confidence,
  rater_id, image_domain, note (free text, optional),
  created_at, app_version
```

This mirrors your existing `AuditEvent` philosophy — immutable, versioned, attributable. It is deliberately *separate* from `TW3Assessment` so that feedback is an evidence log, not a clinical result.

### 3.4 The safety rules (do not skip these)
1. **A suggestion is never automatically the patient's result.** It's logged as evidence. The clinical report still comes from confirmed TW3 staging. (Your codebase already lives by this "AI suggests, human confirms" rule — keep it.)
2. **Corrections do not touch the live model.** They accumulate. Retraining is a separate, gated, reviewed step (§7).
3. **Show the loop back to the user.** A tiny "Thanks — this will help improve accuracy for children like this one" confirmation makes clinicians actually use it. Adoption is the whole game.

### 3.5 Why this specific design makes the model smarter
Because each row is *(image, expert answer, method, who, how sure, image quality, model version)*, you can later: filter to high-confidence TW3 corrections on clean images, run consensus across raters, and retrain on exactly the cases where the current model was wrong — which is the fastest possible way to raise accuracy. That is the flywheel in §7, and this box is its intake valve.

---

## 4. Showing multiple methods (TW3 default, others below in medium font)

Your plan: **TW3 stays the default, headline number; below it, in medium font, show the bone age as computed by other methods, to demonstrate breadth and build trust.** This is a good clinical instinct — cross-method agreement is genuinely reassuring, and disagreement is itself useful information. Two constraints keep it honest:

**Constraint 1 — the copyright wall.** You cannot print numbers from methods whose tables you aren't licensed for and don't possess. The project already removed Bayley–Pinneau and Greulich–Pyle *tables* for this reason. So "show all the methods" must mean methods you can compute *legitimately*:

- **TW3-RUS** — headline, once licensed tables are entered. (default)
- **TW3 letters / TWII / TWII'20** — you already scaffold these in `letters_scoring.py`; they activate with the same licensed table entry.
- **Greulich–Pyle (model-based)** — you can show this *today*, because it's your own trained model's estimate, not a copyrighted atlas table. Label it "GP-style, model estimate."
- **Carpal TW3** — you already compute a separate carpal score/age; showing RUS-vs-carpal agreement is clinically meaningful.

**Constraint 2 — present agreement, not a wall of numbers.** The UI/UX report already flagged the Bone Age panel as the most cognitively overloaded screen (three ages + walls of caveats). So don't just stack four numbers. Show:

```
Bone age (TW3-RUS)              12.4 yr        ← large, default
  Cross-check
  GP-style model estimate       11.8 yr  (±8.6 mo)   ← medium, muted
  TW3 carpal                    10.9 yr             ← medium, muted
  Agreement: within ~0.6 yr ✓                        ← the trust signal
```

The **"Agreement" line is the trust-builder you're actually after** — it says "our methods corroborate each other" in one glance, which is far more convincing to another clinician than four raw numbers. When methods *disagree* by more than a threshold, surface that as a soft flag ("methods differ by >1 yr — re-check staging / image quality"), because in practice that usually means a mis-staged bone or a bad image.

**On "more formulas than just TW3":** be careful here. Adding methods you can't validate on Indian children doesn't increase accuracy — it increases the number of ways to be wrong. The credible path to "more accurate than any single formula" is not *more atlases*; it's **an ensemble that is calibrated to your own population** (§7.3). Breadth for trust: yes, show cross-checks. Breadth for accuracy: only via population-calibrated ensembling, not by importing more Western tables.

---

## 5. Automatic staging — the real accuracy unlock (medium term)

The headline accuracy problem is that TW3 today needs a human to stage 13 bones. The PEARLS-style plan in your README is the right architecture:

1. **PEA** — detect/locate the 13 RUS bones on the image.
2. **RL** — classify each located bone's maturity stage (A–I) as an ordinal problem.
3. **S** — stages → RUS score → bone age. ✅ Already built (`scoring.py`).

You already built module 3 and the *data pipeline* (`pipeline/build_dataset.py`) that turns radiology reports into labelled records and prints a stage-coverage grid. The blocker is purely **data**: the two seed cases cover only 18 of 117 (bone × stage) cells because they're the same age. You need films spanning a **wide age range** so every stage of every bone is represented, each paired with its report's per-bone stages. Your own pipeline already tells you this and measures it — that's excellent engineering foresight.

This is where the suggestion box compounds: if the correction UI is later extended to let a clinician confirm *per-bone stages* (not just the final age), every graded case becomes a PEA/RL training record. Start with final-age feedback (§3), evolve toward per-bone stage capture.

---

## 6. What "self-learning, every day" should actually mean

Let me translate your vision into the four things that are real, in priority order.

**6.1 It learns from use, not from browsing.** Every doctor-confirmed case (via the suggestion box and the assessment lifecycle) is a new labelled example. That is the learning. The "brain" doesn't sit and study overnight; it accumulates evidence and is *retrained on a schedule*.

**6.2 "Daily" is the wrong cadence for retraining; it's the right cadence for monitoring.** You don't want a model that silently changes its answers every morning — in medicine that's a liability, because a number that means one thing today and another tomorrow is untrustworthy and un-auditable. What *should* happen daily is **monitoring**: log every AI-vs-human gap, chart the running MAE, and alert when it drifts. Retraining happens when you've accumulated enough new corrections to matter (e.g. every N cases, or monthly), as a reviewed release.

**6.3 Every new model must pass a locked validation gate before it ships.** This is the guardrail that makes continual learning safe. The research on continual learning in medical imaging is blunt about the failure mode: models suffer **catastrophic forgetting** (learning new cases while losing old accuracy) and **feedback-loop drift** (a slightly-biased correction stream slowly pulls the model off-true). The defenses are standard and you should adopt them: (a) a **frozen "golden" validation set** of expert-consensus cases that never changes, (b) **shadow deployment** — the new model runs silently alongside the old one and must beat it on that golden set before promotion, (c) **keep old data in the retraining mix** so nothing is forgotten, (d) **human review of the diff** before any promotion.

**6.4 The legitimate role for "research the internet every day."** This is real and worth building — just keep it *away from the model weights*. A scheduled daily/weekly agent can: monitor PubMed/medRxiv for new bone-age methods, Indian reference data, and TW3/GP validation studies; watch for new open datasets you could train on; and summarise anything relevant into a digest for you. That keeps *you and the roadmap* current. It informs decisions; it never silently edits the model. (This app already has scheduled-task capability — a weekly "new bone-age literature" digest is a quick win.)

---

## 7. The self-improvement loop, concretely

Putting it together, here is the pipeline to build, in order:

**7.1 Capture** (build now) — the suggestion box (§3) + reuse the audit log. Every AI estimate and every human correction is stored with full provenance. *Without this, nothing downstream is possible.*

**7.2 Curate** (build next) — a small review view that: groups multiple raters' answers per image and runs your existing `consensus.py` to produce de-noised labels; routes disagreements to adjudication; filters by confidence and image quality. Output: a clean, growing, India-specific labelled set.

**7.3 Retrain + calibrate** (periodic, off-device on a free Colab/Kaggle GPU, as your `RETRAIN.md` already documents) —
  (a) First and cheapest win: **retrain the existing screening model on the full RSNA set** (12,611 images vs the ~1,425 it saw). Your own docs estimate this moves MAE from ~14 → ~6–9 months. Do this first; it's mostly free.
  (b) Then **calibrate to Indian children**: fit a correction offset/curve (the ~0.3–0.7 yr GP bias) from your accumulated corrections, or fine-tune on them. This is where your data flywheel starts beating any off-the-shelf model, because *no one else has your population's labels.*
  (c) Longer term: build **PEA/RL** for automatic TW3 staging (§5) once the labelled archive is wide enough.

**7.4 Validate + gate** (every time) — golden-set evaluation, shadow mode, beat-the-incumbent-or-don't-ship, human sign-off (§6.3).

**7.5 Monitor** (daily) — running MAE of AI-vs-human, drift alerts, coverage of the stage grid, and a literature digest (§6.4).

The elegant part: **you've already built 7.1's storage patterns, 7.2's consensus math, 7.3's trainer and retrain docs, and 7.4's honesty discipline.** The missing glue is the feedback table, the capture UI, and the scheduled monitoring — not a research project.

---

## 8. Prioritised backlog

**Do first (days, high leverage):**
1. **Build the suggestion/correction box + `bone_age_feedback` table** (§3). Unlocks everything.
2. **Retrain the screening model on full RSNA** (§7.3a). ~2× accuracy, essentially free.
3. **Add the "cross-check + agreement" display** (§4) — trust win, no new data needed.
4. **Enter the licensed TW3 tables** for at least girls, ideally both sexes (§B0-3). Turns the accurate path on. (Requires your licensed source — an ops task, not an engineering one.)

**Do next (weeks):**
5. **Daily monitoring**: log AI-vs-human gap, chart running MAE, drift alert.
6. **Consensus review view** wiring `consensus.py` to real multi-rater feedback (§7.2).
7. **India calibration offset** from accumulated corrections (§7.3b).
8. **Weekly literature digest** scheduled task (§6.4).

**Do later (months, needs data):**
9. **PEA + RL automatic staging** once the wide-age labelled archive exists (§5).
10. **Population-calibrated ensemble** (TW3 + GP model + carpal) as the "more accurate than one formula" answer (§4).

---

## 9. The uncomfortable truths, said plainly

- The number you show *fastest* today (the AI screening estimate) is the *least* accurate one, and it carries a known bias against Indian children. Fix its accuracy (§7.3a/b) or demote it visually — don't let speed masquerade as authority.
- "Learn every day from the internet" as literally described would make a medical device *less* trustworthy, not more. The version that works — learn from graded cases, retrain on a schedule, gate every release — is slower-sounding but is the only one that's safe and auditable.
- You cannot out-accuracy a data problem with more formulas. One well-calibrated method on your own population beats five imported Western atlases. The suggestion box is worth more than any new formula because it builds the one thing no competitor has: **labelled Indian hand X-rays.**
- Label quality is the ceiling. Single-rater feedback teaches the model one person's errors; multi-rater consensus is what makes it genuinely smart. Capture rater identity from day one.

The core compliment: this codebase is unusually honest and well-structured for a medical tool — the calibration gates, the "never guess," the AI-vs-TW3 separation, the coverage-grid pipeline. You're not starting from scratch; you're closing a loop that's already three-quarters drawn.

---

## Sources

- RSNA Pediatric Bone Age ML Challenge — winner MAD ≈ 4.3 mo; modern DL MAE < 6 mo. [Radiology / RSNA challenge](https://pubs.rsna.org/doi/full/10.1148/radiol.220505), [SOTA overview](https://www.emergentmind.com/topics/rsna-bone-age-challenge-dataset)
- GP overestimates / is delayed in Indian children (boys ~0.7 yr, girls ~0.33 yr); TW3 slightly more consistent. [Applicability of GP to Indian children (PubMed)](https://pubmed.ncbi.nlm.nih.gov/22014975/), [GP vs GR vs TW in Indian children (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8547392/), [Automated vs manual in Indian ethnicity (Springer)](https://link.springer.com/article/10.1007/s00247-022-05516-2)
- Continual learning risks in medical imaging — catastrophic forgetting, drift, feedback loops, and mitigations. [Continual learning review (arXiv)](https://arxiv.org/html/2312.17004v4), [Detection & correction of model degradation (arXiv)](https://arxiv.org/pdf/2506.17442)
- Robustness of DL bone-age models to image variation. [Computational stress testing (Radiology: AI)](https://pubs.rsna.org/doi/full/10.1148/ryai.230240)

*Internal code reviewed: `backend/tw3/scoring.py`, `constants.py`, `consensus.py`, `README.md`; `backend/ai/boneage.py`, `train_boneage.py`, `RETRAIN.md`, model metadata `boneage_gp.json` (MAE 8.6 mo); `backend/api_bone_age.py`; `backend/assessment_service.py`, `models.py`, `db.py`; `frontend/index.html` bone-age panel; prior `UIUX-critique-report.md`.*
