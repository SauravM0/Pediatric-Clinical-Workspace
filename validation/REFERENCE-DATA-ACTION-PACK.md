# Reference data — action pack

**Date:** 19 September 2026 · **Status today: 1 of 7 references installed** (WHO LMS, 19 Sep 2026)
(live status in the app: Overview tab → "Reference data behind these numbers",
or `GET /api/reference-data`).

Every item below already has a built, tested, self-activating install path that
**refuses** to approximate. None of them can be finished by writing more code —
each needs a person to request, buy, download or transcribe. Ordered by value
per unit of effort.

| # | Reference | Action | Effort | Unlocks |
|---|---|---|---|---|
| 1 | IAP 2015 L,M,S | **Email** (below) | 10 min + wait | exact Indian centiles 5–18 y; fixes the interpolated 25th/75th lines |
| 2 | Indian height-velocity L,M,S | **Same email** | — | real velocity centiles; low-velocity rule becomes a centile test |
| 3 | WHO 2006/2007 LMS tables | ✅ **Done 19 Sep 2026** — downloaded, gate passed | — | WHO centiles from WHO's own files |
| 4 | AAP 2017 BP tables (Tables 4–5) | **Transcribe**, two people | ~2 h each | BP category for children under 13 |
| 5 | Khamis-Roche coefficients | **Transcribe**, two people (paper + 1995 erratum) | ~1 h each | adult-height prediction without an X-ray |
| 6 | TW3 book (3rd ed., 2001) | **Buy**, then transcribe | purchase + a day | real TW3 bone age; bone-age adult-height prediction |
| 7 | IAP CSV verification (GC-1) | **Read** the 2015 paper against the CSVs, two people | ~3 h | confirms/corrects the transcribed tables (known defect) |
| 8 | Local dual-read film cohort | Clinic process | months | the only valid Indian accuracy number for bone age |
| — | digiBONE | Downloaded 19 Sep; **cannot be evaluated** until the authors share their training preprocessing (question 3 in the email) | — | Indian-trained bone-age model |

---

## 1–2. One email to the Khadilkar group (IAP LMS + velocity)

**To:** Dr Vaman Khadilkar / Dr Anuradha Khadilkar, Hirabai Cowasji Jehangir
Medical Research Institute (HCJMRI), Pune. (Contact via the institute or the
corresponding-author address on the 2015 *Indian Pediatrics* paper.)

> **Subject:** Request for IAP 2015 growth-chart and 2019 height-velocity L, M, S values — clinical decision-support use
>
> Dear Dr Khadilkar,
>
> I run [clinic name], a paediatric practice in [city]. We use the revised IAP
> 2015 growth charts (Khadilkar et al., *Indian Pediatr* 2015;52:47-55) in a
> clinician-supervised, non-commercial decision-support tool that plots and
> scores children's growth, citing the IAP charts as the reference.
>
> The 2015 paper notes that the lambda, mu and sigma values and the LMS macro are
> available from the authors. Could you kindly share:
>
> 1. The **L, M and S values** underlying the IAP 2015 charts for **height, weight
>    and BMI**, boys and girls, **5.0–18.0 years** (at the 0.5-year steps or finer)
>    — the values also used in *Extended growth charts for Indian children*
>    (JPEM 2021).
> 2. The **L, M and S values** for the height-velocity percentiles in
>    *Height Velocity Percentiles in Indian Children Aged 5–17 Years*
>    (*Indian Pediatr* 2019;56:23-8), boys and girls. Two details would help us
>    apply them correctly: the measurement interval the velocities were computed
>    over, and whether each velocity is indexed at the **midpoint** of the interval
>    or at the second measurement.
>
> 3. We have also been evaluating **digiBONE** (github.com/goellab/digiBONE).
>    Could you share, or point us to, the exact **image preprocessing used in
>    training** the full-hand and segment models (cropping, contrast
>    normalisation, intensity scaling)? With the inference script as published
>    we cannot reproduce the RSNA-baseline models' training accuracy, so we cannot
>    yet evaluate the models fairly on our own films.
>
> Any format is fine (Excel, CSV or PDF). If possible, please give L and S to at
> least four decimal places. We will cite both papers wherever the values are
> used and will not redistribute them.
>
> With thanks and regards,
> [Name, qualifications, registration no.], [clinic, phone]

