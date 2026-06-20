"""
SEC-ERBA RWA Engine for UK RMBS securitisations.

Implements Basel 3.1 / UK CRR Securitisation External Ratings-Based Approach:
- Risk weight lookup by rating, seniority, maturity
- Tranche attachment/detachment/thickness
- RWA = EAD × Risk Weight
- Capital = RWA × 8%
"""

from .sec_erba import get_risk_weight, SEC_ERBA_TABLE
from .capital_structure import Tranche, CapitalStructure
from .rwa_calculator import calculate_tranche_rwa, calculate_deal_rwa

__all__ = [
    "get_risk_weight",
    "SEC_ERBA_TABLE",
    "Tranche",
    "CapitalStructure",
    "calculate_tranche_rwa",
    "calculate_deal_rwa",
]
