"""
Unit tests for SEC-ERBA RWA engine.
"""

import pytest
from src.rwa.sec_erba import get_risk_weight, normalise_rating, interpolate_maturity, FLOOR_RW, UNRATED_RW
from src.rwa.capital_structure import Tranche, CapitalStructure, create_avon_structure
from src.rwa.rwa_calculator import calculate_tranche_rwa, calculate_deal_rwa


class TestRatingNormalisation:
    """Test rating format normalisation."""

    def test_sp_format_unchanged(self):
        assert normalise_rating("AAA") == "AAA"
        assert normalise_rating("BB+") == "BB+"

    def test_moodys_to_sp(self):
        assert normalise_rating("Aaa") == "AAA"
        assert normalise_rating("Aa1") == "AA+"
        assert normalise_rating("Baa2") == "BBB"

    def test_none_returns_none(self):
        assert normalise_rating(None) is None

    def test_unknown_rating(self):
        assert normalise_rating("XYZ") is None


class TestMaturityInterpolation:
    """Test linear interpolation between 1yr and 5yr."""

    def test_at_1yr(self):
        assert interpolate_maturity(0.15, 0.20, 1.0) == 0.15

    def test_at_5yr(self):
        assert interpolate_maturity(0.15, 0.20, 5.0) == 0.20

    def test_at_3yr_midpoint(self):
        # 3yr is exactly midpoint: (0.15 + 0.20) / 2 = 0.175
        result = interpolate_maturity(0.15, 0.20, 3.0)
        assert result == pytest.approx(0.175, rel=1e-6)

    def test_below_1yr_uses_1yr(self):
        assert interpolate_maturity(0.15, 0.20, 0.5) == 0.15

    def test_above_5yr_uses_5yr(self):
        assert interpolate_maturity(0.15, 0.20, 7.0) == 0.20


class TestRiskWeightLookup:
    """Test SEC-ERBA risk weight lookup."""

    def test_aaa_senior_1yr(self):
        rw = get_risk_weight("AAA", "senior", 1.0)
        assert rw == 0.15  # 15% floor

    def test_aaa_senior_5yr(self):
        rw = get_risk_weight("AAA", "senior", 5.0)
        assert rw == 0.20

    def test_bbb_non_senior_3yr(self):
        rw = get_risk_weight("BBB", "non-senior", 3.0)
        # Interpolate: 0.90 + (1.40 - 0.90) * (3-1)/4 = 1.15
        assert rw == pytest.approx(1.15, rel=1e-2)

    def test_unrated_returns_1250pct(self):
        rw = get_risk_weight(None, "non-senior", 3.0)
        assert rw == UNRATED_RW  # 12.50 = 1250%

    def test_moodys_format_works(self):
        rw = get_risk_weight("Aaa", "senior", 1.0)
        assert rw == 0.15

    def test_floor_applied(self):
        rw = get_risk_weight("AAA", "senior", 0.5)
        assert rw >= FLOOR_RW


class TestTranche:
    """Test Tranche class."""

    def test_thickness_calculation(self):
        t = Tranche("A", "AAA", 100, attachment=0.15, detachment=1.00, maturity=3.0, seniority="senior")
        assert t.thickness == 0.85

    def test_is_senior(self):
        t = Tranche("A", "AAA", 100, 0.15, 1.00, 3.0, seniority="senior")
        assert t.is_senior is True

        t2 = Tranche("B", "AA", 50, 0.08, 0.15, 3.0, seniority="non-senior")
        assert t2.is_senior is False

    def test_invalid_attachment_raises(self):
        with pytest.raises(ValueError):
            Tranche("A", "AAA", 100, attachment=-0.1, detachment=1.0, maturity=3.0)

    def test_detachment_must_exceed_attachment(self):
        with pytest.raises(ValueError):
            Tranche("A", "AAA", 100, attachment=0.5, detachment=0.3, maturity=3.0)


class TestCapitalStructure:
    """Test CapitalStructure class."""

    def test_create_avon_structure(self):
        structure = create_avon_structure(839_000_000, "2020-11-30")
        assert structure.deal_id == "AVON2"
        assert len(structure.tranches) == 5
        assert structure.credit_enhancement == 0.15

    def test_validation_detects_overlap(self):
        structure = CapitalStructure("TEST", 100_000_000)
        structure.add_tranche(Tranche("A", "AAA", 80, 0.15, 1.00, 3.0, "senior"))
        structure.add_tranche(Tranche("B", "AA", 20, 0.10, 0.20, 3.0, "non-senior"))  # Overlaps!
        errors = structure.validate()
        assert any("overlap" in e.lower() for e in errors)


class TestRWACalculation:
    """Test RWA calculations."""

    def test_simple_tranche_rwa(self):
        t = Tranche("A", "AAA", 1_000_000, 0.15, 1.00, 3.0, "senior")
        result = calculate_tranche_rwa(t)

        assert result.tranche_name == "A"
        assert result.balance == 1_000_000
        # AAA senior 3yr: interpolate 0.15 + (0.20-0.15)*(3-1)/4 = 0.175
        assert result.risk_weight == pytest.approx(0.175, rel=1e-2)
        assert result.rwa == pytest.approx(175_000, rel=1e-2)
        assert result.capital == pytest.approx(14_000, rel=1e-2)

    def test_deal_rwa_totals(self):
        structure = create_avon_structure(839_000_000, "2020-11-30")
        result = calculate_deal_rwa(structure)

        assert result.deal_id == "AVON2"
        assert len(result.tranche_results) == 5
        assert result.total_rwa > 0
        assert result.total_capital == result.total_rwa * 0.08

    def test_unrated_tranche_high_rwa(self):
        t = Tranche("FLP", None, 1_000_000, 0.00, 0.01, 5.0, "non-senior")
        result = calculate_tranche_rwa(t)

        assert result.risk_weight == UNRATED_RW  # 1250%
        assert result.rwa == 12_500_000  # 1M × 12.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
