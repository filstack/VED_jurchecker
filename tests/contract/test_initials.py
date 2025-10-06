"""
Contract tests for initial expansion (Contract 2).

Tests the expand_initials method of AliasExpander class.
Requirements: FR-002, FR-003

These tests MUST FAIL initially (TDD requirement).
"""
import pytest
from jur_checker import AliasExpander


class TestInitialExpansion:
    """Contract tests for expand_initials method"""

    @pytest.fixture
    def expander(self):
        """Initialize AliasExpander for tests"""
        return AliasExpander(max_aliases=100)

    def test_single_initial_no_patronymic(self, expander):
        """Test Case 2.1: Single initial (no patronymic)"""
        # Arrange
        first = "Алексей"
        patronymic = None
        last = "Навальный"

        # Act
        result = expander.expand_initials(first, patronymic, last)

        # Assert
        assert len(result) == 2, f"Expected 2 variants, got {len(result)}"
        assert "А. Навальный" in result, "Missing 'I. Last' variant (FR-002)"
        assert "Навальный А." in result, "Missing 'Last I.' variant (FR-002)"

    def test_double_initial_with_patronymic(self, expander):
        """Test Case 2.2: Double initial (with patronymic)"""
        # Arrange
        first = "Алексей"
        patronymic = "Анатольевич"
        last = "Навальный"

        # Act
        result = expander.expand_initials(first, patronymic, last)

        # Assert
        assert len(result) == 4, f"Expected 4 variants, got {len(result)}"
        assert "А. Навальный" in result, "Missing single initial variant"
        assert "Навальный А." in result, "Missing reversed single initial"
        assert "А.А. Навальный" in result, "Missing double initial (FR-003)"
        assert "Навальный А.А." in result, "Missing reversed double initial (FR-003)"

    def test_unicode_cyrillic_initials(self, expander):
        """Test Case 2.3: Unicode handling (Cyrillic initials)"""
        # Arrange
        first = "Юрий"
        patronymic = "Павлович"
        last = "Лужков"

        # Act
        result = expander.expand_initials(first, patronymic, last)

        # Assert
        assert "Ю. Лужков" in result, "Cyrillic Ю not correctly extracted"
        assert "Ю.П. Лужков" in result, "Double Cyrillic initials not correctly extracted"
        assert len(result) == 4, "Should generate 4 initial variants"
