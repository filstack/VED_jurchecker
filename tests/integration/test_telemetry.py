"""
Integration test: Telemetry workflow
Verifies that match telemetry is logged to .jsonl files when enabled
"""
import pytest
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime
from jur_checker import JurChecker


def test_telemetry_disabled_by_default(tmp_path, monkeypatch):
    """
    Test: Telemetry disabled by default (no logs written)
    """
    # Ensure ENABLE_MATCH_LOGGING is false
    monkeypatch.setenv("ENABLE_MATCH_LOGGING", "false")

    # Change to temp directory
    os.chdir(tmp_path)

    # Create test CSV
    test_csv = tmp_path / "test.csv"
    test_csv.write_text("id,name,type\ntest-1,Иванов Иван,иноагенты\n", encoding='utf-8')

    # Build checker
    checker = JurChecker(csv_path=str(test_csv))

    # Find matches
    checker.find_raw_candidates("Текст с упоминанием Иванов Иван в контексте.")

    # Verify .logs directory either doesn't exist or has no jsonl files
    logs_dir = tmp_path / ".logs"
    if logs_dir.exists():
        jsonl_files = list(logs_dir.glob("matches-*.jsonl"))
        assert len(jsonl_files) == 0, "Telemetry logs should not be created when disabled"


def test_telemetry_enabled_workflow(tmp_path, monkeypatch):
    """
    Test: Complete telemetry workflow when enabled
    - Enable telemetry via environment variable
    - Find matches
    - Verify JSON logs written to .logs/matches-{date}.jsonl
    - Verify JSON schema
    """
    # Enable telemetry
    monkeypatch.setenv("ENABLE_MATCH_LOGGING", "true")

    # Change to temp directory
    os.chdir(tmp_path)

    # Create .logs directory
    logs_dir = tmp_path / ".logs"
    logs_dir.mkdir()

    # Create test CSV
    test_csv = tmp_path / "test.csv"
    test_csv.write_text("id,name,type\ntest-1,Иванов Иван,иноагенты\n", encoding='utf-8')

    # Build checker
    checker = JurChecker(csv_path=str(test_csv))

    # Find matches
    candidates = checker.find_raw_candidates("Текст с упоминанием Иванов Иван в контексте.")
    assert len(candidates) > 0, "Should find at least one match"

    # Verify telemetry log file exists
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = logs_dir / f"matches-{today}.jsonl"
    assert log_file.exists(), f"Telemetry log {log_file} should exist"

    # Verify JSON entries
    with open(log_file, encoding='utf-8') as f:
        lines = f.readlines()
        assert len(lines) > 0, "Should have at least one telemetry entry"

        for line in lines:
            entry = json.loads(line)

            # Verify required fields
            assert "timestamp" in entry
            assert "alias" in entry
            assert "entity_id" in entry
            assert "entity_name" in entry
            assert "entity_type" in entry
            assert "context" in entry

            # Verify types
            assert isinstance(entry["timestamp"], str)
            assert isinstance(entry["alias"], str)
            assert isinstance(entry["entity_id"], str)

            # Verify privacy constraint (context <= 300 chars)
            assert len(entry["context"]) <= 300


def test_telemetry_multiple_matches(tmp_path, monkeypatch):
    """
    Test: Telemetry logs all matches in a single request
    """
    monkeypatch.setenv("ENABLE_MATCH_LOGGING", "true")
    os.chdir(tmp_path)

    logs_dir = tmp_path / ".logs"
    logs_dir.mkdir()

    # Create test CSV with multiple entities
    test_csv = tmp_path / "test.csv"
    test_csv.write_text(
        "id,name,type\n"
        "test-1,Иванов Иван,иноагенты\n"
        "test-2,Петров Петр,иноагенты\n",
        encoding='utf-8'
    )

    checker = JurChecker(csv_path=str(test_csv))

    # Text with multiple matches
    text = "Иванов Иван и Петров Петр были на встрече."
    candidates = checker.find_raw_candidates(text)

    # Verify telemetry entries match candidates
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = logs_dir / f"matches-{today}.jsonl"

    with open(log_file, encoding='utf-8') as f:
        entries = [json.loads(line) for line in f]
        assert len(entries) == len(candidates), "Should log one entry per match"
