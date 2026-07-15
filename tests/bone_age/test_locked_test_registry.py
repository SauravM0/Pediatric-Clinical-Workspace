"""Frozen locked-test registry + cross-artifact leak guard (Plan 5 WI-1 / PLAN-0 C1).

The committed locked_test.json is the real RSNA validation set (1,425 held-out
images), checksum-locked and disjoint from the 12,611 training images. These tests
read the committed registry (no raw images needed) and prove the guard refuses any
leak and detects tampering.
"""
import pytest

from backend.ai.validation.leak_guard import (LeakError, RegistryError, assert_disjoint,
                                               build_from_dict, load_registry, save_registry)


def test_frozen_registry_loads_and_checksum_verifies():
    reg = load_registry()
    assert not reg.is_empty                       # the real locked test is carved
    assert reg.checksum_verified is True          # and tamper-locked
    assert reg.source == "internal-rsna"
    assert len(reg.patient_ids) == 1425
    assert len(reg.image_hashes) == 1425


def test_frozen_locked_test_is_disjoint_from_training_ids():
    reg = load_registry()
    # ids that belong to the TRAINING set must never appear in the locked test.
    assert_disjoint(reg, {"train": {"patient_ids": ["10000", "10001", "1377"]}})


def test_planted_overlap_refuses(tmp_path):
    reg = save_registry(["v1", "v2", "v3"], ["h1", "h2"],
                        dataset="d", source="s", path=tmp_path / "lt.json")
    assert_disjoint(reg, {"train": {"patient_ids": ["t1", "t2"]}})   # clean -> no raise
    with pytest.raises(LeakError):
        assert_disjoint(reg, {"train": {"patient_ids": ["t1", "v2"]}})       # patient leak
    with pytest.raises(LeakError):
        assert_disjoint(reg, {"calibration": {"image_hashes": ["h1"]}})      # hash leak


def test_checksum_tamper_is_detected():
    reg = load_registry()
    tampered = dict(reg.raw)
    tampered["patient_ids"] = list(tampered["patient_ids"]) + ["INJECTED"]
    with pytest.raises(RegistryError):
        build_from_dict(tampered)                 # altered content -> checksum mismatch
