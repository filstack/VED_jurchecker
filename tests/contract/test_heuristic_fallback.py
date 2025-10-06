"""
Contract tests for heuristic fallback (Contract 6).

Tests the apply_heuristic_fallback method of AliasExpander class.
Requirements: FR-008, FR-009, FR-010

These tests MUST FAIL initially (TDD requirement).
"""
import pytest
from jur_checker import AliasExpander


class TestHeuristicFallback:
    """Contract tests for apply_heuristic_fallback method"""

    @pytest.fixture
    def expander(self):
        """Initialize AliasExpander for tests"""
        return AliasExpander(max_aliases=100)

    def test_empty_morphology_triggers_fallback(self, expander):
        """Test Case 6.1: Empty morphology triggers fallback"""
        # Arrange
        full_name = "John Smith"
        morphology_results = []  # Empty (morphology failed)

        # Act
        result = expander.apply_heuristic_fallback(full_name, morphology_results)

        # Assert
        # Should return heuristic variants when morphology is empty
        assert len(result) > 0, "Should generate heuristic variants when morphology fails"
        assert isinstance(result, list), "Should return a list"

    def test_successful_morphology_no_fallback(self, expander):
        """Test Case 6.2: Successful morphology (no fallback)"""
        # Arrange
        full_name = "Навальный"
        morphology_results = ["навальный", "навального", "навальному"]  # Non-empty

        # Act
        result = expander.apply_heuristic_fallback(full_name, morphology_results)

        # Assert
        # Should return morphology results unchanged (no fallback needed)
        assert result == morphology_results, "Should return morphology results when available"
        assert len(result) == 3, "Should preserve morphology results"

    def test_foreign_name_fallback(self, expander):
        """Test Case 6.3: Foreign name fallback (common patterns)"""
        # Arrange
        full_name = "Müller"
        morphology_results = []  # Empty (foreign name)

        # Act
        result = expander.apply_heuristic_fallback(full_name, morphology_results)

        # Assert
        # Should generate at least the lowercase form
        assert len(result) > 0, "Should generate fallback variants"
        assert "müller" in result or full_name.lower() in result, \
            "Should include lowercase variant"
        # All results should be lowercase
        assert all(r == r.lower() for r in result), "All fallback variants should be lowercase"
