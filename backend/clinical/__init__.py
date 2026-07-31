"""Clinical reasoning: red flags, triage, adult-height context (M5).

Pure domain package -- no database, no HTTP, no I/O beyond its own thresholds
file. ``clinical_service`` builds a snapshot from the ORM and hands it in.

Modules:
    snapshot    PatientSnapshot (the only input) and Finding (the only output)
    rules       the rule set and the engine, with suppression
    prediction  mid-parental target (open) and Khamis-Roche (gated)
    referral    findings -> triage level, specialty routing, parent wording
    thresholds.json  every number, with a source
"""
from .snapshot import ATTENTION, INFO, INSUFFICIENT_DATA, URGENT, Finding, PatientSnapshot

__all__ = ["PatientSnapshot", "Finding", "URGENT", "ATTENTION", "INFO", "INSUFFICIENT_DATA"]
