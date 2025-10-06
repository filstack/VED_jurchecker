"""
Contract tests for morphological case expansion (Contract 3).

Tests the expand_morphological_forms method of AliasExpander class.
Requirements: FR-011, FR-012

These tests MUST FAIL initially (TDD requirement).
"""
import pytest
from jur_checker import AliasExpander


class TestMorphologicalExpansion:
    """Contract tests for expand_morphological_forms method"""

    @pytest.fixture
    def expander(self):
        """Initialize AliasExpander for tests"""
        return AliasExpander(max_aliases=100)

    def test_standard_russian_surname(self, expander):
        """Test Case 3.1: Standard Russian surname (6 case forms)"""
        # Arrange
        surname = "Навальный"

        # Act
        result = expander.expand_morphological_forms(surname)

        # Assert
        # All results should be lowercase
        assert all(r == r.lower() for r in result), "All forms should be lowercase"

        # Check for expected case forms
        assert "навальный" in result, "Missing nominative case"
        assert "навального" in result, "Missing genitive case"
        assert "навальному" in result, "Missing dative case"
        assert "навальным" in result, "Missing instrumental case"
        assert "навальном" in result, "Missing prepositional case"

        # Should have at least 5 distinct forms
        assert len(result) >= 5, f"Expected at least 5 case forms, got {len(result)}"

    def test_foreign_surname_morphology_fails(self, expander):
        """Test Case 3.2: Foreign surname (morphology fails, returns empty)"""
        # Arrange
        surname = "Müller"

        # Act
        result = expander.expand_morphological_forms(surname)

        # Assert
        # Should return empty list when morphology fails
        # (triggering fallback in expand_all)
        assert result == [] or len(result) == 0, \
            "Foreign surname should return empty list when morphology fails"

    def test_feminine_surname(self, expander):
        """Test Case 3.3: Feminine surname"""
        # Arrange
        surname = "Иванова"

        # Act
        result = expander.expand_morphological_forms(surname)

        # Assert
        assert "иванова" in result, "Missing nominative case"
        assert "ивановой" in result, "Missing genitive/dative/instrumental/prepositional case"
        assert len(result) >= 2, "Should have at least nominative + genitive"
        assert all(r == r.lower() for r in result), "All forms should be lowercase"
