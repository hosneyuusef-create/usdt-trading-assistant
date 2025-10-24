import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.backend.core.app import create_app
from src.backend.rfq.service import get_registry

RFQ_LOG = Path("logs/rfq_events.json")


@pytest.fixture(autouse=True)
def reset_registry():
    registry = get_registry()
    registry.clear()
    if RFQ_LOG.exists():
        RFQ_LOG.unlink()
    yield
    registry.clear()


def client() -> TestClient:
    return TestClient(create_app())


def future_timestamp(minutes: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def test_create_rfq_with_valid_data():
    c = client()
    payload = {
        "customer_id": "cust-100",
        "customer_telegram_id": 123456,
        "kyc_tier": "advanced",
        "rfq_type": "buy",
        "network": "TRC20",
        "amount": 5_000_000,
        "min_fill_amount": 1_000_000,
        "expires_at": future_timestamp(),
        "special_conditions": {
            "price_ceiling": 620000,
            "split_allowed": True,
            "specific_providers": ["provider-alpha", "provider-beta"],
            "min_fill_percentage": 50,
        },
    }

    response = c.post("/rfq", json=payload, headers={"X-Role": "customer", "X-User-Id": "tg-123"})
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "open"
    assert data["special_conditions"]["split_allowed"] is True
    assert set(data["special_conditions"]["specific_providers"]) == {"provider-alpha", "provider-beta"}


def test_create_rfq_exceeding_kyc_limit_fails():
    c = client()
    payload = {
        "customer_id": "cust-200",
        "kyc_tier": "basic",
        "rfq_type": "sell",
        "network": "BEP20",
        "amount": 5_000_000,  # > basic limit 1,000,000
        "expires_at": future_timestamp(),
    }
    response = c.post("/rfq", json=payload, headers={"X-Role": "customer", "X-User-Id": "tg-200"})
    assert response.status_code == 400
    assert "KYC" in response.text


def test_update_and_cancel_rfq_logs_event():
    c = client()
    create_payload = {
        "customer_id": "cust-201",
        "kyc_tier": "advanced",
        "rfq_type": "buy",
        "network": "ERC20",
        "amount": 3_000_000,
        "expires_at": future_timestamp(),
    }
    create_resp = c.post("/rfq", json=create_payload, headers={"X-Role": "operations", "X-User-Id": "ops-1"})
    rfq_id = create_resp.json()["rfq_id"]

    update_payload = {"amount": 4_000_000}
    update_resp = c.put(
        f"/rfq/{rfq_id}",
        json=update_payload,
        headers={"X-Role": "operations", "X-User-Id": "ops-1"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["amount"] == 4_000_000

    cancel_resp = c.post(
        f"/rfq/{rfq_id}/cancel",
        params={"reason": "customer_request"},
        headers={"X-Role": "admin", "X-User-Id": "admin-42"},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"
    assert RFQ_LOG.exists()
    events = [json.loads(line) for line in RFQ_LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(event["rfq_id"] == rfq_id and event["reason"] == "customer_request" for event in events)


def test_expired_rfq_status_changes_on_read():
    c = client()
    payload = {
        "customer_id": "cust-300",
        "kyc_tier": "advanced",
        "rfq_type": "sell",
        "network": "TRC20",
        "amount": 2_000_000,
        "expires_at": future_timestamp(),
    }
    resp = c.post("/rfq", json=payload, headers={"X-Role": "customer", "X-User-Id": "tg-300"})
    rfq_id = resp.json()["rfq_id"]

    # Force expiry for test
    registry = get_registry()
    record = registry._storage[rfq_id]  # type: ignore[attr-defined]
    record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    fetch_resp = c.get(f"/rfq/{rfq_id}", headers={"X-Role": "compliance", "X-User-Id": "comp-1"})
    assert fetch_resp.status_code == 200
    assert fetch_resp.json()["status"] == "expired"
