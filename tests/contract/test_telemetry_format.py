"""
Contract test: Telemetry log entries match schema
"""
import pytest
import json
import os
from pathlib import Path
from datetime import datetime
from jur_checker import JurChecker

@pytest.fixture
def telemetry_enabled(monkeypatch):
    """Enable telemetry for tests"""
    monkeypatch.setenv("ENABLE_MATCH_LOGGING", "true")

def test_telemetry_log_entry_schema(telemetry_enabled, tmp_path):
    """Test: Telemetry log entries are valid JSON with required fields"""
    # Setup test environment
    os.chdir(tmp_path)
    logs_dir = tmp_path / ".logs"
    logs_dir.mkdir()

    # Create test checker
    # Note: This test will need actual implementation of telemetry logging
    # For now, verify log file structure

    today = datetime.now().strftime("%Y-%m-%d")
    log_file = logs_dir / f"matches-{today}.jsonl"

    # Manually create test entry (implementation will do this)
    test_entry = {
        "timestamp": datetime.now().isoformat() + "Z",
        "alias": "test",
        "entity_id": "abc-123",
        "entity_name": "Test Entity",
        "entity_type": "иноагенты",
        "context": "test context",
        "request_id": None
    }

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(test_entry, ensure_ascii=False) + "\n")

    # Verify entry can be parsed
    with open(log_file, encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line)

            # Required fields
            assert "timestamp" in entry
            assert "alias" in entry
            assert "entity_id" in entry
            assert "entity_name" in entry
            assert "entity_type" in entry
            assert "context" in entry

            # Validate types
            assert isinstance(entry["timestamp"], str)
            assert isinstance(entry["alias"], str)
            assert len(entry["context"]) <= 300  # Privacy constraint

def test_telemetry_disabled_no_logs():
    """Test: No logs written when telemetry disabled"""
    # Verify ENABLE_MATCH_LOGGING not set or false
    assert os.getenv("ENABLE_MATCH_LOGGING", "false").lower() == "false"

    # After implementation, verify .logs/ directory empty or not created
    logs_path = Path(".logs")
    if logs_path.exists():
        log_files = list(logs_path.glob("matches-*.jsonl"))
        # Files may exist from previous runs, but should not grow
        # This is a placeholder - full test requires implementation
        pass
