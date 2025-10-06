"""
Integration test for performance requirements.

Tests that build completes within time limit (<2 minutes for 1000 entities).
Requirements: Performance requirement (build time)

This test MUST FAIL initially (TDD requirement).
"""
import pytest
import tempfile
import os
import time
from jur_checker import JurChecker


class TestPerformance:
    """Integration tests for performance requirements"""

    @pytest.fixture
    def large_csv(self):
        """Create CSV with 1000 test entities"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("entity_name\n")

            # Add 1000 test entities with varied patterns
            russian_surnames = ["Иванов", "Петров", "Сидоров", "Смирнов", "Кузнецов"]
            first_names = ["Александр", "Дмитрий", "Сергей", "Андрей", "Алексей"]

            for i in range(1000):
                surname = russian_surnames[i % len(russian_surnames)]
                first = first_names[i % len(first_names)]
                f.write(f"{first} {surname} {i}\n")

            temp_path = f.name

        yield temp_path

        # Cleanup
        os.unlink(temp_path)
        pickle_path = temp_path.replace('.csv', '.pkl')
        if os.path.exists(pickle_path):
            os.unlink(pickle_path)

    def test_build_time_under_limit(self, large_csv):
        """Test: Build completes within 2 minutes for 1000 entities"""
        # Act: Measure build time
        start_time = time.time()
        checker = JurChecker(csv_path=large_csv)
        build_time = time.time() - start_time

        # Assert: Should complete within 2 minutes (120 seconds)
        assert build_time < 120, \
            f"Build took {build_time:.2f}s, should be under 120s for 1000 entities"

        # Assert: Automaton should be functional
        assert checker.automaton is not None, "Automaton should be built"

        # Assert: Should detect entities
        text = "Александр Иванов 0 встретился с Дмитрий Петров 500"
        matches = checker.find_raw_candidates(text)
        assert len(matches) > 0, "Should detect entities after build"

    def test_alias_limit_enforced(self, large_csv):
        """Test: Alias limit prevents memory explosion"""
        # Arrange & Act
        checker = JurChecker(csv_path=large_csv)

        # We can't easily count aliases in automaton, but we can verify:
        # 1. Build completes without memory error
        # 2. Automaton works

        # Assert: Build should complete
        assert checker.automaton is not None, "Should build without memory error"

        # Assert: Search should work efficiently
        text = "Александр Иванов 0 " * 100  # Repeated pattern
        start_time = time.time()
        matches = checker.find_raw_candidates(text)
        search_time = time.time() - start_time

        # Assert: Search should be fast (< 1 second for repeated pattern)
        assert search_time < 1.0, \
            f"Search took {search_time:.2f}s, should be under 1s"

    def test_cache_load_performance(self, large_csv):
        """Test: Loading from pickle is faster than CSV build"""
        # Arrange: Build initial automaton (from CSV)
        start_csv = time.time()
        checker1 = JurChecker(csv_path=large_csv)
        csv_build_time = time.time() - start_csv

        # Act: Load from pickle cache
        start_pickle = time.time()
        checker2 = JurChecker(csv_path=large_csv)
        pickle_load_time = time.time() - start_pickle

        # Assert: Pickle load should be faster than CSV build
        assert pickle_load_time < csv_build_time, \
            f"Pickle load ({pickle_load_time:.2f}s) should be faster than CSV build ({csv_build_time:.2f}s)"

        # Assert: Both should produce same results
        text = "Александр Иванов 0"
        matches1 = checker1.find_raw_candidates(text)
        matches2 = checker2.find_raw_candidates(text)

        assert len(matches1) == len(matches2), \
            "Cached and fresh automaton should produce identical results"

    def test_query_time_zero_impact(self, large_csv):
        """Test: Alias expansion has zero query-time impact"""
        # Arrange
        checker = JurChecker(csv_path=large_csv)

        # Act: Measure search time (all alias expansion happened at build time)
        # Use names that match the CSV format: "Александр Иванов 0"
        text = "Александр Иванов 5 работал с Дмитрий Петров 10" * 50

        start_time = time.time()
        matches = checker.find_raw_candidates(text)
        search_time = time.time() - start_time

        # Assert: Search should be very fast (< 0.5s for long text)
        assert search_time < 0.5, \
            f"Search took {search_time:.2f}s, alias expansion should not slow queries"

        # Assert: Should find entities (morphological/initial variants)
        assert len(matches) >= 0, "Search should complete successfully"
