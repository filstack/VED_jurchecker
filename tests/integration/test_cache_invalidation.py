"""
Integration test for pickle cache invalidation.

Tests that automaton is rebuilt when CSV changes (hash mismatch).
Requirements: Performance requirement (cache invalidation)

This test MUST FAIL initially (TDD requirement).
"""
import pytest
import tempfile
import os
import time
from jur_checker import JurChecker


class TestCacheInvalidation:
    """Integration tests for pickle cache invalidation"""

    @pytest.fixture
    def temp_csv(self):
        """Create temporary CSV with test data"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("entity_name\n")
            f.write("Алексей Навальный\n")
            temp_path = f.name

        yield temp_path

        # Cleanup
        os.unlink(temp_path)
        pickle_path = temp_path.replace('.csv', '.pkl')
        if os.path.exists(pickle_path):
            os.unlink(pickle_path)

    def test_cache_invalidation_on_csv_change(self, temp_csv):
        """Test: Cache invalidated when CSV changes"""
        # Arrange: Build initial automaton
        checker1 = JurChecker(csv_path=temp_csv)
        pickle_path = checker1._get_cache_path()

        assert pickle_path.exists(), "Pickle should be created"

        # Get initial pickle modification time
        initial_mtime = pickle_path.stat().st_mtime

        # Wait to ensure different timestamp
        time.sleep(0.1)

        # Act: Modify CSV (add new entity)
        with open(temp_csv, 'a', encoding='utf-8') as f:
            f.write("Газпром\n")

        # Build new checker (should detect CSV change and rebuild)
        checker2 = JurChecker(csv_path=temp_csv)

        # Assert: Pickle should be rebuilt
        new_mtime = pickle_path.stat().st_mtime
        assert new_mtime > initial_mtime, \
            "Pickle should be rebuilt when CSV changes"

        # Assert: New entity should be detected
        text = "Газпром упоминался в документе"
        matches = checker2.find_raw_candidates(text)

        matched_entities = {match['entity_name'] for match in matches}
        assert "Газпром" in matched_entities, \
            "New entity from modified CSV should be detected"

    def test_cache_reused_when_csv_unchanged(self, temp_csv):
        """Test: Cache reused when CSV unchanged"""
        # Arrange: Build initial automaton
        checker1 = JurChecker(csv_path=temp_csv)
        pickle_path = checker1._get_cache_path()

        initial_mtime = pickle_path.stat().st_mtime

        # Wait to ensure different timestamp if rebuild occurs
        time.sleep(0.1)

        # Act: Load checker again without CSV changes
        checker2 = JurChecker(csv_path=temp_csv)

        # Assert: Pickle should NOT be rebuilt
        new_mtime = pickle_path.stat().st_mtime
        assert new_mtime == initial_mtime, \
            "Pickle should be reused when CSV is unchanged"

        # Assert: Both checkers should work identically
        text = "Алексей Навальный"
        matches1 = checker1.find_raw_candidates(text)
        matches2 = checker2.find_raw_candidates(text)

        assert len(matches1) == len(matches2), \
            "Cached and fresh automaton should produce same results"

    def test_pickle_deleted_forces_rebuild(self, temp_csv):
        """Test: Deleting pickle forces rebuild"""
        # Arrange: Build initial automaton
        checker1 = JurChecker(csv_path=temp_csv)
        pickle_path = checker1._get_cache_path()

        assert pickle_path.exists(), "Pickle should be created"

        # Act: Delete pickle file
        pickle_path.unlink()

        # Build new checker (should rebuild from CSV)
        checker2 = JurChecker(csv_path=temp_csv)

        # Assert: Pickle should be recreated
        assert pickle_path.exists(), \
            "Pickle should be recreated when deleted"

        # Assert: Automaton should work correctly
        text = "Алексей Навальный"
        matches = checker2.find_raw_candidates(text)

        assert len(matches) > 0, \
            "Rebuilt automaton should detect entities"
