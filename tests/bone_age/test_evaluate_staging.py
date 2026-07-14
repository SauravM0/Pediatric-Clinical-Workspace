"""Per-bone staging metrics (Plan 5 WI-4) — hand-verified.

Weighted-kappa expectations are hand-computed:
  * perfect agreement -> 1.0
  * chance-level 2x2 (ref [A,A,B,B], pred [A,B,A,B]) -> 0.0
"""
from backend.ai.evaluate import (
    evaluate_staging,
    evaluate_staging_per_bone,
    quadratic_weighted_kappa,
)

_ORDER = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]


def test_perfect_agreement():
    m = evaluate_staging(["A", "B", "C"], ["A", "B", "C"], _ORDER)
    assert m["exact_accuracy"] == 1.0
    assert m["within_one_accuracy"] == 1.0
    assert m["mean_ordinal_distance"] == 0.0
    assert m["weighted_kappa"] == 1.0


def test_within_one_and_ordinal_distance():
    # pred is one stage high on 2 of 3, two-off on none.
    m = evaluate_staging(["B", "C", "C"], ["A", "B", "C"], _ORDER)
    assert m["exact_accuracy"] == round(1 / 3, 4)      # only the 'C' matches
    assert m["within_one_accuracy"] == 1.0             # all within one
    assert m["mean_ordinal_distance"] == round(2 / 3, 4)
    assert m["error_gt_one_rate"] == 0.0


def test_kappa_chance_level_is_zero():
    k = quadratic_weighted_kappa([0, 0, 1, 1], [0, 1, 0, 1], 2)
    assert k == 0.0


def test_kappa_perfect_is_one():
    k = quadratic_weighted_kappa([0, 0, 1, 1], [0, 0, 1, 1], 2)
    assert k == 1.0


def test_confusion_matrix_shape_and_counts():
    m = evaluate_staging(["A", "A", "B"], ["A", "B", "B"], _ORDER)
    conf = m["confusion"]
    assert len(conf) == len(_ORDER) and len(conf[0]) == len(_ORDER)
    # ref A pred A =1 ; ref B pred A =1 ; ref B pred B =1
    assert conf[0][0] == 1        # ref A, pred A
    assert conf[1][0] == 1        # ref B, pred A
    assert conf[1][1] == 1        # ref B, pred B


def test_unstageable_labels_dropped():
    m = evaluate_staging(["A", "NOT_VISIBLE", "C"], ["A", "B", "C"], _ORDER)
    assert m["n"] == 2            # the NOT_VISIBLE pair is dropped


def test_empty_is_insufficient():
    assert evaluate_staging([], [], _ORDER).get("insufficient") is True


def test_per_bone_aggregation_and_gate_keys():
    records = [
        {"bone_code": "radius", "pred": "F", "ref": "F"},
        {"bone_code": "radius", "pred": "G", "ref": "G"},
        {"bone_code": "ulna", "pred": "A", "ref": "A"},
        {"bone_code": "ulna", "pred": "B", "ref": "C"},  # small miss
    ]
    out = evaluate_staging_per_bone(records, _ORDER)
    assert "radius" in out["per_bone"] and "ulna" in out["per_bone"]
    # keys the staging gates consume:
    assert "overall_weighted_kappa" in out
    assert "min_bone_weighted_kappa" in out
    assert out["n"] == 4
