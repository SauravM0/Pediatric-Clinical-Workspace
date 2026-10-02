"""
Build and validate a TW3 training set from parsed report records, and produce a
stage-coverage readiness report.

Why coverage matters: to train the per-bone stage classifier (PEARLS "RL" module)
you need examples of every bone at every stage it can take. This module quantifies
that gap so PACS export is targeted, not blind.
"""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from .report_parser import parse_report, RUS_ALIASES

RUS_KEYS = [k for k, _ in RUS_ALIASES]
STAGES = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]


def record_from_report_file(path: Path) -> Dict:
    rec = parse_report(path.read_text(encoding="utf-8"))
    rec["case_id"] = path.stem
    rec["report_file"] = path.name
    return rec


def validate_record(rec: Dict) -> List[str]:
    """Return a list of problems; empty list == valid for training."""
    problems = []
    if rec.get("sex") not in ("boys", "girls"):
        problems.append("sex missing/unrecognised")
    stages = rec.get("rus_stages", {})
    for key in RUS_KEYS:
        st = stages.get(key)
        if st is None:
            problems.append(f"unstaged RUS bone: {key}")
        elif st not in STAGES:
            problems.append(f"invalid stage '{st}' for {key}")
    if rec.get("reported", {}).get("twiii_rus_bone_age_years") is None:
        problems.append("no TWIII-RUS bone age (needed as regression target)")
    return problems


def coverage(records: List[Dict]) -> Dict:
    """Per-bone stage counts + list of (bone, stage) cells with zero examples."""
    counts = {k: {s: 0 for s in STAGES} for k in RUS_KEYS}
    for rec in records:
        for key, st in rec.get("rus_stages", {}).items():
            if key in counts and st in STAGES:
                counts[key][st] += 1
    empty_cells = [(k, s) for k in RUS_KEYS for s in STAGES if counts[k][s] == 0]
    stage_totals = defaultdict(int)
    for k in RUS_KEYS:
        for s in STAGES:
            stage_totals[s] += counts[k][s]
    return {"per_bone": counts, "empty_cells": empty_cells,
            "stage_totals": dict(stage_totals),
            "cells_total": len(RUS_KEYS) * len(STAGES),
            "cells_covered": len(RUS_KEYS) * len(STAGES) - len(empty_cells)}


def build(reports_dir: Path) -> Dict:
    files = sorted(reports_dir.glob("*.txt"))
    records = [record_from_report_file(p) for p in files]
    valid, invalid = [], []
    for rec in records:
        probs = validate_record(rec)
        (valid if not probs else invalid).append({"case_id": rec["case_id"], "problems": probs})
    return {"n_reports": len(records), "records": records,
            "valid": valid, "invalid": invalid, "coverage": coverage(records)}
