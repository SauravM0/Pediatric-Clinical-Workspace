# Engineering Report — Architecture, Roadmap and Technical Specification

**Author role:** Principal Engineer review
**Date:** 26 July 2026
**Companions:** `GROWTH-AND-BONE-AGE-DIAGNOSIS-AND-ROADMAP-2026-07-26.md` (clinical diagnosis) · `PRODUCT-IMPROVEMENT-MASTER-PLAN-2026-07-26.md` (product plan)
**This document:** baseline architecture → milestone-by-milestone architectural critique → implementation specification
**Verification basis:** full source read, executed runtime probes, 243/244 tests green (1 skipped), hardware capability check

---

# Part 0 — Baseline: the architecture as it actually is

Establishing this precisely matters, because several milestones in the product plan are
cheap or expensive *entirely* as a function of these facts.

## 0.1 Layering

The codebase follows a clean four-layer separation, and it is consistently observed:

```
frontend/index.html          Presentation. Fetches JSON. Recomputes nothing clinical.
        │  HTTP
backend/api_*.py             Transport. Validation, serialization, HTTP status mapping.
        │  Python call, passes `db: Session`
backend/*_service.py         Orchestration + persistence. Lifecycle rules, audit, transactions.
        │  Python call, passes plain values
backend/{tw3,growth,cvd,ai}/ Domain. PURE: no DB, no HTTP, no filesystem (except own data files).
```

**The domain packages are genuinely pure.** `backend/growth/*` imports no SQLAlchemy and no
FastAPI. `backend/tw3/scoring.py` is deterministic and side-effect free. This is the single
most valuable architectural property in the repository and every milestone below is
constrained to preserve it.

## 0.2 Persistence and migration

| Property | Reality |
|---|---|
| Engine | SQLite, single file, `backend/data/tw3.db`, path overridable via `TW3_DB_PATH` |
| ORM | SQLAlchemy 2.0 declarative (`Mapped[...]`, `mapped_column`) |
| Migration tool | **None. No Alembic.** |
| New tables | Handled by `models.Base.metadata.create_all(engine)` — automatic |
| New columns | Hand-maintained `db._ADDED_COLUMNS: dict[table, dict[col, ddl]]`, applied by idempotent `ALTER TABLE ... ADD COLUMN` |
| FK enforcement | `PRAGMA foreign_keys=ON` via a `connect` event hook |
| Session | `get_db()` FastAPI dependency and `session_scope()` context manager; both commit-on-success / rollback-on-error |
| Init | `init_db()` called at **module import time** in `server.py:60` |

**Confirmed defect — schema version is write-once.** `models.ensure_schema_version()` inserts
a row only `if existing is None`, and never updates. I verified this at runtime: created a
DB at version `3`, bumped `config.DB_SCHEMA_VERSION` to `99`, re-ran `init_db()` — the table
still reports `3`.

```
after first init, schema_version rows: ['3']
after bumping DB_SCHEMA_VERSION to 99 and re-init: ['3']
VERDICT: STALE - version never updated
```

This matters more than it looks. `config.py`'s docstring states *"Versions are recorded on
every approved assessment so old results stay reproducible."* On any database that has ever
been initialised, `DB_SCHEMA_VERSION` is decorative. Every milestone that adds schema
inherits this bug. **Fix it in Phase 0 before adding anything.**

## 0.3 Established design patterns (to conform to, not reinvent)

1. **Service functions**: `fn(db: Session, *, kwarg, ..., actor: str = "local-user") -> ORM | dict`. Positional `db` first, everything else keyword-only.
2. **Audit**: every mutation calls `assessment_service._audit(...)` writing an `AuditEvent` with `previous`/`new` JSON and `application_version`.
3. **Domain exceptions** mapped at the API boundary: `AssessmentError`→409/422, `ScoringError`, `TablesError`, `ImagingError`.
4. **Immutability by revision**: approved records are locked; edits create a new revision via `supersedes_id`. Never mutate an approved clinical result.
5. **Reference-data contract** — the strongest pattern here, and the template for all new reference data:
   - values in CSV/JSON under a `data/` dir
   - `checksums.json` pinning parsed *numeric* content (format-insensitive)
   - a `PROVENANCE.md` naming the publication
   - a separate `*_published_reference.json` for independent human verification
   - a test that fails on drift (`test_iap_source.py`) and a `data_integrity.py` regenerator
6. **Gated model release**: candidate → `release_gate.py` (beat incumbent, no subgroup regression, calibration, engineering gates) → `ModelRelease` row → **human sign-off** → deploy.
7. **Withhold rather than guess**: uncalibrated tables yield `None` + an explicit status string, never a fabricated number.
8. **Frontend tests by static analysis**: `tests/frontend/*` regex-parse `index.html` to pin constants (e.g. `COMBINED_CHART_YMAX`). No browser, no JS runner.

## 0.4 Frontend architecture — the principal constraint

| Property | Reality | Consequence |
|---|---|---|
| Structure | **One 4,058-line `index.html`** | No module boundaries |
| Transpilation | **In-browser Babel** (`vendor/babel.min.js`, 3.1 MB) via `<script type="text/babel">` | Whole app re-transpiles on every page load |
| React | 18 UMD production build, vendored | No JSX tooling, no hooks lint |
| CSS | Tailwind **JIT in the browser** (451 KB) | Runtime class generation |
| Build step | **None** | No bundling, tree-shaking, code-splitting, or type checking |
| Offline | Fully vendored | Genuine strength — works with no network |

This is a deliberate, defensible choice for a single-file offline clinical tool, and it is
why the app runs with one command. **But it is the hard ceiling on Phases 3–6**, all of which
are UI-heavy. Adding a patient dashboard, a red-flag panel, and multi-specialty views to a
4,000-line file with no module system and in-browser transpilation is where this project
will bog down. Part II addresses this directly.

## 0.5 Runtime and hardware constraints (measured)

