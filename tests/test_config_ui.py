"""
Test suite for Configuration UI (Stage 22 - M22)
Tests M22-E2E-1 and M22-E2E-2
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import shutil
import json

from src.backend.core.app import create_app
from src.backend.config_ui.service import (
    CONFIG_STORE_DIR,
    CURRENT_CONFIG_FILE,
    CONFIG_HISTORY_FILE,
)

# Test headers for RBAC
ADMIN_HEADERS = {"X-Role": "admin", "X-User-Id": "test_admin"}


@pytest.fixture(scope="module")
def client():
    """Create test client"""
    app = create_app()
    return TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def clean_config_store():
    """Clean config store before each test"""
    if CONFIG_STORE_DIR.exists():
        shutil.rmtree(CONFIG_STORE_DIR)
    CONFIG_STORE_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Cleanup after test
    if CONFIG_STORE_DIR.exists():
        shutil.rmtree(CONFIG_STORE_DIR)


def test_get_current_configuration_default(client):
    """
    M22-E2E-1a: Test getting default configuration on first run
    """
    response = client.get("/config/current", headers=ADMIN_HEADERS)
    assert response.status_code == 200

    data = response.json()
    assert data["version"] == 1
    assert data["created_by"] == "system"
    assert data["is_latest"] == True

    # Check default configuration values
    config = data["configuration"]
    assert config["bidding_deadline_minutes"] == 10
    assert config["min_valid_quotes"] == 2
    assert config["settlement_order"] == "fiat_first"
    assert config["min_provider_score"] == 60
    assert "TRC20" in config["allowed_networks"]


def test_update_configuration(client):
    """
    M22-E2E-1b: Test updating configuration without redeploy
    """
    # Get initial config
    response = client.get("/config/current", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    initial_version = response.json()["version"]

    # Update configuration
    update_request = {
        "configuration": {
            "bidding_deadline_minutes": 15,  # Changed from 10
            "min_valid_quotes": 3,  # Changed from 2
            "allow_deadline_extension": True,
            "settlement_order": "crypto_first",  # Changed from fiat_first
            "fiat_settlement_timeout_minutes": 20,
            "crypto_settlement_timeout_minutes": 15,
            "min_blockchain_confirmations": 2,
            "allowed_networks": ["TRC20", "BEP20"],
            "min_provider_score": 70,  # Changed from 60
            "min_provider_collateral": 1000,
            "scoring_weights": {
                "success_rate": 0.4,
                "on_time_settlement": 0.3,
                "dispute_ratio": 0.2,
                "manual_alerts": 0.1
            },
            "message_template_version": "M19-2025-10-24",
            "dispute_evidence_deadline_minutes": 30,
            "dispute_resolution_deadline_hours": 4,
            "notification_latency_warning_ms": 5000,
            "notification_failure_warning_rate": 0.05
        },
        "change_reason": "Testing configuration update for M22-E2E-1",
        "created_by": "test_admin"
    }

    response = client.post("/config/update", json=update_request, headers=ADMIN_HEADERS)
    assert response.status_code == 200

    data = response.json()
    assert data["version"] == initial_version + 1
    assert data["created_by"] == "test_admin"
    assert data["is_latest"] == True

    # Verify updated values
    config = data["configuration"]
    assert config["bidding_deadline_minutes"] == 15
    assert config["min_valid_quotes"] == 3
    assert config["settlement_order"] == "crypto_first"
    assert config["min_provider_score"] == 70

    # Verify changes are persisted (read again)
    response = client.get("/config/current", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    current_config = response.json()
    assert current_config["version"] == initial_version + 1
    assert current_config["configuration"]["bidding_deadline_minutes"] == 15


def test_configuration_validation(client):
    """
    M22-E2E-1c: Test configuration validation (invalid scoring weights)
    """
    # Scoring weights that don't sum to 1.0
    invalid_request = {
        "configuration": {
            "bidding_deadline_minutes": 10,
            "min_valid_quotes": 2,
            "allow_deadline_extension": True,
            "settlement_order": "fiat_first",
            "fiat_settlement_timeout_minutes": 15,
            "crypto_settlement_timeout_minutes": 15,
            "min_blockchain_confirmations": 1,
            "allowed_networks": ["TRC20"],
            "min_provider_score": 60,
            "min_provider_collateral": 0,
            "scoring_weights": {
                "success_rate": 0.5,  # Sum = 1.1 (invalid!)
                "on_time_settlement": 0.3,
                "dispute_ratio": 0.2,
                "manual_alerts": 0.1
            },
            "message_template_version": "M19-2025-10-24",
            "dispute_evidence_deadline_minutes": 30,
            "dispute_resolution_deadline_hours": 4,
            "notification_latency_warning_ms": 5000,
            "notification_failure_warning_rate": 0.05
        },
        "change_reason": "Testing invalid configuration",
        "created_by": "test_admin"
    }

    response = client.post("/config/update", json=invalid_request, headers=ADMIN_HEADERS)
    assert response.status_code == 400
    assert "Invalid configuration" in response.json()["detail"]["message"]
    assert "Scoring weights must sum to 1.0" in response.json()["detail"]["errors"][0]


def test_configuration_history(client):
    """
    M22-E2E-2a: Test configuration history tracking
    """
    # Create multiple versions
    for i in range(3):
        update_request = {
            "configuration": {
                "bidding_deadline_minutes": 10 + i * 5,
                "min_valid_quotes": 2,
                "allow_deadline_extension": True,
                "settlement_order": "fiat_first",
                "fiat_settlement_timeout_minutes": 15,
                "crypto_settlement_timeout_minutes": 15,
                "min_blockchain_confirmations": 1,
                "allowed_networks": ["TRC20"],
                "min_provider_score": 60,
                "min_provider_collateral": 0,
                "scoring_weights": {
                    "success_rate": 0.4,
                    "on_time_settlement": 0.3,
                    "dispute_ratio": 0.2,
                    "manual_alerts": 0.1
                },
                "message_template_version": "M19-2025-10-24",
                "dispute_evidence_deadline_minutes": 30,
                "dispute_resolution_deadline_hours": 4,
                "notification_latency_warning_ms": 5000,
                "notification_failure_warning_rate": 0.05
            },
            "change_reason": f"Test update {i+1}",
            "created_by": "test_admin"
        }
        response = client.post("/config/update", json=update_request, headers=ADMIN_HEADERS)
        assert response.status_code == 200

    # Get history
    response = client.get("/config/history", headers=ADMIN_HEADERS)
    assert response.status_code == 200

    data = response.json()
    assert data["total_versions"] == 4  # 1 initial + 3 updates
    assert data["current_version"] == 4
    assert len(data["history"]) == 4

    # Verify history entries
    history = data["history"]
    assert history[0]["version"] == 1
    assert history[0]["created_by"] == "system"
    assert history[1]["version"] == 2
    assert history[1]["change_reason"] == "Test update 1"
    assert all("rollback_token" in entry for entry in history)


def test_rollback_configuration(client):
    """
    M22-E2E-2b: Test configuration rollback to previous version
    """
    # Create initial configuration
    response = client.get("/config/current", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    initial_config = response.json()
    initial_version = initial_config["version"]

    # Update to version 2
    update_v2 = {
        "configuration": {
            "bidding_deadline_minutes": 15,
            "min_valid_quotes": 3,
            "allow_deadline_extension": True,
            "settlement_order": "fiat_first",
            "fiat_settlement_timeout_minutes": 15,
            "crypto_settlement_timeout_minutes": 15,
            "min_blockchain_confirmations": 1,
            "allowed_networks": ["TRC20"],
            "min_provider_score": 60,
            "min_provider_collateral": 0,
            "scoring_weights": {
                "success_rate": 0.4,
                "on_time_settlement": 0.3,
                "dispute_ratio": 0.2,
                "manual_alerts": 0.1
            },
            "message_template_version": "M19-2025-10-24",
            "dispute_evidence_deadline_minutes": 30,
            "dispute_resolution_deadline_hours": 4,
            "notification_latency_warning_ms": 5000,
            "notification_failure_warning_rate": 0.05
        },
        "change_reason": "Update to v2",
        "created_by": "test_admin"
    }
    response = client.post("/config/update", json=update_v2, headers=ADMIN_HEADERS)
    assert response.status_code == 200
    v2_data = response.json()
    assert v2_data["version"] == 2

    # Update to version 3
    update_v3 = {
        "configuration": {
            "bidding_deadline_minutes": 20,
            "min_valid_quotes": 4,
            "allow_deadline_extension": True,
            "settlement_order": "crypto_first",
            "fiat_settlement_timeout_minutes": 15,
            "crypto_settlement_timeout_minutes": 15,
            "min_blockchain_confirmations": 1,
            "allowed_networks": ["TRC20"],
            "min_provider_score": 60,
            "min_provider_collateral": 0,
            "scoring_weights": {
                "success_rate": 0.4,
                "on_time_settlement": 0.3,
                "dispute_ratio": 0.2,
                "manual_alerts": 0.1
            },
            "message_template_version": "M19-2025-10-24",
            "dispute_evidence_deadline_minutes": 30,
            "dispute_resolution_deadline_hours": 4,
            "notification_latency_warning_ms": 5000,
            "notification_failure_warning_rate": 0.05
        },
        "change_reason": "Update to v3",
        "created_by": "test_admin"
    }
    response = client.post("/config/update", json=update_v3, headers=ADMIN_HEADERS)
    assert response.status_code == 200
    v3_data = response.json()
    assert v3_data["version"] == 3

    # Get rollback token for version 2
    response = client.get("/config/history", headers=ADMIN_HEADERS)
    history = response.json()["history"]
    v2_token = next(entry["rollback_token"] for entry in history if entry["version"] == 2)

    # Rollback to version 2
    rollback_request = {
        "target_version": 2,
        "rollback_token": v2_token,
        "rollback_by": "test_admin",
        "rollback_reason": "Testing rollback for M22-E2E-2"
    }
    response = client.post("/config/rollback", json=rollback_request, headers=ADMIN_HEADERS)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] == True
    assert data["rolled_back_from"] == 3
    assert data["rolled_back_to"] == 2
    assert data["new_version"] == 4  # Rollback creates new version

    # Verify current configuration matches v2
    response = client.get("/config/current", headers=ADMIN_HEADERS)
    current = response.json()
    assert current["version"] == 4
    assert current["configuration"]["bidding_deadline_minutes"] == 15  # v2 value
    assert current["configuration"]["min_valid_quotes"] == 3  # v2 value
    assert current["configuration"]["settlement_order"] == "fiat_first"  # v2 value


def test_rollback_with_invalid_token(client):
    """
    M22-E2E-2c: Test rollback fails with invalid token
    """
    # Get current config
    response = client.get("/config/current", headers=ADMIN_HEADERS)
    assert response.status_code == 200

    # Attempt rollback with invalid token
    rollback_request = {
        "target_version": 1,
        "rollback_token": "invalid_token_12345",
        "rollback_by": "test_admin",
        "rollback_reason": "Testing invalid rollback"
    }
    response = client.post("/config/rollback", json=rollback_request, headers=ADMIN_HEADERS)
    assert response.status_code == 400
    assert "Invalid rollback token" in response.json()["detail"]


def test_rollback_to_nonexistent_version(client):
    """
    M22-E2E-2d: Test rollback fails for nonexistent version
    """
    rollback_request = {
        "target_version": 999,
        "rollback_token": "any_token",
        "rollback_by": "test_admin",
        "rollback_reason": "Testing nonexistent version rollback"
    }
    response = client.post("/config/rollback", json=rollback_request, headers=ADMIN_HEADERS)
    assert response.status_code == 400
    assert "Version 999 not found" in response.json()["detail"]


def test_config_event_logging(client):
    """
    M22-E2E-1d: Test configuration events are logged
    """
    # Perform update
    update_request = {
        "configuration": {
            "bidding_deadline_minutes": 12,
            "min_valid_quotes": 2,
            "allow_deadline_extension": True,
            "settlement_order": "fiat_first",
            "fiat_settlement_timeout_minutes": 15,
            "crypto_settlement_timeout_minutes": 15,
            "min_blockchain_confirmations": 1,
            "allowed_networks": ["TRC20"],
            "min_provider_score": 60,
            "min_provider_collateral": 0,
            "scoring_weights": {
                "success_rate": 0.4,
                "on_time_settlement": 0.3,
                "dispute_ratio": 0.2,
                "manual_alerts": 0.1
            },
            "message_template_version": "M19-2025-10-24",
            "dispute_evidence_deadline_minutes": 30,
            "dispute_resolution_deadline_hours": 4,
            "notification_latency_warning_ms": 5000,
            "notification_failure_warning_rate": 0.05
        },
        "change_reason": "Test logging",
        "created_by": "test_admin"
    }
    response = client.post("/config/update", json=update_request, headers=ADMIN_HEADERS)
    assert response.status_code == 200

    # Check logs/config_events.json exists
    log_file = Path("logs/config_events.json")
    assert log_file.exists()

    # Read and verify log content
    with open(log_file, "r") as f:
        lines = f.readlines()
        assert len(lines) >= 1

        # Parse last event
        last_event = json.loads(lines[-1])
        assert last_event["event_type"] == "config_update"
        assert last_event["version"] == 2
        assert last_event["created_by"] == "test_admin"
        assert last_event["change_reason"] == "Test logging"
        assert "config_hash" in last_event
