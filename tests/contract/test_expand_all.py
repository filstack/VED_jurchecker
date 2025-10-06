"""
Contract tests for expand_all orchestration (Contract 8).

Tests the expand_all method of AliasExpander class.
Requirements: FR-019, FR-020, FR-021

These tests MUST FAIL initially (TDD requirement).
"""
import pytest
from jur_checker import AliasExpander


class TestExpandAllOrchestration:
    """Contract tests for expand_all method"""

    @pytest.fixture
    def expander(self):
        """Initialize AliasExpander for tests"""
        return AliasExpander(max_aliases=100)

    def test_full_pipeline_russian_name(self, expander):
        """Test Case 8.1: Full pipeline (Russian name with all variants)"""
        # Arrange
        entity_name = "Алексей Навальный"

        # Act
        result = expander.expand_all(entity_name)

        # Assert
        # Should include original (normalized)
        assert "алексей навальный" in result, "Should include normalized original"

        # Should include name orders (FR-001)
        assert "навальный алексей" in result, "Should include reversed name order"

        # Should include initials (FR-002)
        assert any("а. навальный" in r for r in result), "Should include initial variants"

        # Should include morphological forms (FR-011)
        assert any("навального" in r for r in result), "Should include genitive case"

        # Should include transliterations (FR-006)
        assert any("navalny" in r for r in result), "Should include transliterations"

        # Should be normalized (lowercase, no ё)
        assert all(r == r.lower() for r in result), "All variants should be lowercase"

        # Should respect limit (FR-013)
        assert len(result) <= 100, f"Should respect max_aliases limit, got {len(result)}"

        # Should be unique
        assert len(result) == len(set(result)), "Should not contain duplicates"

    def test_foreign_name_fallback(self, expander):
        """Test Case 8.2: Foreign name (triggers heuristic fallback)"""
        # Arrange
        entity_name = "John Smith"

        # Act
        result = expander.expand_all(entity_name)

        # Assert
        # Should include normalized original
        assert "john smith" in result, "Should include normalized original"

        # Should trigger fallback (morphology will fail)
        assert len(result) > 0, "Should generate fallback variants"

        # Should include name orders
        assert "smith john" in result, "Should include reversed name order"

        # Should be normalized
        assert all(r == r.lower() for r in result), "All variants should be lowercase"

    def test_single_word_entity(self, expander):
        """Test Case 8.3: Single-word entity (edge case)"""
        # Arrange
        entity_name = "Газпром"

        # Act
        result = expander.expand_all(entity_name)

        # Assert
        # Should include normalized original
        assert "газпром" in result, "Should include normalized original"

        # Should include morphological forms
        assert any("газпрома" in r for r in result), "Should include genitive case"

        # Should include transliteration
        assert any("gazprom" in r for r in result), "Should include transliteration"

        # Should be normalized
        assert all(r == r.lower() for r in result), "All variants should be lowercase"

        # Should respect limit
        assert len(result) <= 100, "Should respect max_aliases limit"
