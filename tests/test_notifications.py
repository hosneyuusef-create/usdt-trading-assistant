import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.backend.core.app import create_app
from src.backend.provider.service import get_registry as get_provider_registry
from src.backend.rfq.service import get_registry as get_rfq_registry

QUOTE_LOG = Path("logs/quote_events.json")
NOTIFICATION_LOG = Path("logs/notification_events.json")


@pytest.fixture(autouse=True)
def reset_state():
    get_provider_registry().clear()
    get_rfq_registry().clear()
    if QUOTE_LOG.exists():
        QUOTE_LOG.unlink()
    if NOTIFICATION_LOG.exists():
        NOTIFICATION_LOG.unlink()
    yield
    get_provider_registry().clear()
    get_rfq_registry().clear()
    if QUOTE_LOG.exists():
        QUOTE_LOG.unlink()
    if NOTIFICATION_LOG.exists():
        NOTIFICATION_LOG.unlink()


def app_client() -> TestClient:
    return TestClient(create_app())


def create_provider(client: TestClient, telegram_id: int, score: float = 85.0, collateral: int = 250_000_000):
    payload = {
        "telegram_id": telegram_id,
        "display_name": f"Provider {telegram_id}",
        "score": score,
        "collateral_in_rial": collateral,
        "is_active": True,
    }
    client.post(
        "/provider/register",
        json=payload,
        headers={"X-Role": "admin", "X-User-Id": "admin-ops"},
    )


def create_rfq(client: TestClient, amount: float = 2_000_000) -> str:
    payload = {
        "customer_id": "cust-stage14",
        "kyc_tier": "advanced",
        "rfq_type": "buy",
        "network": "TRC20",
        "amount": amount,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
    }
    response = client.post(
        "/rfq",
        json=payload,
        headers={"X-Role": "operations", "X-User-Id": "ops"},
    )
    return response.json()["rfq_id"]


def test_broadcast_to_eligible_providers_logs_event():
    client = app_client()
    create_provider(client, 6001)
    create_provider(client, 6002)
    rfq_id = create_rfq(client)

    resp = client.post(
        f"/notifications/rfq/{rfq_id}/broadcast",
        headers={"X-Role": "operations", "X-User-Id": "ops", "X-Trace-ID": "trace-123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["recipients"] == 2
    assert NOTIFICATION_LOG.exists()


def test_quote_submission_accepts_two_providers():
    client = app_client()
    create_provider(client, 7001)
    create_provider(client, 7002)
    rfq_id = create_rfq(client, amount=5_000_000)

    for provider_id in (7001, 7002):
        resp = client.post(
            "/notifications/quotes",
            json={
                "rfq_id": rfq_id,
                "provider_telegram_id": provider_id,
                "unit_price": 615000,
                "capacity": 2_000_000,
            },
            headers={"X-Role": "provider", "X-User-Id": f"provider-{provider_id}"},
        )
        assert resp.status_code == 200
    quotes = client.get(
        "/notifications/quotes",
        headers={"X-Role": "operations", "X-User-Id": "ops"},
    ).json()
    assert len(quotes) == 2


def test_late_quote_rejected_and_logged():
    client = app_client()
    create_provider(client, 7101)
    rfq_id = create_rfq(client, amount=1_000_000)
    # Expire the RFQ
    registry = get_rfq_registry()
    registry._storage[rfq_id].expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)  # type: ignore[attr-defined]

    resp = client.post(
        "/notifications/quotes",
        json={
            "rfq_id": rfq_id,
            "provider_telegram_id": 7101,
            "unit_price": 620000,
            "capacity": 500_000,
        },
        headers={"X-Role": "provider", "X-User-Id": "provider-7101"},
    )
    assert resp.status_code == 400
    assert "rfq_expired" in resp.text
    assert QUOTE_LOG.exists()
    events = [json.loads(line) for line in QUOTE_LOG.read_text(encoding="utf-8").splitlines()]
    assert any(event["accepted"] is False and event["reason"] == "rfq_expired" for event in events)


def test_rate_limit_blocks_consecutive_quotes():
    client = app_client()
    create_provider(client, 7201)
    rfq_id = create_rfq(client, amount=3_000_000)

    first = client.post(
        "/notifications/quotes",
        json={
            "rfq_id": rfq_id,
            "provider_telegram_id": 7201,
            "unit_price": 615000,
            "capacity": 1_000_000,
        },
        headers={"X-Role": "provider", "X-User-Id": "provider-7201"},
    )
    assert first.status_code == 200

    second = client.post(
        "/notifications/quotes",
        json={
            "rfq_id": rfq_id,
            "provider_telegram_id": 7201,
            "unit_price": 615100,
            "capacity": 500_000,
        },
        headers={"X-Role": "provider", "X-User-Id": "provider-7201"},
    )
    assert second.status_code == 400
    assert "rate_limited" in second.text
