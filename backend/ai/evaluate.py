"""Validation metric evaluator for bone-age outputs (Plan 5 WI-2/WI-3).

Whole-hand skeletal-age metrics required by
``bone_age_product_starter_pack/validation_protocol.md`` §5, plus subgroup
stratification (§3 age bands) — the core of the release-gate evidence.

Design:
* **Pure + deterministic.** No I/O, no model calls, no randomness beyond a
  *seeded* bootstrap — so it is unit-testable on synthetic arrays without a GPU
  or a model file, and two runs on the same inputs give identical numbers.
* **Honest.** A passing INTERNAL metric here is NOT a clinical accuracy claim;
  external Indian validation is a separate, cohort-gated run (Plan 5 WI-8).
  Under-powered subgroups are labelled, never silently passed.

Units are months throughout (the app's internal bone-age unit).
"""
from __future__ import annotations

from typing import Iterable, Optional, Sequence

import numpy as np

# validation_protocol.md §5 agreement bands.
_WITHIN_BANDS_MONTHS = (3, 6, 9, 12)
# validation_protocol.md §3 age bands (years).
_AGE_BANDS = ((5.0, "0-5y"), (8.0, ">5-8y"), (12.0, ">8-12y"), (15.0, ">12-15y"))


def _as_arr(x) -> np.ndarray:
    return np.asarray(x, dtype=float).reshape(-1)


def age_band_years(age_years: Optional[float]) -> str:
    """Map a chronological/bone age (years) to a validation_protocol §3 band."""
    if age_years is None:
        return "unknown"
    a = float(age_years)
    for hi, label in _AGE_BANDS:
        if a <= hi:
            return label
    return ">15-18y"


def _bootstrap_mean_ci(values: np.ndarray, n_boot: int, seed: int,
                       alpha: float = 0.05) -> tuple[float, float]:
    """Seeded percentile bootstrap CI for the mean (deterministic)."""
    n = values.size
    if n < 2 or n_boot <= 0:
        m = float(values.mean()) if n else 0.0
        return m, m
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    means = values[idx].mean(axis=1)
    lo = float(np.percentile(means, 100 * alpha / 2))
    hi = float(np.percentile(means, 100 * (1 - alpha / 2)))
    return lo, hi


def _coverage(targets: np.ndarray, intervals: Sequence[Sequence[float]],
              target_coverage: Optional[float]) -> dict:
    lows = _as_arr([iv[0] for iv in intervals])
    highs = _as_arr([iv[1] for iv in intervals])
    if lows.size != targets.size:
        raise ValueError(f"intervals length {lows.size} != targets length {targets.size}")
    covered = (targets >= lows) & (targets <= highs)
    emp = float(covered.mean()) if targets.size else 0.0
    out = {"empirical": round(emp, 4), "n_covered": int(covered.sum()), "n": int(targets.size)}
    if target_coverage is not None:
        out["target"] = float(target_coverage)
        out["meets_target"] = bool(emp >= float(target_coverage))
    return out


