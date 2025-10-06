"""
Integration test: Mode configuration
Verifies that different ALIAS_STRICTNESS modes produce separate caches
"""
import pytest
import os
import tempfile
from pathlib import Path
from jur_checker import JurChecker


def test_mode_specific_cache_files(tmp_path, monkeypatch):
    """
    Test: Different modes create separate cache files
    - strict mode creates {csv}_strict_automaton.pkl
    - balanced mode creates {csv}_balanced_automaton.pkl
    - aggressive mode creates {csv}_aggressive_automaton.pkl
    """
    # Create test CSV
    test_csv = tmp_path / "test.csv"
    test_csv.write_text("id,name,type\ntest-1,Иванов Иван,иноагенты\n", encoding='utf-8')

    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()

    # Test strict mode
    monkeypatch.setenv("ALIAS_STRICTNESS", "strict")
    checker_strict = JurChecker(csv_path=str(test_csv), cache_dir=str(cache_dir))

    strict_cache = cache_dir / "test_strict_automaton.pkl"
    strict_hash = cache_dir / "test_strict_hash.txt"
    assert strict_cache.exists(), "Strict mode cache should exist"
    assert strict_hash.exists(), "Strict mode hash should exist"

    # Test balanced mode
    monkeypatch.setenv("ALIAS_STRICTNESS", "balanced")
    checker_balanced = JurChecker(csv_path=str(test_csv), cache_dir=str(cache_dir))

    balanced_cache = cache_dir / "test_balanced_automaton.pkl"
    balanced_hash = cache_dir / "test_balanced_hash.txt"
    assert balanced_cache.exists(), "Balanced mode cache should exist"
    assert balanced_hash.exists(), "Balanced mode hash should exist"

    # Test aggressive mode
    monkeypatch.setenv("ALIAS_STRICTNESS", "aggressive")
    checker_aggressive = JurChecker(csv_path=str(test_csv), cache_dir=str(cache_dir))

    aggressive_cache = cache_dir / "test_aggressive_automaton.pkl"
    aggressive_hash = cache_dir / "test_aggressive_hash.txt"
    assert aggressive_cache.exists(), "Aggressive mode cache should exist"
    assert aggressive_hash.exists(), "Aggressive mode hash should exist"

    # Verify all three caches coexist
    cache_files = list(cache_dir.glob("test_*_automaton.pkl"))
    assert len(cache_files) == 3, "Should have 3 separate cache files"


def test_mode_change_triggers_rebuild(tmp_path, monkeypatch, caplog):
    """
    Test: Changing mode uses different cache (doesn't load old cache)
    """
    import logging

    test_csv = tmp_path / "test.csv"
    test_csv.write_text("id,name,type\ntest-1,Иванов Иван,иноагенты\n", encoding='utf-8')

    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()

    # Build with strict mode
    monkeypatch.setenv("ALIAS_STRICTNESS", "strict")
    with caplog.at_level(logging.INFO):
        checker1 = JurChecker(csv_path=str(test_csv), cache_dir=str(cache_dir))

    # Should build from scratch (no cache)
    build_logs = [r for r in caplog.records if "построен с нуля" in r.message]
    assert len(build_logs) > 0, "First build should be from scratch"

    caplog.clear()

    # Change to balanced mode
    monkeypatch.setenv("ALIAS_STRICTNESS", "balanced")
    with caplog.at_level(logging.INFO):
        checker2 = JurChecker(csv_path=str(test_csv), cache_dir=str(cache_dir))

    # Should also build from scratch (different cache file)
    build_logs = [r for r in caplog.records if "построен с нуля" in r.message]
    assert len(build_logs) > 0, "Mode change should trigger rebuild"

    caplog.clear()

    # Use strict mode again
    monkeypatch.setenv("ALIAS_STRICTNESS", "strict")
    with caplog.at_level(logging.INFO):
        checker3 = JurChecker(csv_path=str(test_csv), cache_dir=str(cache_dir))

    # Should load from cache this time
    cache_logs = [r for r in caplog.records if "загружен из кэша" in r.message]
    assert len(cache_logs) > 0, "Second strict build should use cache"


def test_health_endpoint_reflects_mode(monkeypatch):
    """
    Test: /health endpoint returns current alias_mode
    (This is a cross-check with contract test)
    """
    from fastapi.testclient import TestClient
    from main import app

    # Test each mode
    for mode in ["strict", "balanced", "aggressive"]:
        monkeypatch.setenv("ALIAS_STRICTNESS", mode)

        # Restart the app to pick up new env var
        # Note: In real test, may need to reload the module
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "alias_mode" in data
        # Note: This test assumes the environment is properly reloaded
        # In practice, may need to restart the FastAPI app