- `torch 2.12.1+cpu` — **no CUDA**. `onnxruntime 1.27.0`, providers `['AzureExecutionProvider', 'CPUExecutionProvider']`.
- Production inference path is **ONNX only**; `torch` is a dev/training dependency.
- Existing model was trained on Colab (`boneage-gp-mnv3s-ft-colab-2026-07-05`).
- Chart series build costs 2–3 s per `(measure, sex)`, memoised by `functools.lru_cache(maxsize=None)`.
- No authentication, no authorization, no encryption at rest.

## 0.6 Confirmed design smell blocking two milestones

The set of growth measures is declared **seven times in six files**, with no single source of truth:

```
backend/api_growth.py:17        _VALID_MEASURES = ("height", "weight", "bmi")
backend/api_growth.py:19        _UNITS = {...}
backend/growth/blend.py:74      _REQUIRE_MONOTONIC = {...}
backend/growth/qa_report.py:39  _MEASURE_FILE_PART = {...}
backend/growth/validation.py:51 MEASURES = ("height", "weight", "bmi")
backend/growth/who_reference.py:47  _MEASURE_MAP = {...}
backend/growth/who_reference.py:77  _SEAM_5Y = _Seam(measures=frozenset({...}))
```

Adding head circumference (B11) or sitting height (B14) requires a correct edit in all seven,
with **no compiler and no test that fails on a miss**. Contrast with `tw3/constants.py`, which
does this correctly for bones and stages. This is textbook shotgun surgery and it must be
fixed *before* the milestones that depend on it, not during.

---

# Part I — Baseline architectural and implementation roadmap

Seven milestones. Dependency-ordered.

```
M0 ─ Foundation Hardening ──┬─→ M1 Growth Reference Integrity
                            ├─→ M2 Longitudinal Clinical Record
                            │        │
M3 Bone Age Integrity ──────┼────────┤
                            │        ↓
                            └─→ M4 Inference Platform
                                     │
                                     ↓
                            M5 Clinical Reasoning Engine
                                     │
                                     ↓
                            M6 Presentation Re-platform ─→ multi-specialty
```

| ID | Milestone | Objective | Layer touched |
|---|---|---|---|
| **M0** | Foundation hardening | Fix schema versioning; centralise the measure registry; introduce a migration discipline | db, config, growth |
| **M1** | Growth reference integrity | Single authoritative LMS source; exact reproduction; correct tails | growth (domain) |
| **M2** | Longitudinal clinical record | Persist observations, puberty, encounters; velocity + conditional SDS | models, new service |
| **M3** | Bone age integrity | Truthful labelling; domain guards; licensed-table intake | tw3 (domain) |
| **M4** | Inference platform | Pluggable model registry; preprocessing pipeline; digiBONE via ONNX | ai, imaging |
| **M5** | Clinical reasoning engine | Rules engine for red flags, referral, prediction | new pure domain pkg |
| **M6** | Presentation re-platform | Module boundaries and a build step for the frontend | frontend |

---

# Part II — Critical evaluation of each milestone against the current codebase

This is where the baseline roadmap meets reality. For each milestone: what fits the
architecture, what fights it, and what has to change.

---

## M0 — Foundation Hardening

**Fits:** Small, surgical, entirely inside existing patterns.

**Fights:** Nothing. This is pure debt paydown.

### Critique

The migration story (`create_all` + `_ADDED_COLUMNS`) is **adequate but silently fragile**.
It works because every added column so far has been nullable or defaulted. It has three
failure modes that M2 will hit:

1. **No down-migration.** Irreversible by design. Acceptable for a local-first app; must be documented.
2. **No column type/constraint changes.** SQLite cannot `ALTER COLUMN`. Any future type change needs table rebuild — not currently possible.
3. **`_ADDED_COLUMNS` is not verified against the ORM.** If a developer adds a `mapped_column` to `Patient` and forgets `_ADDED_COLUMNS`, fresh DBs work and existing DBs raise `OperationalError: no such column` at query time — in production, not in tests (tests use a fresh temp DB).

**That third one is a live bug waiting for M2**, which adds seven columns to `Patient`.

**Verdict:** Do not adopt Alembic. It is disproportionate for a single-file local SQLite app
and would fight the "one command to run" property. Instead, close the gap with a **drift
test** (spec in Part III, §M0.2) that reflects over the ORM metadata, compares against a
freshly-created schema, and fails if any mapped column is absent from both. That gives you
Alembic's main safety property at ~40 lines and zero operational surface.

---

## M1 — Growth Reference Integrity

**Fits:** `backend/growth/` is pure, well-tested, and already has the reference-data contract.

**Fights:** Three specific couplings.

### Critique

**(a) The LMS swap is a larger blast radius than it looks.**

`iap_reference.py` currently maintains *three* parallel value paths — the LMS fit, the exact
`table_fns` PCHIP path, and `_z_from_display_anchors` inversion — plus `_EXACT_TABLE_GUARD`
to keep them from colliding at the seam. Obtaining real L,M,S collapses all three into one.
That is a large *simplification*, but it invalidates:

- `validation.check_source_reproduction()` — asserts the exact-table path reproduces the CSV to 1e-9
- `tests/growth/test_display_scoring_consistency.py` — asserts display and scoring agree, which is the *problem `_z_from_display_anchors` was invented to solve*; once LMS is exact this becomes trivially true
- `tests/growth/test_iap_source.py` — CSV-based; would need to target the LMS file instead
- `blend._quintic_bridge` — probes `iap_value_at_z` derivatives at `BLEND_HI ± 1/24y`; the guard band exists specifically so those probes stay LMS-based end-to-end. **Removing `_EXACT_TABLE_GUARD` without care re-introduces the seam inconsistency the guard was added to fix.**

**This is the single highest-regression-risk change in the whole plan.** It must be done as a
strangler: add the LMS path behind a flag, assert old ≈ new within tolerance across a dense
grid, *then* delete the old paths. Spec in Part III.

**(b) `lru_cache(maxsize=None)` makes reference data effectively immutable at runtime.**

`api_growth._cached_series` memoises per `(measure, sex, age_min, age_max, render_step)`. If
reference data becomes swappable (LMS file, velocity tables), a stale cache will serve
old curves indefinitely. Also unbounded: adding measures and age ranges multiplies entries.
Needs an explicit invalidation hook keyed on a reference-data fingerprint.

