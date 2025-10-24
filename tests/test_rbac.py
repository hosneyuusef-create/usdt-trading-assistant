import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.backend.core.app import create_app
from src.backend.provider.service import get_registry

AUDIT_LOG = Path("logs/access_audit.json")


def _client():
    return TestClient(create_app())


def test_rbac_enforces_roles_and_logs_access():
    registry = get_registry()
    registry.clear()
    if AUDIT_LOG.exists():
        AUDIT_LOG.unlink()

    client = _client()
    payload = {
        "telegram_id": 5555,
        "display_name": "RBAC Test Provider",
        "score": 82.0,
        "collateral_in_rial": 220_000_000,
        "is_active": True,
    }

    # Missing role header -> 401
    response = client.post("/provider/register", json=payload)
    assert response.status_code == 401

    # Role without permission -> 403
    response = client.post(
        "/provider/register",
        json=payload,
        headers={"X-Role": "customer", "X-User-Id": "user-100"},
    )
    assert response.status_code == 403

    # Allowed role -> 201
    response = client.post(
        "/provider/register",
        json=payload,
        headers={"X-Role": "admin", "X-User-Id": "admin-1"},
    )
    assert response.status_code == 201

    # Operations role can view eligible list
    response = client.get(
        "/provider/eligible",
        headers={"X-Role": "operations", "X-User-Id": "ops-1"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    assert AUDIT_LOG.exists()
    entries = [json.loads(line) for line in AUDIT_LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
    reasons = [entry.get("reason") for entry in entries]

    assert "missing_role_header" in reasons
    assert "forbidden" in reasons

    successes = [entry for entry in entries if entry["success"]]
    assert any(entry["role"] == "admin" and entry["action"] == "provider:register" for entry in successes)
    assert any(entry["role"] == "operations" and entry["action"] == "provider:view" for entry in successes)

    registry.clear()
