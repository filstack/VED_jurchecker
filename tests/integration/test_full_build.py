"""
Integration test for full dictionary build with alias expansion.

Tests the complete pipeline: CSV → aliases → automaton → pickle cache.
Requirements: FR-019, FR-020, FR-021

This test MUST FAIL initially (TDD requirement).
"""
import pytest
import tempfile
import os
from pathlib import Path
from jur_checker import JurChecker


class TestFullBuild:
    """Integration tests for full dictionary build process"""

    @pytest.fixture
    def temp_csv(self):
        """Create temporary CSV with test data"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("entity_name\n")
            f.write("Алексей Навальный\n")
            f.write("Газпром\n")
            f.write("John Smith\n")
            temp_path = f.name

        yield temp_path

        # Cleanup
        os.unlink(temp_path)
        # Cleanup pickle if exists
        pickle_path = temp_path.replace('.csv', '.pkl')
        if os.path.exists(pickle_path):
            os.unlink(pickle_path)

    def test_build_with_alias_expansion(self, temp_csv):
        """Test: Full build pipeline with alias expansion"""
        # Arrange & Act
        checker = JurChecker(csv_path=temp_csv)

        # Assert: Automaton should be built
        assert checker.automaton is not None, "Automaton should be built"

        # Assert: Should detect original names
        text = "Алексей Навальный работал в Газпроме с John Smith"
        matches = checker.find_raw_candidates(text)

        assert len(matches) > 0, "Should find at least one entity"

        # Extract matched entity names
        matched_entities = {match['entity_name'] for match in matches}

        assert "Алексей Навальный" in matched_entities, "Should detect original Russian name"
        assert "Газпром" in matched_entities, "Should detect organization name"
        assert "John Smith" in matched_entities, "Should detect foreign name"

    def test_morphological_variant_detection(self, temp_csv):
        """Test: Detect morphological case variants"""
        # Arrange
        checker = JurChecker(csv_path=temp_csv)

        # Act: Search with genitive case
        text = "Дело Навального слушали в суде"
        matches = checker.find_raw_candidates(text)

        # Assert: Should match "Навального" (genitive) to "Алексей Навальный"
        assert len(matches) > 0, "Should detect morphological variant"
        matched_entities = {match['entity_name'] for match in matches}
        assert "Алексей Навальный" in matched_entities, \
            "Should match genitive 'Навального' to base entity"

    def test_transliteration_variant_detection(self, temp_csv):
        """Test: Detect transliterated variants"""
        # Arrange
        checker = JurChecker(csv_path=temp_csv)

        # Act: Search with transliterated name
        text = "Navalny was mentioned in the article about Gazprom"
        matches = checker.find_raw_candidates(text)

        # Assert: Should match transliterations
        assert len(matches) > 0, "Should detect transliterated variants"
        matched_entities = {match['entity_name'] for match in matches}

        # Should match transliterated forms back to original entities
        assert "Алексей Навальный" in matched_entities or "Газпром" in matched_entities, \
            "Should match transliterations to original entities"

    def test_initial_variant_detection(self, temp_csv):
        """Test: Detect initial variants"""
        # Arrange
        checker = JurChecker(csv_path=temp_csv)

        # Act: Search with initials
        text = "А. Навальный и А.А. Навальный упоминались в документе"
        matches = checker.find_raw_candidates(text)

        # Assert: Should match initial variants
        assert len(matches) > 0, "Should detect initial variants"
        matched_entities = {match['entity_name'] for match in matches}
        assert "Алексей Навальный" in matched_entities, \
            "Should match initials to full name"

    def test_pickle_cache_created(self, temp_csv):
        """Test: Pickle cache is created after build"""
        # Arrange & Act
        checker = JurChecker(csv_path=temp_csv)

        # Assert: Pickle file should be created in .cache/ directory
        from pathlib import Path
        cache_path = checker._get_cache_path()
        assert cache_path.exists(), "Pickle cache should be created"

        # Assert: Pickle should be loadable
        checker2 = JurChecker(csv_path=temp_csv)
        assert checker2.automaton is not None, "Should load from pickle cache"
