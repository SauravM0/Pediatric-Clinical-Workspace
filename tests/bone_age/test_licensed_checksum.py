"""Tamper-lock for the licensed original-TW3 letters table (Plan 1 WI-1).

A verified licensed clinical table must be immutable-by-detection, at parity with
the RUS table (backend/tw3/tables.py). These tests prove:
  * a save writes a matching checksum and reloads cleanly (checksum_verified);
  * a hand-edited value after verification is DETECTED -> load refuses -> scoring off;
  * a pure whitespace/formatting reformat does NOT trip the lock (canonicalisation);
  * the letters checksum is the SAME function as the RUS table's (parity).

Pure file I/O against a temp path -- no DB, no model, no server.
"""
import json
from pathlib import Path

import pytest

from backend.tw3 import compute_checksum as rus_compute_checksum
from backend.tw3.letters_scoring import (
    LetterTablesError,
    build_from_dict,
    load_letter_tables,
    save_letter_tables,
)

_MINIMAL = {"method": "TW3-letters", "version": "wi1-test", "source_reference": "unit"}


def _save(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "letters_tables.json"
    save_letter_tables(dict(data), p)
    return p


def test_save_writes_matching_checksum_and_reloads(tmp_path):
    p = _save(tmp_path, _MINIMAL)
    on_disk = json.loads(p.read_text(encoding="utf-8"))
    assert "checksum" in on_disk and on_disk["checksum"]
    t = load_letter_tables(p)
    assert t.checksum_verified is True


def test_hand_edited_value_is_detected(tmp_path):
    p = _save(tmp_path, _MINIMAL)
    doc = json.loads(p.read_text(encoding="utf-8"))
    # Tamper with content but keep the (now stale) checksum -> must be caught.
    doc["version"] = "tampered"
    p.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    with pytest.raises(LetterTablesError, match="checksum mismatch"):
        load_letter_tables(p)


def test_reformat_does_not_trip_the_lock(tmp_path):
    p = _save(tmp_path, _MINIMAL)
    doc = json.loads(p.read_text(encoding="utf-8"))
    # Rewrite with different indentation / key order but identical content.
    reordered = {k: doc[k] for k in sorted(doc)}
    p.write_text(json.dumps(reordered, indent=8), encoding="utf-8")
    t = load_letter_tables(p)  # canonicalisation ignores formatting -> still valid
    assert t.checksum_verified is True


def test_absent_checksum_is_not_an_error_but_not_verified(tmp_path):
    p = tmp_path / "letters_tables.json"
    p.write_text(json.dumps(_MINIMAL), encoding="utf-8")  # no checksum key
    t = load_letter_tables(p)
    assert t.checksum_verified is False  # uncalibrated template, loads fine


def test_checksum_is_parity_with_rus_table():
    # The letters lock uses the exact same canonical checksum as the RUS table.
    payload = {"method": "TW3-letters", "version": "v", "rus_stage_to_score": {"boys": {}}}
    saved = save_letter_tables(dict(payload), Path(__import__("tempfile").mkdtemp()) / "t.json")
    doc = saved.raw
    assert doc["checksum"] == rus_compute_checksum(doc)


def test_build_from_dict_verifies_inline_checksum():
    data = dict(_MINIMAL)
    data["checksum"] = compute_ok = rus_compute_checksum(data)
    t = build_from_dict(data)
    assert t.checksum_verified is True
    # flip one character of the checksum -> mismatch raises
    bad = dict(_MINIMAL)
    bad["checksum"] = ("0" if compute_ok[0] != "0" else "1") + compute_ok[1:]
    with pytest.raises(LetterTablesError, match="checksum mismatch"):
        build_from_dict(bad)