**(c) Adding measures is blocked by §0.6.** B11 (head circumference) and B14 (sitting height /
US:LS / arm span) cannot be done cleanly until the measure registry exists. **M0 must precede
M1's new measures**, not run in parallel.

**Verdict:** M1 is architecturally sound but must be sequenced M0 → registry → new measures,
and the LMS swap must be strangler-patterned with a numeric equivalence gate.

---

## M2 — Longitudinal Clinical Record

**Fits:** The service-layer pattern, audit helper, and revision-immutability model all
transfer directly.

**Fights:** One serious architectural hazard, and one genuine modelling decision.

### Critique

**(a) The purity hazard — do not let persistence leak into `backend/growth/`.**

The obvious implementation is to give `growth` functions a `db` handle so they can fetch a
patient's history for velocity. **This would destroy the most valuable property in the
codebase.** `backend/growth/*` currently imports no SQLAlchemy; it is deterministic,
trivially testable, and reusable.

The correct shape follows the existing `tw3` precedent exactly — `tw3/scoring.py` is pure and
`assessment_service.py` does all persistence:

```
backend/growth_service.py     NEW. DB access. Fetches observations, calls pure domain fns.
backend/growth/velocity.py    NEW. PURE. velocity(obs_pairs) -> cm/yr + SDS.
backend/growth/conditional.py NEW. PURE. conditional_sds(z1, z2, age1, age2) -> z.
```

Domain functions take **plain values** (lists of `(age_years, value)` tuples), never ORM
objects. Enforce with a test that asserts `backend.growth` never imports `sqlalchemy`.

**(b) Mutability model for observations — a real decision, not a default.**

The existing clinical record is immutable-by-revision. Should a height measurement be?

- Strict revisioning (like `TW3Assessment`) is over-engineered: a mistyped height is a typo, not a superseded clinical judgement.
- Free mutation loses the audit trail on clinical data.

**Recommendation:** soft-correction. Observations are append-only with a nullable
`corrected_by_id` self-FK and a `status` of `active | corrected | erroneous`. A correction
inserts a new row and marks the old one, mirroring `supersedes_id` on assessments without
the full lifecycle. Every write emits an `AuditEvent`. This is consistent with the codebase's
philosophy and cheap.

**(c) `Patient` gains seven columns → `_ADDED_COLUMNS` must be updated in the same commit.**
This is exactly the M0 drift-test failure mode. M0 first.

**(d) Velocity needs a new reference dataset** → must follow the §0.3 reference-data contract
(CSV + checksums + PROVENANCE.md + verification JSON + drift test). Do not shortcut it because
it is "just one more table."

**Verdict:** Architecturally clean *if* the purity boundary is enforced by test. The mutability
model needs an explicit decision, recorded.

---

## M3 — Bone Age Integrity

**Fits:** Extremely well. The gating machinery already exists and was built for exactly this.

**Fights:** Almost nothing — this is the best-prepared area of the codebase.

### Critique

`tables.py` already has: structural fail-fast validation, checksum verification, per-sex
`is_calibrated()`, `curve_validation` with reference cases, and `scoring.validate_curve()`
that clears a provisional flag only on local evidence. `letters_tables.json` is correctly
empty with blank `provenance` and scoring disabled.

**The infrastructure is ahead of the data. M3 is mostly a data-intake and labelling exercise,
not an engineering one.** Two genuine engineering items:

**(a) The clamp (C3) is a domain-layer fix, and the type signature already supports it.**
`scoring._interp_months` silently clamps out-of-domain scores to the endpoint. `ScoreResult`
already carries `bone_age_months: Optional[int]` plus a `status: str`, and the codebase's
"withhold rather than guess" pattern is established. So returning `None` with
`status="outside_curve_domain"` requires **no signature change and no API contract change** —
callers already handle `None`. This is a ~15-line fix. It is cheap because the architecture
was designed for it.

**(b) Per-bone stage constraints (C9) belong in the data file, not `constants.py`.**
`STAGES`/`LETTER_STAGES` are flat tuples; `tables._derive_allowed_stages()` already derives
per-bone allowed stages *from the data* for TW3-C. The letters path should use the identical
mechanism once licensed data exists — no new pattern needed.

**Verdict:** Lowest-risk, highest-integrity-return milestone. Do the two-day labelling and
clamp work immediately; it is nearly free and it is the difference between a defensible
research tool and a misleading one.

---

## M4 — Inference Platform

**Fits:** `ModelRelease`, `release_gate.py`, `conformal.py`, `suggestion_gate.py` are a real
MLOps spine — unusually mature for a project this size.

**Fights:** Four concrete integration problems that the plan document under-specified.

### Critique

**(a) digiBONE is PyTorch; production is ONNX-only.**

Adding `torch` to `requirements.txt` moves the deployable from ~200 MB to >2 GB and imports a
CUDA-less training framework into a clinical inference path. **Do not do this.** Convert
digiBONE to ONNX offline (Colab), commit only the `.onnx` + a metadata JSON matching the
existing `boneage_gp.json` shape, and keep `torch` in `requirements-dev.txt`. This preserves
the current deployment profile exactly.

**(b) The release gate assumes like-for-like comparison; digiBONE is not like-for-like.**

`release_gate.py` requires a candidate to *beat the incumbent*. But digiBONE is a different
**method** (segmental Greulich–Pyle, Indian-calibrated) versus the incumbent's whole-image
GP-on-RSNA. Comparing MAE on the locked RSNA test is valid and useful — but "beats incumbent
on RSNA" is the wrong acceptance criterion for a model whose value proposition is *Indian*
accuracy. The gate needs a `comparison_basis` concept: same-dataset comparisons gate on
delta; cross-method adoptions gate on absolute thresholds plus a documented rationale.
Otherwise you will either block a better model or weaken the gate to let it through.

**(c) Preprocessing changes silently invalidate the conformal calibration.**

`boneage_gp.json` stores `conformal.quantiles_months` computed on a specific val split with
specific preprocessing. Changing preprocessing (CLAHE, segmentation) changes the residual
distribution, so the stored quantiles no longer deliver their nominal coverage — and nothing
currently detects that. **The calibration must be keyed to a preprocessing version**, with a
startup assertion that the pipeline fingerprint matches the one the quantiles were computed
under. Empirical coverage is already measured (89.47% vs 0.90 target); make a mismatch fail
loudly rather than drift.

