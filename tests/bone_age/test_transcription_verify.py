"""Dual-transcription reconciliation tool (Plan 1 WI-2)."""
import json

from backend.tw3.verify_transcription import diff_tables, main, reconcile


def _tbl(radius_h=8.0, with_curve=True):
    t = {
        "method": "TW3-letters", "version": "t",
        "rus_stage_to_score": {"girls": {"radius": {"G": 7.0, "H": radius_h}}},
    }
    if with_curve:
        t["rus_score_to_age"] = {"twiii": {"girls": [[13, 5.0], [117, 15.0]]}}
    return t


def test_identical_transcriptions_have_no_diff():
    assert diff_tables(_tbl(), _tbl()) == []


def test_single_cell_mismatch_is_located():
    diffs = diff_tables(_tbl(radius_h=8.0), _tbl(radius_h=8.5))
    assert len(diffs) == 1
    d = diffs[0]
    assert d["path"] == "rus_stage_to_score.girls.radius.H"
    assert d["a"] == 8.0 and d["b"] == 8.5 and d["kind"] == "value_mismatch"


def test_missing_cell_is_reported():
    a = _tbl()
    b = _tbl()
    del b["rus_stage_to_score"]["girls"]["radius"]["G"]  # B is missing a letter
    diffs = diff_tables(a, b)
    assert any(d["kind"] == "only_in_a" and d["path"].endswith("radius.G") for d in diffs)


def test_curve_mismatch_is_reported():
    a = _tbl()
    b = _tbl()
    b["rus_score_to_age"]["twiii"]["girls"] = [[13, 5.0], [117, 16.0]]  # last anchor differs
    diffs = diff_tables(a, b)
    assert any(d["path"] == "rus_score_to_age.twiii.girls" for d in diffs)


def test_reconcile_writes_locked_file_only_when_clean(tmp_path):
    out = tmp_path / "merged.json"
    res = reconcile(_tbl(), _tbl(), out_path=out)
    assert res["ok"] and out.exists()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert "checksum" in doc                       # merged file is checksum-locked

    res2 = reconcile(_tbl(radius_h=8.0), _tbl(radius_h=9.0), out_path=tmp_path / "no.json")
    assert res2["ok"] is False and not (tmp_path / "no.json").exists()


def test_cli_exit_codes(tmp_path, capsys):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps(_tbl()))
    b.write_text(json.dumps(_tbl()))
    assert main([str(a), str(b)]) == 0             # clean -> exit 0

    b.write_text(json.dumps(_tbl(radius_h=7.5)))
    assert main([str(a), str(b)]) == 1             # mismatch -> exit 1
    assert "MISMATCH" in capsys.readouterr().out
