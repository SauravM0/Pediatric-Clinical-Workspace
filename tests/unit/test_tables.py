"""TW3 tables loader / integrity tests (directive §10, §24)."""

from __future__ import annotations

import json

import pytest

from backend.tw3 import compute_checksum, load_tables
from backend.tw3.tables import TablesError, _TABLES_PATH, load_tables as load_path


def test_production_tables_load() -> None:
    t = load_tables()
    assert t.method
    assert t.version  # version is mandatory (§24)
    assert set(t.score_to_age).issubset({"boys", "girls"})


def test_missing_version_fails(tmp_path) -> None:
    bad = tmp_path / "t.json"
    bad.write_text(json.dumps({"method": "TW3-RUS"}), encoding="utf-8")
    with pytest.raises(TablesError):
        load_path(bad)


def test_unknown_bone_fails(tmp_path) -> None:
    bad = tmp_path / "t.json"
    bad.write_text(json.dumps({
        "method": "TW3-RUS", "version": "1",
        "stage_to_score": {"girls": {"not_a_bone": {"G": 10}}},
    }), encoding="utf-8")
    with pytest.raises(TablesError):
        load_path(bad)


def test_non_numeric_score_fails(tmp_path) -> None:
    bad = tmp_path / "t.json"
    bad.write_text(json.dumps({
        "method": "TW3-RUS", "version": "1",
        "stage_to_score": {"girls": {"radius": {"G": "ten"}}},
    }), encoding="utf-8")
    with pytest.raises(TablesError):
        load_path(bad)


def test_checksum_mismatch_fails(tmp_path) -> None:
    bad = tmp_path / "t.json"
    bad.write_text(json.dumps({
        "method": "TW3-RUS", "version": "1", "checksum": "deadbeef",
        "stage_to_score": {"girls": {"radius": {"G": 10}}},
        "score_to_age": {"girls": [[10, 5.0], [20, 6.0]]},
    }), encoding="utf-8")
    with pytest.raises(TablesError):
        load_path(bad)


def test_checksum_roundtrip(tmp_path) -> None:
    content = {
        "method": "TW3-RUS", "version": "1",
        "stage_to_score": {"girls": {"radius": {"G": 10}}},
        "score_to_age": {"girls": [[10, 5.0], [20, 6.0]]},
    }
    content["checksum"] = compute_checksum(content)
    good = tmp_path / "t.json"
    good.write_text(json.dumps(content), encoding="utf-8")
    t = load_path(good)
    assert t.checksum_verified is True
