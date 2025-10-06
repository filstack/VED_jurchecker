"""
Contract tests for transliteration expansion (Contract 4).

Tests the expand_transliterations method of AliasExpander class.
Requirements: FR-006, FR-007

These tests MUST FAIL initially (TDD requirement).
"""
import pytest
from jur_checker import AliasExpander


class TestTransliterationExpansion:
    """Contract tests for expand_transliterations method"""

    @pytest.fixture
    def expander(self):
        """Initialize AliasExpander for tests"""
        return AliasExpander(max_aliases=100)

    def test_basic_transliteration(self, expander):
        """Test Case 4.1: Basic transliteration (Cyrillic→Latin)"""
        # Arrange
        variants = ["Навальный", "А. Навальный", "Алексей Навальный"]

        # Act
        result = expander.expand_transliterations(variants)

        # Assert
        assert "navalny" in result, "Missing basic transliteration"
        assert "a. navalny" in result, "Missing transliteration with initials"
        assert "aleksey navalny" in result or "alexey navalny" in result, \
            "Missing full name transliteration"
        # All output should be ASCII (Latin)
        assert all(s.isascii() for s in result), "All transliterations should be ASCII/Latin"

    def test_phonetic_simplification(self, expander):
        """Test Case 4.2: Phonetic simplification (Юрий → Yuri not Iurii)"""
        # Arrange
        variants = ["Юрий", "Ю. Лужков"]

        # Act
        result = expander.expand_transliterations(variants)

        # Assert
        # Should use phonetic variant (yu/yuri), not ISO 9 (iu/iurii)
        assert any("yuri" in r or "yuriy" in r for r in result), \
            "Should use phonetic Yuri/Yuriy, not ISO Iurii"
        assert any("yu" in r.lower() for r in result), \
            "Should use phonetic 'yu' not ISO 'iu'"
        # ISO 9 forms should NOT appear
        assert not any("iu" in r.lower() and "yu" not in r.lower() for r in result), \
            "Should not use ISO 9 'iu' form"

    def test_mixed_script_handling(self, expander):
        """Test Case 4.3: Mixed script (skip or pass-through)"""
        # Arrange
        variants = ["John Smith", "Müller"]

        # Act
        result = expander.expand_transliterations(variants)

        # Assert
        # Should either skip (empty result) or pass through gracefully
        # Main requirement: no crashes
        assert isinstance(result, list), "Should return a list"
        # Accept either behavior: skip entirely or pass through
        # No strict assertion - just verify graceful handling
