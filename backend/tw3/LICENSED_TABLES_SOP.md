# Licensed TW3 Tables — Standard Operating Procedure (Plan 1 WI-9)

How a licensed clinician safely enters the copyrighted Tanner–Whitehouse point
tables and score→age curves so the software can compute a real, gated bone age.
Scoring stays **disabled** until every step passes — nothing is guessed, nothing
undocumented is trusted, and no post-verification edit is honoured.

**Legal:** enter values **only** from a reference your clinic legally owns. The TW3
point tables (Tanner, Healy, Goldstein & Cameron, 2001) are copyrighted and are not
bundled with this software.

---

## The four gates (all must pass for scoring to turn on)

`GET /api/bone-age/config` → `stage_systems["tw3-letters"].gates` shows each:

1. **any_calibrated** — every bone has point values and each score→age curve has ≥2 anchors.
2. **reference_cases_pass** — the clinic's own historically-reported films reproduce within tolerance.
3. **provenance_complete** — the six required source fields are filled.
4. **checksum_verified** — the table is checksum-locked and unaltered since verification.

`scoring_enabled` becomes `true` only when all four are green.

---

## Steps

1. **Record the licence first.** In the `provenance` block of the tables file, fill
   `book_title`, `edition`, `licensed_owner`, `entered_by`, `verified_by`,
   `verification_date` (ISBN/pages optional). No values are typed until this is done.

2. **Two independent transcriptions.** Transcriber A and Transcriber B each enter the
   full point tables + score→age curves into **separate** files, from the licensed
   book, without seeing each other's work. (Points: `rus_stage_to_score[sex][bone][letter]`
   and `carpal_stage_to_score`; curves: `rus_score_to_age[curve][sex]` and
   `carpal_score_to_age` as ascending `[score, ageYears]` anchors. TWII and TWIII are
   separate curves; RUS and carpal are always separate — never averaged.)

3. **Reconcile every cell.** Run:
   ```
   python -m backend.tw3.verify_transcription A.json B.json --out letters_tables.json
   ```
   Every mismatch prints its exact location and both values. Resolve each against the
   book and re-run until it reports `OK`. A clean run writes the merged,
   **checksum-locked** canonical file.

4. **Enter reference cases.** Add 2–3 of the clinic's own historically-reported films
   (their staging + the age that was clinically reported) under `reference_cases`. These
   are the ground truth the software must reproduce before it will score.

5. **Verify + lock.** Save through the app (the save path re-locks the checksum), or for a
   hand-edited file:
   ```
   python -m backend.tw3.letters_scoring --lock
   ```

6. **Gate check.** `GET /api/bone-age/config` (or `python -m backend.tw3.letters_scoring`)
   must show `scoring_ready: true` with all four gates green. If not, it names the failing
   gate. Only then does scoring activate and the report show real RUS + carpal ages.

7. **Re-verification on any change.** Any later edit to the file invalidates the checksum →
   scoring auto-disables and `/config` discloses the mismatch. Repeat steps 3–6 to re-enable.

---

## Decisions to confirm before step 2
- Which licensed **edition** (TW3 vs TW2) — this fixes the primary curve (`twiii` vs `twii`).
- **RUS-only or RUS + carpal** (carpal needs a licensed carpal table).
- **TWII′20** in or out (only if the licence covers the TW2 20-bone method).
- Which **reference films** serve as ground truth, and the tolerance (default ±0.3 yr).
