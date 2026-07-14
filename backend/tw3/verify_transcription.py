"""Dual-transcription reconciliation for licensed TW3 letter tables (Plan 1 WI-2).

The standard control for copyrighted numeric tables: two people transcribe the
SAME licensed book independently into two files, and every cell is compared. A
single typo the provenance/reference-case gates might miss is caught here, with
its exact location. Only on an EMPTY diff is a merged, checksum-locked canonical
file produced.

Compares only the transcribed copyrighted content -- the point tables and the
score->age curves. Provenance and the clinic's own reference_cases are NOT part of
the book transcription, so they are not diffed.

Pure (diff is I/O-free); the CLI reads/writes files.

    python -m backend.tw3.verify_transcription A.json B.json [--out merged.json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .letters_scoring import save_letter_tables

# sections that carry copyrighted, dual-transcribed values
_POINT_SECTIONS = ("rus_stage_to_score", "carpal_stage_to_score", "tw20_stage_to_score")
_CURVE_2 = ("rus_score_to_age", "carpal_score_to_age")   # section -> curve -> sex -> anchors
_CURVE_1 = ("tw20_score_to_age",)                        # section -> sex -> anchors


def _strip(d: Any) -> dict:
    return {k: v for k, v in (d or {}).items() if not str(k).startswith("_")}


def _flatten(tbl: dict) -> dict:
    """Flatten the transcribed sections to ``{dotted.path: value}`` for cell diff."""
    flat: dict[str, Any] = {}
    for sec in _POINT_SECTIONS:
        for sex, bones in _strip(tbl.get(sec, {})).items():
            for bone, rows in _strip(bones).items():
                for letter, pts in _strip(rows).items():
                    flat[f"{sec}.{sex}.{bone}.{letter}"] = pts
    for sec in _CURVE_2:
        for curve, by_sex in _strip(tbl.get(sec, {})).items():
            for sex, anchors in _strip(by_sex).items():
                flat[f"{sec}.{curve}.{sex}"] = [list(a) for a in (anchors or [])]
    for sec in _CURVE_1:
        for sex, anchors in _strip(tbl.get(sec, {})).items():
            flat[f"{sec}.{sex}"] = [list(a) for a in (anchors or [])]
    return flat


def diff_tables(a: dict, b: dict) -> list[dict]:
    """Cell-by-cell diff of two transcriptions. Each mismatch is
    ``{path, kind, a, b}`` where kind is only_in_a / only_in_b / value_mismatch."""
    fa, fb = _flatten(a), _flatten(b)
    diffs: list[dict] = []
    for key in sorted(set(fa) | set(fb)):
        if key not in fa:
            diffs.append({"path": key, "kind": "only_in_b", "a": None, "b": fb[key]})
        elif key not in fb:
            diffs.append({"path": key, "kind": "only_in_a", "a": fa[key], "b": None})
        elif fa[key] != fb[key]:
            diffs.append({"path": key, "kind": "value_mismatch", "a": fa[key], "b": fb[key]})
    return diffs


def reconcile(a: dict, b: dict, out_path: Path | None = None) -> dict:
    """Diff two transcriptions; on a clean match optionally write a merged,
    checksum-locked canonical file (using transcription A as the base). Returns a
    result dict with ``ok`` and the mismatches."""
    diffs = diff_tables(a, b)
    result = {"ok": not diffs, "n_mismatches": len(diffs), "mismatches": diffs}
    if not diffs and out_path is not None:
        save_letter_tables(dict(a), Path(out_path))   # validates + locks
        result["written"] = str(out_path)
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Reconcile two independent TW3 transcriptions")
    ap.add_argument("file_a")
    ap.add_argument("file_b")
    ap.add_argument("--out", default=None, help="write the merged+checksummed file if clean")
    args = ap.parse_args(argv)

    a = json.loads(Path(args.file_a).read_text(encoding="utf-8"))
    b = json.loads(Path(args.file_b).read_text(encoding="utf-8"))
    res = reconcile(a, b, Path(args.out) if args.out else None)
    if res["ok"]:
        print(f"OK — transcriptions match ({len(_flatten(a))} cells).")
        if res.get("written"):
            print(f"Wrote merged, checksum-locked file: {res['written']}")
        return 0
    print(f"MISMATCH — {res['n_mismatches']} cell(s) differ:")
    for m in res["mismatches"]:
        print(f"  {m['path']}: A={m['a']!r}  B={m['b']!r}  ({m['kind']})")
    print("Resolve each against the licensed book, then re-run.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
