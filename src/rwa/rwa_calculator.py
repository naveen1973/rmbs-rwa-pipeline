"""
RWA calculator for SEC-ERBA approach.

RWA = EAD × Risk Weight
Capital = RWA × 8%
"""

from dataclasses import dataclass

from .sec_erba import get_risk_weight
from .capital_structure import Tranche, CapitalStructure


CAPITAL_RATIO = 0.08  # 8% Basel capital requirement


@dataclass
class TrancheRWA:
    """RWA calculation result for a single tranche."""

    tranche_name: str
    rating: str | None
    seniority: str
    balance: float  # EAD
    thickness: float
    maturity: float
    risk_weight: float
    rwa: float
    capital: float

    @property
    def risk_weight_pct(self) -> float:
        """Risk weight as percentage."""
        return self.risk_weight * 100

    def to_dict(self) -> dict:
        """Convert to dictionary for reporting."""
        return {
            "tranche": self.tranche_name,
            "rating": self.rating or "NR",
            "seniority": self.seniority,
            "balance": round(self.balance, 2),
            "thickness": f"{self.thickness:.1%}",
            "maturity": f"{self.maturity:.1f}yr",
            "risk_weight": f"{self.risk_weight_pct:.1f}%",
            "rwa": round(self.rwa, 2),
            "capital": round(self.capital, 2),
        }


@dataclass
class DealRWA:
    """RWA calculation result for entire deal."""

    deal_id: str
    cutoff_date: str | None
    pool_balance: float
    tranche_results: list[TrancheRWA]

    @property
    def total_rwa(self) -> float:
        """Total RWA across all tranches."""
        return sum(t.rwa for t in self.tranche_results)

    @property
    def total_capital(self) -> float:
        """Total capital requirement."""
        return sum(t.capital for t in self.tranche_results)

    @property
    def weighted_avg_rw(self) -> float:
        """Balance-weighted average risk weight."""
        total_balance = sum(t.balance for t in self.tranche_results)
        if total_balance == 0:
            return 0.0
        return self.total_rwa / total_balance

    def summary(self) -> dict:
        """Summary statistics for the deal."""
        return {
            "deal_id": self.deal_id,
            "cutoff_date": self.cutoff_date,
            "pool_balance": round(self.pool_balance, 2),
            "total_rwa": round(self.total_rwa, 2),
            "total_capital": round(self.total_capital, 2),
            "weighted_avg_rw": f"{self.weighted_avg_rw * 100:.1f}%",
            "rwa_density": f"{(self.total_rwa / self.pool_balance) * 100:.1f}%",
        }

    def to_table(self) -> list[dict]:
        """Convert all tranche results to table format."""
        return [t.to_dict() for t in self.tranche_results]


def calculate_tranche_rwa(tranche: Tranche) -> TrancheRWA:
    """
    Calculate RWA for a single tranche.

    Args:
        tranche: Tranche object with rating, balance, maturity, etc.

    Returns:
        TrancheRWA with calculated risk weight, RWA, and capital.
    """
    rw = get_risk_weight(
        rating=tranche.rating,
        seniority=tranche.seniority,
        maturity=tranche.maturity,
        thickness=tranche.thickness,
    )

    rwa = tranche.balance * rw
    capital = rwa * CAPITAL_RATIO

    return TrancheRWA(
        tranche_name=tranche.name,
        rating=tranche.rating,
        seniority=tranche.seniority,
        balance=tranche.balance,
        thickness=tranche.thickness,
        maturity=tranche.maturity,
        risk_weight=rw,
        rwa=rwa,
        capital=capital,
    )


def calculate_deal_rwa(structure: CapitalStructure) -> DealRWA:
    """
    Calculate RWA for entire capital structure.

    Args:
        structure: CapitalStructure with tranches.

    Returns:
        DealRWA with results for all tranches and summary.
    """
    tranche_results = [calculate_tranche_rwa(t) for t in structure.tranches]

    return DealRWA(
        deal_id=structure.deal_id,
        cutoff_date=structure.cutoff_date,
        pool_balance=structure.pool_balance,
        tranche_results=tranche_results,
    )


def print_rwa_report(deal_rwa: DealRWA) -> None:
    """Print formatted RWA report to console."""
    print(f"\n{'=' * 80}")
    print(f"SEC-ERBA RWA REPORT: {deal_rwa.deal_id}")
    print(f"Cutoff: {deal_rwa.cutoff_date}")
    print(f"{'=' * 80}\n")

    # Tranche table
    print(f"{'Tranche':<10} {'Rating':<6} {'Senior':<8} {'Balance':>14} "
          f"{'Thick':>7} {'Mat':>5} {'RW':>8} {'RWA':>14} {'Capital':>12}")
    print("-" * 95)

    for t in deal_rwa.tranche_results:
        print(f"{t.tranche_name:<10} {t.rating or 'NR':<6} {t.seniority:<8} "
              f"£{t.balance:>12,.0f} {t.thickness:>6.1%} {t.maturity:>4.1f}y "
              f"{t.risk_weight_pct:>6.1f}% £{t.rwa:>12,.0f} £{t.capital:>10,.0f}")

    print("-" * 95)
    summary = deal_rwa.summary()
    print(f"{'TOTAL':<10} {'':<6} {'':<8} £{deal_rwa.pool_balance:>12,.0f} "
          f"{'':<7} {'':<5} {summary['weighted_avg_rw']:>8} "
          f"£{deal_rwa.total_rwa:>12,.0f} £{deal_rwa.total_capital:>10,.0f}")
    print(f"\nRWA Density: {summary['rwa_density']}")
    print()
