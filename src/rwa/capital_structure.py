"""
Capital structure representation for RMBS tranches.

Each tranche has:
- Attachment point (A): where losses start hitting this tranche
- Detachment point (D): where losses fully wipe out this tranche
- Thickness = D - A
- Seniority: senior (most senior tranche) vs non-senior
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Tranche:
    """A single tranche in a securitisation capital structure."""

    name: str
    rating: str | None  # S&P or Moody's format, None if unrated
    balance: float  # Current outstanding balance (GBP)
    attachment: float  # Attachment point (0.00 - 1.00)
    detachment: float  # Detachment point (0.00 - 1.00)
    maturity: float  # Weighted average life (years)
    seniority: Literal["senior", "non-senior"] = "non-senior"

    @property
    def thickness(self) -> float:
        """Tranche thickness = D - A."""
        return self.detachment - self.attachment

    @property
    def is_senior(self) -> bool:
        """True if this is the most senior tranche."""
        return self.seniority == "senior"

    def __post_init__(self):
        if self.attachment < 0 or self.attachment > 1:
            raise ValueError(f"Attachment must be 0-1, got {self.attachment}")
        if self.detachment < 0 or self.detachment > 1:
            raise ValueError(f"Detachment must be 0-1, got {self.detachment}")
        if self.detachment <= self.attachment:
            raise ValueError(f"Detachment ({self.detachment}) must be > attachment ({self.attachment})")


@dataclass
class CapitalStructure:
    """Complete capital structure of a securitisation deal."""

    deal_id: str
    pool_balance: float  # Total pool balance (GBP)
    tranches: list[Tranche] = field(default_factory=list)
    cutoff_date: str | None = None

    def add_tranche(self, tranche: Tranche) -> None:
        """Add a tranche to the structure."""
        self.tranches.append(tranche)

    @property
    def total_tranche_balance(self) -> float:
        """Sum of all tranche balances."""
        return sum(t.balance for t in self.tranches)

    @property
    def credit_enhancement(self) -> float:
        """Credit enhancement = subordination below most senior tranche."""
        if not self.tranches:
            return 0.0
        senior = [t for t in self.tranches if t.is_senior]
        if not senior:
            return 0.0
        return senior[0].attachment

    def get_tranche(self, name: str) -> Tranche | None:
        """Find tranche by name."""
        for t in self.tranches:
            if t.name == name:
                return t
        return None

    def validate(self) -> list[str]:
        """Check structure integrity, return list of errors."""
        errors = []

        # Check tranches don't overlap
        sorted_tranches = sorted(self.tranches, key=lambda t: t.attachment)
        for i in range(len(sorted_tranches) - 1):
            if sorted_tranches[i].detachment > sorted_tranches[i + 1].attachment:
                errors.append(
                    f"Tranches {sorted_tranches[i].name} and {sorted_tranches[i+1].name} overlap"
                )

        # Check exactly one senior tranche
        senior_count = sum(1 for t in self.tranches if t.is_senior)
        if senior_count != 1:
            errors.append(f"Expected 1 senior tranche, found {senior_count}")

        # Check senior is most senior
        if self.tranches:
            max_detachment = max(t.detachment for t in self.tranches)
            for t in self.tranches:
                if t.is_senior and t.detachment != max_detachment:
                    errors.append(f"Senior tranche {t.name} is not most senior by detachment")

        return errors


def create_avon_structure(pool_balance: float, cutoff_date: str) -> CapitalStructure:
    """
    Create Avon Finance No.2 capital structure.

    Based on investor report structure. Simplified for demonstration.
    Actual attachment/detachment points from deal documentation.
    """
    structure = CapitalStructure(
        deal_id="AVON2",
        pool_balance=pool_balance,
        cutoff_date=cutoff_date,
    )

    # Class A (senior) - typically AAA rated
    structure.add_tranche(Tranche(
        name="Class A",
        rating="AAA",
        balance=pool_balance * 0.85,  # ~85% of pool
        attachment=0.15,
        detachment=1.00,
        maturity=3.5,
        seniority="senior",
    ))

    # Class B (mezzanine) - typically AA
    structure.add_tranche(Tranche(
        name="Class B",
        rating="AA",
        balance=pool_balance * 0.07,
        attachment=0.08,
        detachment=0.15,
        maturity=4.0,
        seniority="non-senior",
    ))

    # Class C (mezzanine) - typically A
    structure.add_tranche(Tranche(
        name="Class C",
        rating="A",
        balance=pool_balance * 0.04,
        attachment=0.04,
        detachment=0.08,
        maturity=4.5,
        seniority="non-senior",
    ))

    # Class D (junior) - typically BBB or below
    structure.add_tranche(Tranche(
        name="Class D",
        rating="BBB",
        balance=pool_balance * 0.03,
        attachment=0.01,
        detachment=0.04,
        maturity=5.0,
        seniority="non-senior",
    ))

    # First Loss Piece (unrated)
    structure.add_tranche(Tranche(
        name="FLP",
        rating=None,  # Unrated
        balance=pool_balance * 0.01,
        attachment=0.00,
        detachment=0.01,
        maturity=5.0,
        seniority="non-senior",
    ))

    return structure