**(d) `imaging.py` normalisation is lossy before the model ever sees the image.**

`_normalise_to_uint8` does global min–max scaling, and `store_radiograph` caps the analysis
image at 1024 px. For whole-hand screening at 224 px this is fine. For **per-bone staging**
(M4's localizer/stager, C7/C14) it is not: a distal phalanx epiphysis occupies a small
fraction of the frame, and 1024 px throws away the detail that distinguishes adjacent stages.
Global min–max is also fragile — one bright annotation marker or collimator edge compresses
the entire diagnostic range.

Fix: percentile-based windowing (clip to 1st/99th percentile) instead of raw min/max, and a
separate higher-resolution derivative for per-bone crops. **Note this changes stored image
derivatives**, so it needs a derivative-version field and lazy regeneration.

**Verdict:** M4 is the highest-complexity milestone. The MLOps spine is sound; the four issues
above are integration details that will each cause a silent correctness failure if skipped.

---

## M5 — Clinical Reasoning Engine

**Fits:** Should be a new pure domain package — precisely the `tw3`/`growth` pattern.

**Fights:** The temptation to embed rules in the API or the frontend.

### Critique

Red flags, referral triage and adult-height prediction must be a **pure, deterministic,
independently testable domain package** — `backend/clinical/`. Inputs: a plain dataclass
snapshot. Outputs: a list of structured findings. No DB, no HTTP, no I/O.

The critical design property is **explainability as a data structure, not a string**. Each
rule must emit:

```python
@dataclass(frozen=True)
class Finding:
    rule_id: str            # "SHORT_STATURE_SEVERE"
    severity: str           # info | attention | urgent
    title: str
    rationale: str          # human-readable, includes the actual numbers
    inputs_used: dict       # {"height_sds": -3.2, "age_years": 7.4}
    source: str             # citation
    confidence: str
    suppressed_by: tuple[str, ...] = ()
```

`inputs_used` is what makes this auditable and testable — a rule that cannot state which
numbers it fired on cannot be clinically defended.

**Rule interaction is the real hazard.** Naive independent rules will double-count: a child
with height SDS −3.2 fires `SHORT_STATURE`, `SEVERE_SHORT_STATURE`, and
`BELOW_MID_PARENTAL_TARGET` simultaneously, producing three alarms for one problem. Alarm
fatigue is the documented failure mode of clinical decision support. Hence `suppressed_by`
and an explicit precedence pass.

**Second hazard: missing data must not read as normal.** If puberty staging is absent, the
"no breast development by 13" rule must return `insufficient_data`, never "no flag." The
`Optional`-and-explicit-status discipline already used in `ScoreResult` is the right precedent.

**Verdict:** Architecturally the cleanest new work in the plan, provided it stays pure and
treats explainability and suppression as first-class.

---

## M6 — Presentation Re-platform

**Fits:** Nothing. This is where the architecture actively fights the roadmap.

**Fights:** Everything in M2, M5 and multi-specialty is UI-bearing.

### Critique

M2 (patient dashboard, observation entry, history), M5 (findings panel) and Phase 6
(per-specialty views) together roughly double the frontend. The current vehicle is a
4,058-line single file with **in-browser Babel transpilation of the entire application on
every page load**.

Consequences already latent, which will become acute:

- Every load transpiles ~4,000 lines with a 3.1 MB Babel bundle. Doubling the app roughly doubles a cost paid on every open.
- No module system → no code splitting. A dentist using the orthodontic view downloads the entire endocrine app.
- No type checking, no hooks lint. In a clinical UI computing SDS thresholds, an undetected `undefined` renders as a plausible-looking blank.
- `tests/frontend/*` pin behaviour by **regex-parsing the HTML source**. That is a legitimately clever zero-dependency guard, and I would keep it for constants — but it cannot scale to test a dashboard's logic.

**The decision is a genuine trade-off, and the offline property is the thing to protect.**

- **Option A — stay monolithic.** Zero setup cost, keeps one-command run. Accept that the file reaches 8,000+ lines and testing stays static-analysis-only. Viable only if the UI stays roughly as it is.
- **Option B — precompiled single file** *(recommended)*. Introduce esbuild: author in `frontend/src/*.jsx`, build to one bundled `app.js`, commit the artefact. Preserves offline operation and the single-command run, **eliminates in-browser Babel entirely** (drop 3.1 MB), and enables modules, code splitting and real component tests. Cost: ~1 day setup, plus a build step contributors must run.
- **Option C — full SPA toolchain (Vite/TS).** Best engineering, highest ceremony, risks the offline-single-command property that makes this tool deployable in a low-connectivity clinic.

**Verdict:** Option B. Do it **before** M2's and M5's UI, not after. Retrofitting a build step
onto 8,000 lines of JSX is materially harder than onto 4,000, and every milestone in between
adds to the debt.

---

## Cross-cutting: security must gate deployment, not follow it

`server.py` binds `127.0.0.1` (good) but `render.yaml` and `Procfile` exist for public
deployment, `Patient.name` is plaintext, and there is no authentication anywhere. Today the
exposure is bounded because the app is stateless for growth and local for bone age. **M2
changes the risk class**: it creates a persistent longitudinal database of identified
children.

**Therefore M2 must not ship before authentication, encryption at rest, and a DPDP Act 2023
consent/retention posture.** This is a hard sequencing constraint, not a backlog item.

---

# Part III — Technical specification

Concrete specifications for each milestone. Anything marked **⚠️** is an edge case that will
cause a silent, wrong-but-plausible clinical output if unhandled.

---

## M0 — Foundation Hardening

### M0.1 · Fix schema versioning

`backend/models.py::ensure_schema_version` — change from insert-once to upsert-with-history:

```python
def ensure_schema_version(engine: Engine) -> None:
    """Record the current schema version, appending on change.

    Previously inserted only when the table was empty, so DB_SCHEMA_VERSION was
    never recorded again after first init -- verified stale at runtime. History is
    retained (one row per version) because reproducing an old result requires
    knowing which schema produced it, not just the current one.
    """
    from backend.db import SessionLocal

    with SessionLocal() as db:
        latest = db.execute(
            select(SchemaVersion).order_by(SchemaVersion.id.desc())
        ).scalars().first()
        if latest is None or latest.version != DB_SCHEMA_VERSION:
            db.add(SchemaVersion(version=DB_SCHEMA_VERSION))
            db.commit()
```

⚠️ **Do not** update the existing row — append. An approved assessment created under schema 3
must remain attributable to schema 3.

**Test:** `tests/test_schema_version.py` — init, bump constant, re-init, assert two rows in order.

### M0.2 · ORM ↔ `_ADDED_COLUMNS` drift test

`tests/test_migration_drift.py`:

```python
def test_every_mapped_column_is_creatable_or_migratable():
    """Guards the hand-maintained migration path.

    create_all() covers fresh DBs; _ADDED_COLUMNS covers existing ones. A column
    added to a model but not to _ADDED_COLUMNS works on a fresh DB (so tests pass)
    and raises OperationalError on a real one. This closes that gap.
    """
    from backend import models
    from backend.db import _ADDED_COLUMNS

    baseline = _V1_TABLE_COLUMNS   # frozen snapshot of the original schema
    for table_name, table in models.Base.metadata.tables.items():
        if table_name not in baseline:
            continue                        # wholly new table: create_all handles it
        for col in table.columns:
            if col.name in baseline[table_name]:
                continue
            assert col.name in _ADDED_COLUMNS.get(table_name, {}), (
                f"{table_name}.{col.name} is mapped but missing from _ADDED_COLUMNS; "
                "existing databases will fail at query time."
            )
```

⚠️ Any new column in `_ADDED_COLUMNS` must be **nullable or defaulted** — SQLite cannot add a
`NOT NULL` column without a default to a populated table. Assert this in the same test.

### M0.3 · Measure registry (unblocks B11, B14)

New `backend/growth/measures.py`, mirroring `tw3/constants.py`:

```python
@dataclass(frozen=True)
class Measure:
    key: str                    # "height"
    label: str                  # "Height"
    unit: str                   # "cm"
    rg_measurement_method: str | None   # rcpchgrowth constant, None if not WHO-backed
    monotonic: bool             # height/weight yes; BMI no (adiposity rebound)
    file_part: str              # "height_cm"
    age_min: float
    age_max: float
    who_seam_applies: bool

MEASURES: Final[dict[str, Measure]] = {...}
MEASURE_KEYS: Final[tuple[str, ...]] = tuple(MEASURES)
```

Then delete all seven duplicate declarations and derive from `MEASURES`. Add a test asserting
no module defines a literal measure tuple.

⚠️ `who_reference._SEAM_5Y` currently applies to all three measures; head circumference is
WHO-0-5y-only and has **no** 5y seam. Encode via `who_seam_applies`, not a hardcoded set.

⚠️ Sitting height and arm span have **no WHO reference at all** (`rg_measurement_method=None`)
— every WHO-touching code path must handle that without falling back to height.

### M0.4 · Cache invalidation

```python
def reference_fingerprint() -> str:
    """SHA-256 over every loaded reference data file + the pinned rcpchgrowth version."""

@lru_cache(maxsize=256)
def _cached_series(measure, sex, age_min, age_max, render_step, fingerprint): ...
```

Threading the fingerprint through as a cache-key argument makes stale curves structurally
impossible. Bound `maxsize` (currently `None`).

---

## M1 — Growth Reference Integrity

### M1.1 · LMS ingestion (strangler pattern — **mandatory**)

New file `backend/growth/data/iap_2015_lms.csv`:

```csv
sex,measure,age_years,L,M,S
boy,height,5.0,1.0000,109.2,0.04123
```

Full reference-data contract applies: add to `checksums.json`, document in `PROVENANCE.md`,
record the donating authority and date.

**Migration sequence — do not compress these steps:**

1. Add `iap_lms_reference.py` alongside the existing `iap_reference.py`. Do not modify the latter.
2. Add `GROWTH_LMS_ENABLED` (env-gated, default off).
3. Add an **equivalence gate** test:

```python
def test_lms_path_matches_published_table_exactly():
    for sex, measure, age, centile in _all_published_cells():   # 1,134 cells
        assert abs(lms_value(...) - published) < 1e-6

def test_lms_path_agrees_with_legacy_within_tolerance():
    """Dense grid, 0.1y steps, z in [-3, +3]. Legacy is an approximation, so this
    is a sanity band, not equality -- large divergence means a transcription error
    in the new LMS file, not merely the expected fit error."""
    assert max_abs_diff < TOL[measure]
```

4. Only once both pass, flip the default, delete `_z_from_display_anchors`, `table_fns`, `_EXACT_TABLE_GUARD`, and the L/S smoothing branch.

⚠️ **`blend._quintic_bridge` probes `iap_value_at_z` at `BLEND_HI ± 1/24y` and
`validation.py` probes further still.** With true LMS, value/slope/curvature come from one
continuous function, so `_EXACT_TABLE_GUARD` becomes unnecessary — but its removal must be
verified by re-running `validation.run_full_validation()`, which is the check that caught the
original seam inconsistency.

⚠️ LMS at ages between published knots requires interpolating **L, M and S separately**, then
applying Cole. Interpolating the resulting *values* instead is subtly wrong for skewed
distributions. Use `PchipInterpolator` per parameter, matching the existing convention.

⚠️ `L` may cross zero. Cole's formula degenerates at `L = 0` and must use the log form:
`X = M·exp(S·z)`. `lms_core.py` delegates to rcpchgrowth which handles this; a hand-rolled
replacement (M1.4) must too. Add an explicit `L≈0` test case.

### M1.2 · Tail correction (ship even if LMS never arrives)

In `iap_reference.iap_z_for_value`, replace unbounded linear extrapolation:

```python
_Z_REPORTABLE_MIN, _Z_REPORTABLE_MAX = -5.0, 5.0

# Beyond the outermost drawn centile, fall back to the LMS inverse rather than
# extrapolating the centile ladder linearly: the ladder is linear in VALUE, but
# weight/BMI are strongly right-skewed, so linear extrapolation compresses the
# lower tail toward the mean. Measured: a true -3.0 SD weight scored -2.6 SD,
# i.e. a child meeting the WHO severe threshold reported just above it.
```

⚠️ Clamp reported z to ±5 and set an `out_of_range` flag rather than returning `-12.9` for a
40 cm six-year-old. The API response should carry the flag so the UI can show "outside
reference range" instead of a confident number.

⚠️ The frontend has a **twin implementation**, `zForValueFromCentileStats` (`index.html:459`).
Fixing only the backend leaves the bug live in the adult-height projection path, which uses
the frontend function. Both must change, and `tests/frontend/` should pin the corrected
behaviour by static analysis.

### M1.3 · Velocity (depends on M2)

`backend/growth/velocity.py` — **pure**:

```python
def height_velocity(a1: float, v1: float, a2: float, v2: float) -> VelocityResult:
    """cm/year between two measurements. Pure; no DB.

    Interval rules (clinical, not arbitrary):
      < 0.5y  -> refuse. Measurement error (~0.3cm SD) dominates: over 3 months a
                 0.5cm error becomes 2 cm/yr of spurious velocity.
      0.5-1.5y-> accept.
      > 2.0y  -> accept but flag: a spurt inside the window is averaged away.
    """
```

⚠️ Velocity centiles are **interval-specific**. Khadilkar's reference is annual; a 6-month
interval annualised is not distributed identically. Store the actual interval and either
restrict SDS to 0.75–1.25y intervals or apply the published interval correction. Do not
silently annualise and compare against annual centiles.

⚠️ Height *can* legitimately decrease slightly (diurnal variation, measurement technique,
scoliosis progression). Do not reject negative velocity outright — flag it.

### M1.4 · Drop `rcpchgrowth` (AGPL)

Vendor WHO 2006/2007 LMS as CSVs under the reference-data contract; implement Cole in
`lms_core.py` (~30 lines including the `L≈0` log branch).

⚠️ `tests/growth/test_dependency_pin.py` asserts the pin — update it to assert *absence*.
⚠️ Removing rcpchgrowth also removes `_BOUNDARY_NUDGES_YEARS`, the workaround for its
internal 1.999–2.0014y dead zone. Verify the 2.0y seam behaviour is preserved by the existing
regression tests before deleting the nudge logic.

---

## M2 — Longitudinal Clinical Record

### M2.1 · Schema

```python
class Observation(Base):
    __tablename__ = "observation"
    __table_args__ = (
        Index("ix_observation_patient_type_date", "patient_id", "obs_type", "observed_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), nullable=False)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounter.id"), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    age_months: Mapped[float | None] = mapped_column(Float, nullable=True)  # derived, cached
    obs_type: Mapped[str] = mapped_column(String(24), nullable=False)   # measures.MEASURE_KEYS
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(12), nullable=False)
    method: Mapped[str | None] = mapped_column(String(32), nullable=True)  # stadiometer|infantometer|...
    measured_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="active", nullable=False)
    corrected_by_id: Mapped[int | None] = mapped_column(ForeignKey("observation.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
```

⚠️ **Store `observed_at`, derive `age_months`.** If DOB is later corrected, ages must
recompute. Caching `age_months` is a performance convenience — add a service function to
recompute all of a patient's observations on DOB change, and call it from the patient-update
path. Failing to do this silently corrupts every historical z-score.

⚠️ `value` must be validated against `obs_type` at the service layer: a height of 15 (metres?
inches?) must be rejected. Range-check per measure against the reference domain ± generous margin.

`Patient` additions (**all nullable → all must go into `_ADDED_COLUMNS`**):
`mother_height_cm`, `father_height_cm`, `gestational_age_weeks`, `birth_weight_g`,
`birth_length_cm`, `ethnicity`, `conditions_json`, `medications_json`.

⚠️ Parental heights are frequently *self-reported* and biased upward. Store a
`parental_height_source` (`measured | reported`) — mid-parental target height is only as good
as its inputs, and reporting a target as if measured overstates precision.

### M2.2 · Service layer

New `backend/growth_service.py`, following `assessment_service.py` conventions exactly:

```python
def record_observation(db: Session, *, patient_id: int, obs_type: str, value: float,
                       observed_at: datetime, unit: str | None = None,
                       method: str | None = None, encounter_id: int | None = None,
                       actor: str = "local-user") -> Observation: ...

def correct_observation(db: Session, observation_id: int, *, new_value: float,
                        reason: str, actor: str = "local-user") -> Observation:
    """Append a corrected row, mark the original 'corrected'. Never mutates in place."""

def series_for(db: Session, patient_id: int, obs_type: str) -> list[tuple[float, float]]:
    """(age_years, value) pairs, status='active', ascending. PLAIN VALUES ONLY --
    this is the boundary; backend.growth must never receive an ORM object."""
```

⚠️ **Purity enforcement test:**

```python
def test_growth_domain_has_no_persistence_dependency():
    """backend/growth is pure by contract (like backend/tw3). Velocity work makes it
    tempting to pass a Session in; that would end its testability and reusability."""
    for path in (Path("backend/growth")).rglob("*.py"):
        src = path.read_text()
        assert "sqlalchemy" not in src and "from backend.models" not in src, path
```

### M2.3 · Duplicate and implausibility guards

⚠️ Same `(patient_id, obs_type)` on the same calendar day → warn, do not block (legitimate
re-measurement). Return `duplicate_of`, mirroring `radiograph_service.attach_image`.

⚠️ Height decreasing by >1 cm between visits → flag `implausible_decrease`. Requires clinician
confirmation before storing. This is the single most common data-entry error in growth clinics
and it silently destroys velocity.

⚠️ Two observations <30 days apart → exclude from velocity by default.

---

## M3 — Bone Age Integrity

### M3.1 · Curve domain guard

`backend/tw3/scoring.py`:

```python
_CURVE_EXTRAPOLATION_TOLERANCE = 0.0   # explicit: no extrapolation

def _interp_months(anchors, score) -> tuple[Optional[int], str]:
    """Returns (months, status). Out-of-domain returns (None, reason) rather than
    silently clamping to an endpoint.

    The digitized TW3-C curve spans score 150-1000 (boys) / 270-1000 (girls). Below
    the first anchor the old clamp returned exactly 6.00y for ANY score -- 50, 100
    and 150 were indistinguishable in the output, with nothing marking the answer
    as a clamp rather than a computation.
    """
    if score < pts[0][0]:
        return None, f"score {score:.0f} below curve domain (min {pts[0][0]:.0f})"
    if score > pts[-1][0]:
        return None, f"score {score:.0f} above curve domain (max {pts[-1][0]:.0f})"
```

⚠️ `ScoreResult.bone_age_months` is already `Optional[int]` and callers already branch on
`None` — **no API contract change**. Verify `report.py` and `api_bone_age.py` render the new
status instead of an empty cell.

⚠️ Score exactly equal to an endpoint is in-domain (`<`, not `<=`).

⚠️ A maximum-grade assessment legitimately totals exactly 1000 — must not be rejected.

### M3.2 · Method labelling

Single source in `tw3/constants.py`:

```python
METHOD_DISPLAY_NAME: Final[str] = "TW3-C (Chinese) RUS — provisional"
METHOD_QUALIFIER: Final[str] = (
    "Provisional research curve (±0.5y, digitized from a published figure). "
    "Not Tanner-Whitehouse TW3."
)
```

Surface in: `api_bone_age` responses, `tw3/report.py`, the growth PDF, and the frontend.
Add a static-analysis frontend test asserting the qualifier string is present — matching the
existing `tests/frontend/` convention.

---

## M4 — Inference Platform

### M4.1 · Model registry

Generalise the single-model assumption:

```python
@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    kind: str                 # screening | localizer | stager
    method: str               # greulich-pyle | tw3-rus
    onnx_path: Path
    input_size: int
    preprocessing_version: str      # <-- binds calibration to pipeline
    conformal_quantiles: dict[str, float]
    population: str                 # "RSNA-US" | "Indian-HCJMRI" | "mixed"
    metrics: dict
```

⚠️ **`preprocessing_version` is the critical field.** Assert at load time that the active
pipeline's fingerprint equals the model's, and refuse to serve conformal intervals on
mismatch. Otherwise a preprocessing change silently degrades interval coverage with no signal.

### M4.2 · Preprocessing pipeline

New `backend/ai/preprocess.py`, versioned:

```python
PREPROCESSING_VERSION = "prep-2.0-clahe-seg"

def preprocess(arr: np.ndarray, *, target: int) -> np.ndarray:
    """1. Percentile window (1st/99th) -- NOT global min/max.
       2. CLAHE (clipLimit=2.0, tileGrid=8x8).
       3. Hand segmentation -> largest connected component -> background to 0.
       4. Rotation normalisation via principal axis.
       5. Pad to square (preserve aspect), resize to `target`.
    """
```

⚠️ Global min–max (`imaging._normalise_to_uint8`) is destroyed by one bright annotation
marker or collimator edge — a single saturated pixel compresses the whole diagnostic range.
Percentile windowing is robust to both.

⚠️ **Do not change `imaging._normalise_to_uint8` itself.** It feeds `store_radiograph`, and
stored derivatives are referenced by existing `Radiograph` rows. Add preprocessing as a
separate inference-time step; if stored derivatives must change, add
`Radiograph.derivative_version` and regenerate lazily.

⚠️ Segmentation must **fail open**: if no plausible hand component is found, fall back to the
unsegmented image and add a quality flag. A segmentation bug must not silently feed a black
image to the model and produce a confident wrong age.

⚠️ CLAHE on an already-processed film photo can amplify JPEG blocking. Gate by
`Radiograph.source_domain` (`film_photo`/`compressed` already exist in `IMAGE_DOMAINS`).

### M4.3 · digiBONE integration

1. Convert to ONNX offline (Colab) at opset 17; verify parity (max abs diff < 1e-4) against PyTorch on ≥100 images.
2. Commit `.onnx` + `ModelSpec` JSON. **`torch` stays in `requirements-dev.txt`.**
3. Evaluate on the existing locked RSNA test via `evaluate.py` — unchanged harness, directly comparable to the 8.99 mo baseline.
4. Re-run `calibrate_conformal.py` on the same calibration split with the new pipeline.
5. Route through `release_gate.py` with a new `comparison_basis` field (see M4.4).

⚠️ digiBONE outputs **Greulich–Pyle** age. The `BoneAgeFeedback.method` enum already
distinguishes `greulich-pyle` from `tw3-rus` — keep them separate in monitoring, and never
average across methods.

⚠️ Verify the licence file ships with the artefact; MIT requires attribution.

### M4.4 · Release-gate extension

```python
comparison_basis: str   # "same-method-same-dataset" | "cross-method-adoption"
```

- `same-method-same-dataset` → existing behaviour (beat incumbent, no subgroup regression).
- `cross-method-adoption` → gate on **absolute** thresholds from `gates.json` plus a mandatory
  written rationale and human sign-off. Never auto-deploy.

⚠️ Do not weaken the existing gate to admit digiBONE. Add the new basis explicitly; a
loosened gate is a permanent loss of a safety property.

---

## M5 — Clinical Reasoning Engine

### M5.1 · Package shape

```
backend/clinical/
    __init__.py
    snapshot.py     PatientSnapshot dataclass -- the ONLY input
    rules.py        Rule registry
    growth_rules.py
    puberty_rules.py
    referral.py     Findings -> triage level + specialty
    prediction.py   Khamis-Roche
```

Pure. No DB, no HTTP. Same purity test as M2.2.

### M5.2 · Rule contract

```python
class Rule(Protocol):
    rule_id: str
    requires: tuple[str, ...]      # snapshot fields that must be non-None
    def evaluate(self, s: PatientSnapshot) -> Finding | None: ...
```

⚠️ **Missing data must never read as normal.** The engine checks `requires` first; unmet →
emit an `insufficient_data` finding naming the missing input. A silent absence of a flag is
indistinguishable from "checked and fine," which is the most dangerous failure mode in
decision support.

⚠️ **Suppression is mandatory.** `SEVERE_SHORT_STATURE` suppresses `SHORT_STATURE`. Without
a precedence pass, one clinical problem produces three alarms and clinicians learn to ignore
the panel.

⚠️ **Thresholds are data, not code.** Put them in `clinical/thresholds.json` under the
reference-data contract, each with its citation. A threshold change is then a reviewed,
checksummed, logged event — consistent with how `gates.json` is already handled.

### M5.3 · Khamis–Roche

⚠️ Validated **4.0–17.5 years only** — outside that, return `None` with a reason. Do not
extrapolate.
⚠️ Requires *measured* parental heights; degrade confidence explicitly when self-reported.
⚠️ Publish the ±5.3 cm 90% interval **with every prediction**. A point estimate alone will be
read as precise.
⚠️ Never present alongside mid-parental target height without distinct labels — this
mislabelling is already an open audit finding.

### M5.4 · Referral triage

Three levels only: `routine_monitoring` | `discuss_with_paediatrician` | `specialist_soon`.

⚠️ **No "minor"/"benign"/"normal" output path may exist in the code.** Enforce with a test
asserting the triage enum contains no reassuring terminal state. Anthropometry can indicate
that something needs review; it cannot rule out serious disease.

⚠️ Patient-facing output must be behind a clinician-release flag, default off.

---

## M6 — Presentation Re-platform (Option B)

```
frontend/
  src/            *.jsx modules, authored
  vendor/         react, react-dom (KEEP)   babel.min.js (DELETE after cutover)
  app.js          built artefact, COMMITTED
  index.html      thin shell
build.mjs         esbuild, ~20 lines
```

⚠️ **Commit the built artefact.** Offline, one-command operation is a real product property
for low-connectivity clinics — do not trade it for build purity.

⚠️ Add a CI check that `app.js` matches a fresh build of `src/`, or the committed artefact
will silently drift from source.

⚠️ Migrate incrementally: extract components one at a time, keeping the app runnable at every
commit. Do not attempt a big-bang rewrite of 4,058 lines.

⚠️ `tests/frontend/*` regex-parse `index.html`. After extraction those constants live in
`src/*.jsx` — update the paths in the same commit or the guards silently pass against a file
that no longer contains the logic. **A regex test that no longer matches anything is a test
that always passes.**

---

## Revised sequencing (architecture-constrained)

The product plan's ordering changes once architecture is accounted for:

| Order | Milestone | Why here |
|---|---|---|
| 1 | **M0** Foundation | Schema-version bug and measure registry block everything downstream |
| 2 | **M3.1/M3.2** Bone age labelling + clamp | ~2 days, near-zero risk, removes the largest overstatement |
| 3 | **M1.2** Tail correction | Independent of the LMS request; fixes a live misclassification |
| 4 | **M6** Build step | Must precede the UI-heavy milestones, not follow them |
| 5 | **Security** auth + encryption + DPDP | Hard gate before persisting identified children |
| 6 | **M2** Longitudinal record | Unblocks velocity, conditional SDS, reasoning |
| 7 | **M1.1/M1.3** LMS swap + velocity | LMS arrives on an external timeline; velocity needs M2 |
| 8 | **M4** Inference platform | Highest complexity; benefits from M0's discipline |
| 9 | **M5** Reasoning engine | Needs M2 data and M1 correct references |
| 10 | **Multi-specialty** | Only after M1 and M4 are accurate |

**Two changes from the product plan, both architecturally forced:**

- **M6 (build step) moves earlier.** Retrofitting a build onto 8,000 lines is materially harder than onto 4,000, and M2/M5 will add most of those lines.
- **Security moves before M2**, because M2 is the milestone that creates a persistent identified-patient database. Today's risk profile is bounded by statelessness; M2 removes that bound.

---

## Definition of done (per milestone)

| Milestone | Objective, measurable exit criteria |
|---|---|
| M0 | Schema-version test passes; drift test passes; zero duplicate measure declarations; 243 tests still green |
| M1 | All 1,134 published cells reproduce to <1e-6; z round-trips to 1e-9 over ±3 SD; no unbounded extrapolation; `run_full_validation()` all-pass |
| M2 | 3 visits persist and plot; DOB correction recomputes all ages; purity test passes; implausible-decrease guard fires |
| M3 | No surface renders plain "TW3"; out-of-domain scores return `None` + status; `validate_curve()` wired to the release path |
| M4 | Locked-test MAE < 6.0 mo (own gate); conformal empirical coverage within ±1% of nominal; preprocessing fingerprint asserted at load |
| M5 | Every finding carries `inputs_used` + citation; suppression verified; no reassuring terminal triage state exists in the enum |
| M6 | `babel.min.js` removed; committed artefact matches a fresh build; frontend tests re-pointed and genuinely matching |

---

## Closing engineering judgement

Three observations that should shape how this work is approached.

**The architecture is better than the data, and better than the UI.** The layering is clean,
the domain packages are genuinely pure, the reference-data contract (checksums + provenance +
independent verification + drift tests) is stronger than most commercial medical software,
and the MLOps spine (gated release, conformal calibration, adjudication, leak-guarded locked
test) is unusually mature. The correct strategy is therefore **conform to the existing
patterns rather than introduce new ones** — nearly every milestone above has a precedent
already in the codebase to copy.

**The cheapest high-value work is disproportionately cheap because of that architecture.**
The bone-age clamp fix is ~15 lines with no contract change, purely because `Optional` +
explicit status was already the established idiom. The same fix in a codebase that returned
bare floats would be a breaking API change. Good structure is already paying out here.

**The two real architectural risks are the frontend and the LMS swap.** The frontend is a
capacity problem that compounds with every UI milestone — address it before M2, not after.
The LMS swap is a regression problem: it deletes three interlocking mechanisms
(`_z_from_display_anchors`, `table_fns`, `_EXACT_TABLE_GUARD`) that exist specifically to
compensate for the missing data, and those mechanisms are load-bearing for the WHO/IAP seam.
Strangler pattern with a numeric equivalence gate is not optional there.

Everything else is execution.
