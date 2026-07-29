"""Regression guard: predicted adult height must stay separate from the
mid-parental genetic target (audit F-1).

The bone-age panel used to set the headline "Predicted Adult Height" to the
mid-parental height whenever both parents' heights were entered
(`pah = mph !== null ? mph : skeletalPah`). Those are different clinical
quantities: mid-parental height is the genetic TARGET (where the child is
expected to land given the parents); a prediction is a CHILD-SPECIFIC estimate
from the child's own skeletal maturity. Conflating them defeats the point of a
prediction, which is to detect deviation FROM the target channel.

Like the other frontend guards in this folder, this parses frontend/src/
as source (no browser/JS runtime needed) so a future edit that re-introduces the
conflation fails loudly.
"""
import re
from pathlib import Path

# M6: the app moved out of index.html into frontend/src/; _source locates it.
from _frontend_source import frontend_source


def _src() -> str:
    return frontend_source()


def test_prediction_is_not_conflated_with_mid_parental_target():
    src = _src()
    # The exact old conflation, tolerant of whitespace: pah = mph ? mph : skeletalPah
    conflation = re.search(
        r"\bpah\b\s*=\s*mph\s*!==\s*null\s*\?\s*mph\s*:\s*skeletalPah", src
    )
    assert conflation is None, (
        "frontend/src/ re-introduces the F-1 conflation: 'Predicted Adult "
        "Height' is being set to the mid-parental genetic target. Keep them "
        "separate (predictedPah = the child-specific skeletal estimate only)."
    )


def test_prediction_comes_only_from_the_skeletal_estimate():
    src = _src()
    assert re.search(r"const\s+predictedPah\s*=\s*skeletalPah\b", src), (
        "predictedPah must be the child-specific skeletal estimate only "
        "(null until the licensed %-attained table is calibrated), never the "
        "mid-parental target."
    )


def test_prediction_vs_target_difference_is_computed():
    src = _src()
    assert "predVsTarget" in src, (
        "The clinically useful comparison (skeletal prediction minus genetic "
        "target) must be computed and shown."
    )


def test_ui_labels_keep_target_and_prediction_distinct():
    src = _src()
    # The target must be badged as a target, and the gated prediction must state
    # it never borrows the target's value.
    assert "Genetic target — not a prediction" in src
    assert "never substituted here" in src


def test_target_channel_is_not_mislabelled_as_two_sd():
    src = _src()
    # +/-8.5 cm is a target RANGE, not literally +/-2 SD (that is ~ +/-10 cm).
    assert "target channel ±2 SD" not in src, (
        "The +/-8.5 cm mid-parental band must not be labelled '±2 SD'."
    )
