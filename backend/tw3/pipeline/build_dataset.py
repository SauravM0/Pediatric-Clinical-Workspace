"""
CLI: build the TW3 training set from report texts and print a readiness report.

    python -m backend.tw3.pipeline.build_dataset [reports_dir] [--out manifest.json]

Reports are .txt files (transcribed or OCR'd radiology reports). Each becomes one
labelled record. Pair each with its DICOM/PNG via the `report_file`/`image_ref`
fields once films are exported.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from .dataset import build, RUS_KEYS, STAGES

DEFAULT_DIR = Path(__file__).with_name("sample_reports")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build TW3 training set from reports")
    ap.add_argument("reports_dir", nargs="?", default=str(DEFAULT_DIR))
    ap.add_argument("--out", default=None, help="write full manifest JSON here")
    args = ap.parse_args()

    result = build(Path(args.reports_dir))
    cov = result["coverage"]

    print(f"Reports parsed : {result['n_reports']}")
    print(f"Valid for training : {len(result['valid'])}   Invalid : {len(result['invalid'])}")
    for bad in result["invalid"]:
        print(f"  - {bad['case_id']}: {'; '.join(bad['problems'])}")

    print(f"\nStage-coverage : {cov['cells_covered']}/{cov['cells_total']} "
          f"(bone x stage) cells have >=1 example")
    print("Stage totals   : " + "  ".join(f"{s}:{cov['stage_totals'][s]}" for s in STAGES))

    # Compact per-bone grid so gaps are obvious.
    print("\nPer-bone stage counts (rows=bones, cols=A..I):")
    print("        " + "  ".join(STAGES))
    for k in RUS_KEYS:
        row = cov["per_bone"][k]
        print(f"  {k:<6} " + "  ".join(str(row[s]) for s in STAGES))

    missing = cov["empty_cells"]
    print(f"\nEmpty cells (need PACS films): {len(missing)} of {cov['cells_total']}")
    print("A per-bone stage classifier needs examples in (nearly) every cell above.")
    print("Export past hand films whose reports fill the zero cells first.")

    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nManifest written: {args.out}")


if __name__ == "__main__":
    main()
