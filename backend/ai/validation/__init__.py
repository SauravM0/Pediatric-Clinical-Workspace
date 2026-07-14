"""Bone-age validation & release-gate infrastructure (Plan 5).

Pure, deterministic evidence machinery: a frozen test-set registry + leak guard
(leak_guard), encoded engineering gates (gates), and the release-gate engine
(release_gate) that Plan 2 (WI-7) and Plan 3 (WI-8) call to decide whether a
candidate model may ship. A passing INTERNAL result is not a clinical accuracy
claim -- external validation is a separate, cohort-gated run.
"""
