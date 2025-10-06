"""
Contract tests for text normalization (Contract 7).

Tests the normalize_alias method of AliasExpander class.
Requirements: FR-016, FR-017, FR-018

These tests MUST FAIL initially (TDD requirement).
"""
import pytest
from jur_checker import AliasExpander


class TestNormalization:
    """Contract tests for normalize_alias method"""

    @pytest.fixture
    def expander(self):
        """Initialize AliasExpander for tests"""
        return AliasExpander(max_aliases=100)

    def test_yo_replacement(self, expander):
        """Test Case 7.1: ё → е replacement (FR-016)"""
        # Arrange
        alias = "Алёша Попович"

        # Act
        result = expander.normalize_alias(alias)

        # Assert
        assert "ё" not in result, "Should replace ё with е"
        assert "алеша попович" == result, "Should correctly replace ё → е and lowercase"

    def test_lowercase_conversion(self, expander):
        """Test Case 7.2: Lowercase conversion (FR-017)"""
        # Arrange
        alias = "НАВАЛЬНЫЙ Алексей"

        # Act
        result = expander.normalize_alias(alias)

        # Assert
        assert result == result.lower(), "Should convert to lowercase"
        assert result == "навальный алексей", "Should be fully lowercase"

    def test_whitespace_cleanup(self, expander):
        """Test Case 7.3: Whitespace cleanup (FR-018)"""
        # Arrange
        alias = "  Навальный   Алексей  "

        # Act
        result = expander.normalize_alias(alias)

        # Assert
        assert result == "навальный алексей", "Should trim and normalize whitespace"
        assert "  " not in result, "Should not contain double spaces"
        assert not result.startswith(" "), "Should not start with space"
        assert not result.endswith(" "), "Should not end with space"

    def test_combined_normalization(self, expander):
        """Test Case 7.4: Combined normalization (all rules)"""
        # Arrange
        alias = "  АЛЁША  Попович  "

        # Act
        result = expander.normalize_alias(alias)

        # Assert
        # Should apply all normalization rules
        assert result == "алеша попович", \
            "Should apply ё→е, lowercase, and whitespace cleanup"
        assert "ё" not in result, "Should replace ё"
        assert result == result.lower(), "Should be lowercase"
        assert "  " not in result, "Should normalize whitespace"
