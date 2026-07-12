# Bone-age product starter data pack

This pack contains the non-proprietary data structures that can be used immediately to
build and test a bone-age analysis application.

## Included

- `bone_inventory.csv` — the 13 RUS and 7 carpal bone inventory.
- `case_input_schema.json` — patient and radiograph input fields.
- `per_bone_annotation_template.csv` — annotation format for boxes, masks, stages, readers, and adjudication.
- `licensed_reference_loader.json` — empty, code-ready structure for licensed TW reference data.
- `report_output_schema.json` — clinician-reviewed report structure.
- `validation_protocol.md` — testing, quality-control, abstention, and release requirements.

## What this pack does not contain

It does not contain the copyrighted official TW stage descriptions, reference illustrations,
sex-specific stage point tables, score-to-age tables, or adult-height prediction tables.

## Safe product path

1. Train a whole-hand research model using a legally obtained public bone-age dataset.
2. Build the 20-bone localization and annotation workflow.
3. Have trained clinicians annotate local images using a licensed manual.
4. Install the licensed reference values through `licensed_reference_loader.json`.
5. Validate internally and externally.
6. Keep every patient report under clinician review until regulatory and clinical validation are complete.

## Critical distinction

The public RSNA dataset provides whole-image bone-age labels and sex. It does not provide
official TW3 A–I labels for each of the 20 bones. It can train a baseline age estimator, but
it cannot by itself create a genuine TW3 per-bone scoring engine.