def evaluate_age(
    preds: Iterable[float],
    targets: Iterable[float],
    *,
    intervals: Optional[Sequence[Sequence[float]]] = None,
    target_coverage: Optional[float] = None,
    abstained: Optional[Iterable[bool]] = None,
    bootstrap: int = 2000,
    seed: int = 12345,
) -> dict:
    """Whole-hand bone-age metrics (validation_protocol.md §5).

    ``preds`` / ``targets`` are predicted vs reference bone age in MONTHS.
    Optional ``intervals`` (per-case ``[lo, hi]`` in months) yields empirical
    coverage; ``target_coverage`` (e.g. 0.90) flags whether it is met. Optional
    ``abstained`` (bool per case) yields the abstention rate.

    Returns MAE, median AE, RMSE, signed bias + bootstrap 95% CI, Bland-Altman
    mean-diff + limits of agreement, and % within +/-3/6/9/12 months.
    """
    preds = _as_arr(preds)
    targets = _as_arr(targets)
    if preds.shape != targets.shape:
        raise ValueError(f"preds/targets shape mismatch: {preds.shape} vs {targets.shape}")
    n = int(preds.size)
    if n == 0:
        return {"n": 0, "insufficient": True}

    diff = preds - targets            # signed error (+ = model over-reads)
    abs_err = np.abs(diff)
    sd_diff = float(diff.std(ddof=1)) if n > 1 else 0.0
    signed_bias = float(diff.mean())
    ci_lo, ci_hi = _bootstrap_mean_ci(diff, bootstrap, seed)

    out = {
        "n": n,
        "mae_months": round(float(abs_err.mean()), 3),
        "median_ae_months": round(float(np.median(abs_err)), 3),
        "rmse_months": round(float(np.sqrt(np.mean(diff ** 2))), 3),
        "signed_bias_months": round(signed_bias, 3),
        "signed_bias_ci95_months": [round(ci_lo, 3), round(ci_hi, 3)],
        "bland_altman": {
            "mean_diff_months": round(signed_bias, 3),
            "sd_diff_months": round(sd_diff, 3),
            "loa_lower_months": round(signed_bias - 1.96 * sd_diff, 3),
            "loa_upper_months": round(signed_bias + 1.96 * sd_diff, 3),
        },
        "pct_within_months": {
            str(k): round(float(np.mean(abs_err <= k) * 100.0), 2) for k in _WITHIN_BANDS_MONTHS
        },
    }
    if intervals is not None:
        out["coverage"] = _coverage(targets, intervals, target_coverage)
    if abstained is not None:
        ab = np.asarray(list(abstained), dtype=bool)
        if ab.size != n:
            raise ValueError(f"abstained length {ab.size} != n {n}")
        out["abstention_rate"] = round(float(ab.mean()), 4)
    return out


def evaluate_by_subgroup(
    records: Iterable[dict],
    by: Sequence[str],
    *,
    min_n: int = 1,
    bootstrap: int = 2000,
    seed: int = 12345,
) -> dict:
    """Run ``evaluate_age`` overall and stratified by the fields in ``by``.

    ``records``: dicts with ``pred`` + ``target`` (months) and the subgroup keys
    in ``by`` (e.g. ``sex``, ``age_band``, ``image_domain``, ``site``,
    ``diagnosis``). Cells below ``min_n`` are returned as ``insufficient`` rather
    than scored -- an underpowered subgroup must never masquerade as a pass. The
    worst-MAE sufficient subgroup is flagged (the master audit's bias concern).
    """
    recs = list(records)
    overall = evaluate_age([r["pred"] for r in recs], [r["target"] for r in recs],
                           bootstrap=bootstrap, seed=seed)
    groups: dict[tuple, list] = {}
    for r in recs:
        key = tuple(str(r.get(k, "unspecified")) for k in by)
        groups.setdefault(key, []).append(r)

    cells: list[dict] = []
    worst: Optional[dict] = None
    for key, items in sorted(groups.items()):
        label = dict(zip(by, key))
        if len(items) < min_n:
            cells.append({"group": label, "n": len(items), "insufficient": True})
            continue
        m = evaluate_age([i["pred"] for i in items], [i["target"] for i in items],
                         bootstrap=bootstrap, seed=seed)
        cells.append({"group": label, **m})
        if worst is None or m["mae_months"] > worst["mae_months"]:
            worst = {"group": label, "mae_months": m["mae_months"]}
    return {"overall": overall, "subgroups": cells, "worst_subgroup": worst}


# ── per-bone staging metrics (Plan 5 WI-4; feeds the staging gates for Plan 4) ──

def quadratic_weighted_kappa(ref_idx: Sequence[int], pred_idx: Sequence[int],
                             k: int) -> Optional[float]:
    """Cohen's quadratic-weighted kappa over ``k`` ordered categories (0..k-1).

    Rewards near-misses less harshly than distant ones (A vs B costs less than A
    vs I) -- the right agreement measure for an ORDINAL stage scale. Returns None
    when there is nothing to score; 1.0 for perfect agreement; 0.0 at chance.
    """
    ref_idx = list(ref_idx)
    pred_idx = list(pred_idx)
    n = len(ref_idx)
    if n == 0 or k < 1:
        return None
    if k == 1:
        return 1.0  # only one possible category -> trivially perfect
    O = np.zeros((k, k), dtype=float)
    for r, p in zip(ref_idx, pred_idx):
        O[int(r), int(p)] += 1.0
    W = np.zeros((k, k), dtype=float)
    for i in range(k):
        for j in range(k):
            W[i, j] = ((i - j) ** 2) / ((k - 1) ** 2)
    row = O.sum(axis=1)
    col = O.sum(axis=0)
    E = np.outer(row, col) / n
    denom = float((W * E).sum())
    if denom == 0.0:
        # No expected disagreement (all mass in one category): agreement is perfect
        # iff there is no observed disagreement.
        return 1.0 if float((W * O).sum()) == 0.0 else 0.0
    return round(1.0 - float((W * O).sum()) / denom, 4)


