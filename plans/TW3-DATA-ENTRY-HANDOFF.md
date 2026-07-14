# TW3 Bone-Age Data-Entry — Handoff for a New Session

**Purpose:** paste this into a fresh chat so it has the full context and does NOT repeat
the mistakes below. This summarises (a) what the product's TW3 20-bone analysis actually
is, (b) exactly what data is still needed, and (c) the objective checks any candidate
table must pass — because six AI-reconstructed tables have already failed them.

⚠️ **TW3 = Tanner–Whitehouse 3 (a pediatric bone-age method). NOT "The Witcher 3."**

---

## 1. What the product is / two different "bone age" systems

- **Pediatric clinical workspace** (FastAPI + static frontend). Bone age via the **TW3**
  skeletal-maturity method from a hand-wrist X-ray. Decision-support only; a clinician
  confirms every result. India-focused (uses IAP/Khadilkar growth references elsewhere).
- **System A — whole-image AI screening** (`backend/ai/boneage.py`): a Greulich-Pyle
  whole-image estimate → ONE number. **NOT TW3, NOT 20 bones.** MAE ≈ 8.6 months (trained
  on full RSNA). It is a **triage / cross-check suggestion only.**
- **System B — TW3 20-bone structured report** (`/api/bone-age/report`, `backend/tw3/`):
  the real per-bone analysis of **all 20 bones = 13 RUS + 7 carpal**, each with stage,
  visibility, confidence, points, and a **separate RUS bone age and carpal bone age**
  (never averaged). **This is the "TW3 20-bone analysis."**

## 2. Does the TW3 20-bone analysis exist and give accurate bone age? YES — with one condition

- The 20-bone report is **built, tested, and verified end-to-end.** A synthetic-fixture
  test proves the whole chain: enter licensed tables → 4 gates pass → `/report` returns
  real, separate RUS + carpal ages across all 20 bones.
- **BUT by default scoring is OFF.** The copyrighted TW3 point tables + score→age curves
  are not bundled (they must be lawfully licensed and entered). Until then the report shows
  the 20-bone **staging framework** with "—" for scores/ages.
- Today the **doctor stages the 20 bones manually.** The AI does **not** auto-read them yet
  (automatic per-bone localizer + stager = "Plan 4", code exists but no trained models —
  needs a GPU + labeled data).
- **So "accurate TW3 bone age" is blocked ONLY on entering real, correct licensed tables.**

## 3. The four activation gates (ALL must pass for scoring to switch on)

1. **calibrated** — every bone has point values; each score→age curve has ≥2 anchors.
2. **reference_cases reproduce** — the clinic's OWN historically-reported films re-score
   within tolerance (default ±0.3 yr).
3. **provenance complete** — real book edition + a real person who entered AND a different
   real person who verified.
4. **checksum locked** — the table is checksum-verified and unaltered.

`scoring_ready = calibrated ∧ reference_cases ∧ provenance ∧ checksum`.

## 4. Exact data still needed (from a LICENSED TW3 copy)

1. RUS stage points — 13 bones × A–I × boys & girls (ulna A–H, no I).
2. **RUS score→age curve (50th centile), boys & girls** ← the piece that turns points into an age.
3. Carpal stage points — 7 carpals × A–I × boys & girls.
4. Carpal score→age curve — boys & girls.
5. TWII′20 points (its own 20-bone table) + curve — optional.
6. % predicted adult height (bone age → % attained) — optional.
7. Provenance (title, edition, ISBN, pages, licensed owner, entered_by, verified_by, date).
8. **2–3 of the clinic's OWN reference films** — sex, the 13 RUS stages, and the reported
   bone age. THIS is the validator.

Bone codes used by the product: RUS = radius, ulna, mc1, mc3, mc5, pp1, pp3, pp5, mp3, mp5,
dp1, dp3, dp5. Carpal = capitate, hamate, triquetral, lunate, scaphoid, trapezium, trapezoid.
Sexes = boys, girls. Stages = A..I.

## 5. ⚠️ CRITICAL — objective checks every candidate table MUST pass (apply these mechanically)

Six AI-reconstructed tables were tried; **all failed.** A new session must run these checks
and REJECT any table that fails — do not accept a confident "verified" label.

- **Sum-to-1000 invariant:** the maximum (stage-I, ulna stage-H) RUS points across the 13
  bones must sum to **exactly 1000** for boys AND girls. (Carpal max also sums to 1000.)
- **Monotonicity:** within each bone the points must be **non-decreasing** A→I (stage I ≥ H ≥ …).
  A later/more-mature stage cannot score lower.
- **Reference-case reconciliation:** for each reference case, the listed per-bone points must
  sum to the stated total, and that total must map to the stated age on the score→age curve.

**KEY LESSON: sum-to-1000 is NECESSARY, not SUFFICIENT.** An AI can *game* it by shaving a
cell to force the total — which is exactly what happened (it reduced DP5 by the exact overage,
creating an impossible girls-DP5 where stage I < stage H). Passing the sum proves nothing about
whether individual cells are correct.

**Definitive tell of fabrication:** the numbers CHANGED on every attempt. Radius stage-I went
213 → 106 → 213 → 201 across versions; a real published book has ONE value. That drift proves
the AI is *generating*, not *reading*.

## 6. The ONLY two valid paths to correct data

1. **Photos/scans of the actual licensed book pages** — values are *read*, not reconstructed.
   (The web AI admitted it has no physical book, so a chatbot cannot supply authoritative values.)
2. **Validate any candidate table against the clinic's REAL reference films** — real patients
   with a known reported bone age. If the points are wrong, real films won't reproduce →
   rejected. **AI-invented reference cases are circular** (they can't validate AI-invented points).

## 7. Honest ceiling (do not overclaim)

- Even if a reconstructed table reproduces 2–3 real films, it is **PROVISIONAL decision-support**
  (label it "AI-reconstructed, not authoritative TW3"; the clinician confirms every result), not a
  definitive TW3 bone age. 2–3 cases is a weak check; real validation needs many cases across the
  age range.
- Original TW3 is British-derived; for Indian children it needs local validation regardless.

## 8. Implementation plans already written (in the repo `plans/`)

- Plan 1 — licensed TW3 tables (loader, 4 gates, dual-transcription tool, checksum lock). **Built.**
- Plan 2 — human-gated self-learning flywheel (capture, consensus, adjudication, gated release). **Backend built.**
- Plan 3 — screening-model accuracy/calibration. Plan 4 — automatic per-bone AI (localizer+stager, needs GPU+data).
- Plan 5 — validation + release-gate infrastructure (evaluator, gates, report). **Built.**
- The scoring engine, 4 gates, dual-transcription, checksum lock, and 20-bone report are all
  implemented and green (200+ tests). What's missing is ONLY the lawful, correct table VALUES.

## 9. What the new session should do

1. Ask for **real book scans** OR the clinic's **real reference films** — nothing else validates.
2. Run any candidate table through §5's checks (sum-to-1000, monotonicity, case reconciliation).
   **Reject on any failure.**
3. If entering data: mark it PROVISIONAL, keep scoring gated on the real reference films, and never
   label reconstructed data as authoritative TW3.
4. Do NOT accept a chatbot-generated table as authoritative — six attempts have already failed.
