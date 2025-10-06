"""
Contract tests for name order expansion (Contract 1).

Tests the expand_name_orders method of AliasExpander class.
Requirements: FR-001, FR-004

These tests MUST FAIL initially (TDD requirement).
"""
import pytest
from jur_checker import AliasExpander


class TestNameOrderExpansion:
    """Contract tests for expand_name_orders method"""

    @pytest.fixture
    def expander(self):
        """Initialize AliasExpander for tests"""
        return AliasExpander(max_aliases=100)

    def test_two_part_name_no_patronymic(self, expander):
        """Test Case 1.1: Two-part name (no patronymic)"""
        # Arrange
        first = "Алексей"
        patronymic = None
        last = "Навальный"

        # Act
        result = expander.expand_name_orders(first, patronymic, last)

        # Assert
        assert len(result) == 2, f"Expected 2 variants, got {len(result)}"
        assert "Алексей Навальный" in result, "Missing 'First Last' variant"
        assert "Навальный Алексей" in result, "Missing 'Last First' variant"

    def test_three_part_name_with_patronymic(self, expander):
        """Test Case 1.2: Three-part name (with patronymic)"""
        # Arrange
        first = "Алексей"
        patronymic = "Анатольевич"
        last = "Навальный"

        # Act
        result = expander.expand_name_orders(first, patronymic, last)

        # Assert
        assert len(result) == 3, f"Expected 3 variants, got {len(result)}"
        assert "Алексей Анатольевич Навальный" in result, "Missing full name (FR-004)"
        assert "Алексей Навальный" in result, "Missing 'First Last' variant"
        assert "Навальный Алексей" in result, "Missing 'Last First' variant"

    def test_single_word_name(self, expander):
        """Test Case 1.3: Single-word name"""
        # Arrange
        first = "Навальный"
        patronymic = None
        last = "Навальный"

        # Act
        result = expander.expand_name_orders(first, patronymic, last)

        # Assert
        assert len(result) >= 1, f"Expected at least 1 variant, got {len(result)}"
        assert "Навальный Навальный" in result, "Missing repeated name variant"