def evaluate_staging(pred_stages: Sequence[str], ref_stages: Sequence[str],
                     stage_order: Sequence[str]) -> dict:
    """Per-bone staging metrics for ONE bone (validation_protocol.md §5).

    ``pred_stages`` / ``ref_stages`` are aligned stage labels (e.g. 'A'..'I');
    ``stage_order`` is the ordered vocabulary. Returns exact-stage accuracy,
    within-one accuracy, quadratic-weighted kappa, mean ordinal distance, a
    confusion matrix, and n. Labels outside ``stage_order`` are dropped (an
    unstageable bone contributes nothing rather than corrupting the metric).
    """
    order = list(stage_order)
    idx = {s: i for i, s in enumerate(order)}
    pairs = [(idx[p], idx[r]) for p, r in zip(pred_stages, ref_stages)
             if p in idx and r in idx]
    n = len(pairs)
    if n == 0:
        return {"n": 0, "insufficient": True}
    p_idx = [p for p, _ in pairs]
    r_idx = [r for _, r in pairs]
    dist = np.abs(np.array(p_idx) - np.array(r_idx))
    conf = np.zeros((len(order), len(order)), dtype=int)
    for p, r in pairs:
        conf[r, p] += 1
    return {
        "n": n,
        "exact_accuracy": round(float(np.mean(dist == 0)), 4),
        "within_one_accuracy": round(float(np.mean(dist <= 1)), 4),
        "weighted_kappa": quadratic_weighted_kappa(r_idx, p_idx, len(order)),
        "mean_ordinal_distance": round(float(dist.mean()), 4),
        "error_gt_one_rate": round(float(np.mean(dist > 1)), 4),
        "confusion": conf.tolist(),
        "stage_order": order,
    }


def evaluate_staging_per_bone(records: Iterable[dict], stage_order: Sequence[str],
                              *, min_n: int = 1) -> dict:
    """Aggregate per-bone staging metrics + the pooled/overall figures the gates
    need (validation_protocol.md §6).

    ``records``: dicts with ``bone_code``, ``pred`` (predicted stage) and ``ref``
    (reference/consensus stage). Carpals are evaluated per-bone like any other, so
    they can be gated separately. Returns per-bone metrics plus
    ``overall_weighted_kappa`` (pooled over all bones) and
    ``min_bone_weighted_kappa`` (worst sufficiently-sized bone) -- exactly the
    keys gates.evaluate_gates(staging=...) consumes.
    """
    recs = list(records)
    by_bone: dict[str, list[dict]] = {}
    for r in recs:
        by_bone.setdefault(str(r["bone_code"]), []).append(r)

    per_bone: dict[str, dict] = {}
    bone_kappas: list[float] = []
    exacts: list[float] = []
    for bone, items in sorted(by_bone.items()):
        m = evaluate_staging([i["pred"] for i in items], [i["ref"] for i in items], stage_order)
        per_bone[bone] = m
        if m.get("n", 0) >= min_n and isinstance(m.get("weighted_kappa"), (int, float)):
            bone_kappas.append(m["weighted_kappa"])
            exacts.append(m["exact_accuracy"])

    pooled = evaluate_staging([r["pred"] for r in recs], [r["ref"] for r in recs], stage_order)
    return {
        "n": pooled.get("n", 0),
        "overall_weighted_kappa": pooled.get("weighted_kappa"),
        "min_bone_weighted_kappa": (min(bone_kappas) if bone_kappas else None),
        "macro_exact_accuracy": (round(float(np.mean(exacts)), 4) if exacts else None),
        "per_bone": per_bone,
    }