**When the files arrive** (save Excel as CSV first):

```bash
python -m backend.growth.ingest_iap_lms received_iap.csv            # report only
python -m backend.growth.ingest_iap_lms received_iap.csv --install --supplied-by "Dr V Khadilkar, HCJMRI" --received YYYY-MM-DD
python -m backend.growth.ingest_velocity_reference received_velocity.csv
python -m backend.growth.ingest_velocity_reference received_velocity.csv --install --supplied-by "Dr V Khadilkar, HCJMRI" --received YYYY-MM-DD
```

Details and what each gate checks: `backend/growth/data/IAP-LMS-REQUEST.md`,
`backend/growth/data/VELOCITY-REFERENCE-REQUEST.md`.

## 3. WHO LMS tables — DONE (19 September 2026)

Downloaded from WHO (12 expanded tables), converted without altering values,
installed, and the gate passed: 11,046 points against the previous engine, worst
deviation 0.006 units (tolerance 0.02); full chart validation passes. Provenance
with source URLs and the WHO licence note (CC BY-NC-SA 3.0 IGO — non-commercial)
is in `backend/growth/data/who_lms/PROVENANCE.json`.

Remaining, as a deliberate separate step: remove `rcpchgrowth` from
`requirements.txt` (it is the oracle the gate compares against, and
`who_reference.py` still imports it as the fallback) — see `WHO-LMS-REQUEST.md`.

## 4. AAP 2017 BP tables (transcribe)

Flynn et al., *Pediatrics* 2017;140(3):e20171904 — open access. Table 4 (boys),
Table 5 (girls), ages 1–12, seven height columns, the **cm** height row. Two
people fill two copies of `backend/vitals/data/aap2017_bp_tables.template.csv`
independently, then:

```bash
python -m backend.vitals.ingest_aap_bp first.csv --compare second.csv --install \
  --entered-by "Dr A" --verified-by "Dr B" --source "Flynn et al. Pediatrics 2017, Tables 4-5"
```

See `backend/vitals/AAP-BP-TABLES.md`.

## 5. Khamis-Roche (transcribe)

Khamis HJ, Roche AF. *Pediatrics* 1994;94(4):504-7 **and its 1995 erratum**.
Check the units (some printings are imperial). Two transcriptions, then
`python -m backend.clinical.ingest_khamis_roche first.csv --compare second.csv --install …`.
See `backend/clinical/KHAMIS-ROCHE-REQUEST.md`.

## 6. TW3 book (buy)

Tanner, Healy, Goldstein & Cameron, *Assessment of Skeletal Maturity and
Prediction of Adult Height (TW3 Method)*, 3rd ed., 2001, ISBN 0-7020-2511-9.
**Not** TW2, not the Greulich–Pyle atlas. Entry procedure, the four activation
gates, and the adult-height percentages: `backend/tw3/TW3-BOOK-REQUEST.md` and
`backend/tw3/LICENSED_TABLES_SOP.md`.

## 7. Verify the IAP CSVs against the paper (GC-1)

Four of seven height/weight columns in `backend/growth/data/*_IAP_5_18.csv` are
interpolated, not published (the 25th line is really the 26.5th). Two people
read the 2015 paper's tables into `iap_2015_published_reference.json`; the source
test then checks every cell. See `backend/growth/data/PROVENANCE.md`. Item 1
makes this largely moot for scoring, but the charts' drawn lines still need it.

## 8. Local dual-read cohort

200 of the clinic's own hand–wrist films, at least 15 per sex × pubertal stratum,
each read independently by two people. It is the only way to get a bone-age
accuracy figure that applies to Indian children. Tooling:
`python -m backend.ai.validation.carve_local_cohort`; report in the Bone Age tab.

## digiBONE — downloaded, not evaluable yet

Weights downloaded and verified 19 Sep 2026. Its published inference
preprocessing does not reproduce even the RSNA baseline's training accuracy, so
no fair number can be produced yet. Question 3 in the email asks the authors for
it. Details: `backend/ai/DIGIBONE.md`.
