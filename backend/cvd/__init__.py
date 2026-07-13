"""Adult cardiovascular-risk models (kept separate from the paediatric modules)."""
from .qrisk3 import QRISK3_ELIGIBLE_AGE, qrisk3

__all__ = ["qrisk3", "QRISK3_ELIGIBLE_AGE"]
