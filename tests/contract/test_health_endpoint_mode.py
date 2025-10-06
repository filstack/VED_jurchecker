"""
Contract test: /health endpoint returns alias_mode field
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_endpoint_includes_alias_mode():
    """Test: /health response includes alias_mode field"""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # Required field
    assert "status" in data
    assert data["status"] == "ok"

    # New optional field (backward compatible)
    assert "alias_mode" in data
    assert data["alias_mode"] in ["strict", "balanced", "aggressive"]

def test_health_endpoint_alias_mode_matches_env():
    """Test: alias_mode reflects environment variable"""
    import os
    expected_mode = os.getenv("ALIAS_STRICTNESS", "strict")

    response = client.get("/health")
    data = response.json()

    assert data["alias_mode"] == expected_mode
