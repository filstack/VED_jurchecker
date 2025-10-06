"""
Integration test: Log retention
Verifies that old telemetry logs are cleaned up based on LOG_RETENTION_DAYS
"""
import pytest
import os
from pathlib import Path
from datetime import datetime, timedelta
from jur_checker import JurChecker


def test_log_retention_cleanup_old_logs(tmp_path, monkeypatch):
    """
    Test: Old logs are deleted on startup
    - Create logs from 35 days ago, 20 days ago, and today
    - Set retention to 30 days
    - Start JurChecker
    - Verify only recent logs remain
    """
    os.chdir(tmp_path)

    # Set retention to 30 days
    monkeypatch.setenv("LOG_RETENTION_DAYS", "30")

    # Create .logs directory
    logs_dir = tmp_path / ".logs"
    logs_dir.mkdir()

    # Create test log files with different dates
    today = datetime.now()
    old_date = today - timedelta(days=35)
    recent_date = today - timedelta(days=20)

    old_log = logs_dir / f"matches-{old_date.strftime('%Y-%m-%d')}.jsonl"
    recent_log = logs_dir / f"matches-{recent_date.strftime('%Y-%m-%d')}.jsonl"
    today_log = logs_dir / f"matches-{today.strftime('%Y-%m-%d')}.jsonl"

    # Create dummy log files
    old_log.write_text('{"test": "old"}\n', encoding='utf-8')
    recent_log.write_text('{"test": "recent"}\n', encoding='utf-8')
    today_log.write_text('{"test": "today"}\n', encoding='utf-8')

    # Verify all files exist before cleanup
    assert old_log.exists()
    assert recent_log.exists()
    assert today_log.exists()

    # Create test CSV and build checker (triggers cleanup)
    test_csv = tmp_path / "test.csv"
    test_csv.write_text("id,name,type\ntest-1,Иванов Иван,иноагенты\n", encoding='utf-8')

    checker = JurChecker(csv_path=str(test_csv))

    # Verify old log was deleted
    assert not old_log.exists(), "35-day-old log should be deleted"

    # Verify recent logs remain
    assert recent_log.exists(), "20-day-old log should remain"
    assert today_log.exists(), "Today's log should remain"


def test_log_retention_custom_days(tmp_path, monkeypatch, caplog):
    """
    Test: Custom retention period via LOG_RETENTION_DAYS
    """
    import logging

    os.chdir(tmp_path)

    # Set retention to 10 days
    monkeypatch.setenv("LOG_RETENTION_DAYS", "10")

    logs_dir = tmp_path / ".logs"
    logs_dir.mkdir()

    # Create logs from 15 days ago and 5 days ago
    today = datetime.now()
    old_date = today - timedelta(days=15)
    recent_date = today - timedelta(days=5)

    old_log = logs_dir / f"matches-{old_date.strftime('%Y-%m-%d')}.jsonl"
    recent_log = logs_dir / f"matches-{recent_date.strftime('%Y-%m-%d')}.jsonl"

    old_log.write_text('{"test": "old"}\n', encoding='utf-8')
    recent_log.write_text('{"test": "recent"}\n', encoding='utf-8')

    # Build checker
    test_csv = tmp_path / "test.csv"
    test_csv.write_text("id,name,type\ntest-1,Иванов Иван,иноагенты\n", encoding='utf-8')

    with caplog.at_level(logging.INFO):
        checker = JurChecker(csv_path=str(test_csv))

    # Verify cleanup logged
    cleanup_logs = [r for r in caplog.records if "Cleaned up" in r.message and "telemetry" in r.message]
    assert len(cleanup_logs) > 0, "Cleanup should be logged"
    assert "retention: 10 days" in cleanup_logs[0].message

    # Verify old log deleted, recent remains
    assert not old_log.exists(), "15-day-old log should be deleted (retention=10)"
    assert recent_log.exists(), "5-day-old log should remain"


def test_log_retention_no_logs_dir(tmp_path, monkeypatch):
    """
    Test: Cleanup handles missing .logs directory gracefully
    """
    os.chdir(tmp_path)

    monkeypatch.setenv("LOG_RETENTION_DAYS", "30")

    # Don't create .logs directory
    logs_dir = tmp_path / ".logs"
    assert not logs_dir.exists()

    # Build checker (should not crash)
    test_csv = tmp_path / "test.csv"
    test_csv.write_text("id,name,type\ntest-1,Иванов Иван,иноагенты\n", encoding='utf-8')

    try:
        checker = JurChecker(csv_path=str(test_csv))
        # Should succeed without error
        assert True
    except Exception as e:
        pytest.fail(f"Cleanup should handle missing .logs directory: {e}")


def test_log_retention_malformed_filenames(tmp_path, monkeypatch, caplog):
    """
    Test: Cleanup skips malformed log filenames
    """
    import logging

    os.chdir(tmp_path)
    monkeypatch.setenv("LOG_RETENTION_DAYS", "30")

    logs_dir = tmp_path / ".logs"
    logs_dir.mkdir()

    # Create malformed log files
    bad_log1 = logs_dir / "matches-invalid-date.jsonl"
    bad_log2 = logs_dir / "not-a-match-log.jsonl"
    good_log = logs_dir / f"matches-{datetime.now().strftime('%Y-%m-%d')}.jsonl"

    bad_log1.write_text("{}\n", encoding='utf-8')
    bad_log2.write_text("{}\n", encoding='utf-8')
    good_log.write_text("{}\n", encoding='utf-8')

    # Build checker
    test_csv = tmp_path / "test.csv"
    test_csv.write_text("id,name,type\ntest-1,Иванов Иван,иноагенты\n", encoding='utf-8')

    with caplog.at_level(logging.WARNING):
        checker = JurChecker(csv_path=str(test_csv))

    # Verify malformed files were skipped (logged warning)
    # Note: malformed files should remain, not crash the system
    assert bad_log1.exists(), "Malformed log should be skipped, not deleted"
    assert good_log.exists(), "Valid log should remain"
