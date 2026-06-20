"""
SEC-ERBA risk weight table and lookup.

Basel 3.1 / UK CRR Article 263: Securitisation External Ratings-Based Approach.
Risk weights depend on: credit rating, seniority, and maturity.
"""

from typing import Literal

SeniorityType = Literal["senior", "non-senior"]

# SEC-ERBA risk weight table (Basel 3.1 / UK CRR)
# Format: {rating: {seniority: {maturity_years: risk_weight}}}
# Maturity 1 and 5 are the anchor points; intermediate values interpolate.
SEC_ERBA_TABLE: dict[str, dict[str, dict[int, float]]] = {
    "AAA": {
        "senior":     {1: 0.15, 5: 0.20},
        "non-senior": {1: 0.15, 5: 0.30},
    },
    "AA+": {
        "senior":     {1: 0.15, 5: 0.25},
        "non-senior": {1: 0.15, 5: 0.40},
    },
    "AA": {
        "senior":     {1: 0.20, 5: 0.30},
        "non-senior": {1: 0.25, 5: 0.50},
    },
    "AA-": {
        "senior":     {1: 0.25, 5: 0.35},
        "non-senior": {1: 0.30, 5: 0.55},
    },
    "A+": {
        "senior":     {1: 0.30, 5: 0.45},
        "non-senior": {1: 0.40, 5: 0.65},
    },
    "A": {
        "senior":     {1: 0.35, 5: 0.55},
        "non-senior": {1: 0.50, 5: 0.80},
    },
    "A-": {
        "senior":     {1: 0.45, 5: 0.70},
        "non-senior": {1: 0.60, 5: 0.95},
    },
    "BBB+": {
        "senior":     {1: 0.55, 5: 0.85},
        "non-senior": {1: 0.75, 5: 1.15},
    },
    "BBB": {
        "senior":     {1: 0.70, 5: 1.05},
        "non-senior": {1: 0.90, 5: 1.40},
    },
    "BBB-": {
        "senior":     {1: 0.90, 5: 1.40},
        "non-senior": {1: 1.20, 5: 1.85},
    },
    "BB+": {
        "senior":     {1: 1.20, 5: 1.85},
        "non-senior": {1: 1.40, 5: 2.70},
    },
    "BB": {
        "senior":     {1: 1.40, 5: 2.50},
        "non-senior": {1: 1.70, 5: 3.30},
    },
    "BB-": {
        "senior":     {1: 1.70, 5: 3.00},
        "non-senior": {1: 2.20, 5: 4.20},
    },
    "B+": {
        "senior":     {1: 2.20, 5: 3.80},
        "non-senior": {1: 3.30, 5: 5.80},
    },
    "B": {
        "senior":     {1: 2.80, 5: 4.60},
        "non-senior": {1: 4.70, 5: 7.50},
    },
    "B-": {
        "senior":     {1: 3.80, 5: 6.20},
        "non-senior": {1: 6.50, 5: 10.50},
    },
    "CCC+": {
        "senior":     {1: 5.20, 5: 9.20},
        "non-senior": {1: 10.00, 5: 12.50},
    },
    "CCC": {
        "senior":     {1: 7.00, 5: 12.50},
        "non-senior": {1: 12.50, 5: 12.50},
    },
    "CCC-": {
        "senior":     {1: 12.50, 5: 12.50},
        "non-senior": {1: 12.50, 5: 12.50},
    },
}

# Rating normalisation (map variants to canonical form)
RATING_MAP: dict[str, str] = {
    "Aaa": "AAA", "AAA": "AAA",
    "Aa1": "AA+", "AA+": "AA+",
    "Aa2": "AA",  "AA": "AA",
    "Aa3": "AA-", "AA-": "AA-",
    "A1": "A+",   "A+": "A+",
    "A2": "A",    "A": "A",
    "A3": "A-",   "A-": "A-",
    "Baa1": "BBB+", "BBB+": "BBB+",
    "Baa2": "BBB",  "BBB": "BBB",
    "Baa3": "BBB-", "BBB-": "BBB-",
    "Ba1": "BB+",   "BB+": "BB+",
    "Ba2": "BB",    "BB": "BB",
    "Ba3": "BB-",   "BB-": "BB-",
    "B1": "B+",     "B+": "B+",
    "B2": "B",      "B": "B",
    "B3": "B-",     "B-": "B-",
    "Caa1": "CCC+", "CCC+": "CCC+",
    "Caa2": "CCC",  "CCC": "CCC",
    "Caa3": "CCC-", "CCC-": "CCC-",
}

FLOOR_RW = 0.15  # 15% floor per Basel 3.1
UNRATED_RW = 12.50  # 1250% for unrated tranches


def normalise_rating(rating: str | None) -> str | None:
    """Normalise rating to S&P format (AAA, AA+, etc.)."""
    if rating is None:
        return None
    return RATING_MAP.get(rating.strip())


def interpolate_maturity(rw_1yr: float, rw_5yr: float, maturity: float) -> float:
    """Linear interpolation between 1yr and 5yr risk weights."""
    if maturity <= 1:
        return rw_1yr
    if maturity >= 5:
        return rw_5yr
    return rw_1yr + (rw_5yr - rw_1yr) * (maturity - 1) / 4


def get_risk_weight(
    rating: str | None,
    seniority: SeniorityType,
    maturity: float,
    thickness: float | None = None,
) -> float:
    """
    Look up SEC-ERBA risk weight.

    Args:
        rating: Credit rating (S&P or Moody's format, e.g. "AAA", "Aa1")
        seniority: "senior" or "non-senior"
        maturity: Weighted average life in years
        thickness: Tranche thickness (D - A) for non-senior adjustment (optional)

    Returns:
        Risk weight as decimal (0.15 = 15%, 12.50 = 1250%)
    """
    # Unrated → 1250%
    norm_rating = normalise_rating(rating)
    if norm_rating is None:
        return UNRATED_RW

    # Lookup base risk weight
    if norm_rating not in SEC_ERBA_TABLE:
        return UNRATED_RW

    rw_table = SEC_ERBA_TABLE[norm_rating][seniority]
    rw = interpolate_maturity(rw_table[1], rw_table[5], maturity)

    # Non-senior thickness adjustment (CRR Article 264)
    # For thin mezzanine tranches, risk weight increases
    if seniority == "non-senior" and thickness is not None and thickness < 0.10:
        # Simplified: scale up for thin tranches (< 10% thickness)
        rw = rw * (1 + (0.10 - thickness) * 2)

    # Apply floor
    rw = max(rw, FLOOR_RW)

    return round(rw, 4)
