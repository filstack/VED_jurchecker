"""
Contract tests for alias limit enforcement (Contract 5).

Tests the prioritize_aliases method of AliasExpander class.
Requirements: FR-013, FR-014, FR-015

These tests MUST FAIL initially (TDD requirement).
"""
import pytest
from jur_checker import AliasExpander


class TestAliasLimitEnforcement:
    """Contract tests for prioritize_aliases method"""

    @pytest.fixture
    def expander(self):
        """Initialize AliasExpander for tests"""
        return AliasExpander(max_aliases=100)

    def test_under_limit_no_truncation(self, expander):
        """Test Case 5.1: Under limit (no truncation)"""
        # Arrange
        aliases = [f"alias_{i}" for i in range(50)]

        # Act
        result = expander.prioritize_aliases(aliases)

        # Assert
        assert len(result) == 50, "Should not truncate when under limit"
        assert result == aliases, "Should preserve all aliases when under limit"

    def test_over_limit_truncation(self, expander):
        """Test Case 5.2: Over limit (truncation to max_aliases)"""
        # Arrange
        # Create 150 aliases (over the 100 limit)
        aliases = [f"alias_{i}" for i in range(150)]

        # Act
        result = expander.prioritize_aliases(aliases)

        # Assert
        assert len(result) == 100, f"Should truncate to max_aliases=100, got {len(result)}"
        # Should keep first 100 (higher priority items)
        assert result == aliases[:100], "Should keep highest priority aliases"

    def test_prioritization_order(self, expander):
        """Test Case 5.3: Prioritization order (full name > initials > morphology)"""
        # Arrange
        # Simulate prioritized list with full names first, then initials, then morphology
        aliases = [
            "Алексей Навальный",           # Full name (highest priority)
            "А. Навальный",                # Initials
            "навального",                  # Morphological form (lowest priority)
            "navalny"                      # Transliteration
        ]

        # Act
        result = expander.prioritize_aliases(aliases)

        # Assert
        # Order should be preserved (full names first)
        assert result[0] == "Алексей Навальный", "Full name should have highest priority"
        assert len(result) == 4, "Should preserve all aliases when under limit"
