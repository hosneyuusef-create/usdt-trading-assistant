import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.backend.core.app import create_app
from src.backend.provider.service import get_registry as get_provider_registry
from src.backend.rfq.service import get_registry as get_rfq_registry
from src.backend.notifications.service import get_quote_registry
from src.backend.settlement.service import get_registry as get_settlement_registry

DISPUTE_LOG = Path("logs/dispute_events.json")
SETTLEMENT_LOG = Path("logs/settlement_events.json")


@pytest.fixture(autouse=True)
def reset_state():
    get_provider_registry().clear()
    get_rfq_registry().clear()
    quote_registry = get_quote_registry()
    quote_registry._quotes.clear()  # type: ignore[attr-defined]
    quote_registry._submission_times.clear()  # type: ignore[attr-defined]
    get_settlement_registry()._storage.clear()  # type: ignore[attr-defined]
    for path in (DISPUTE_LOG, SETTLEMENT_LOG):
        if path.exists():
            path.unlink()
    yield
    get_provider_registry().clear()
    get_rfq_registry().clear()
    quote_registry._quotes.clear()  # type: ignore[attr-defined]
    quote_registry._submission_times.clear()  # type: ignore[attr-defined]
    get_settlement_registry()._storage.clear()  # type: ignore[attr-defined]
    for path in (DISPUTE_LOG, SETTLEMENT_LOG):
        if path.exists():
            path.unlink()


def client() -> TestClient:
    return TestClient(create_app())


def create_provider(client: TestClient, telegram_id: int):
    response = client.post(
        "/provider/register",
        json={
            "telegram_id": telegram_id,
            "display_name": f"Provider {telegram_id}",
            "score": 85,
            "collateral_in_rial": 250_000_000,
            "is_active": True,
        },
        headers={"X-Role": "admin", "X-User-Id": "admin-settlement"},
    )
    assert response.status_code == 201


def create_rfq(client: TestClient, amount: float):
    payload = {
        "customer_id": "cust-settlement",
        "kyc_tier": "advanced",
        "rfq_type": "buy",
        "network": "TRC20",
        "amount": amount,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
        "special_conditions": {"split_allowed": True},
    }
    response = client.post(
        "/rfq",
        json=payload,
        headers={"X-Role": "operations", "X-User-Id": "ops-settlement"},
    )
    assert response.status_code == 201
    return response.json()["rfq_id"]


def submit_quote(client: TestClient, rfq_id: str, provider_id: int, unit_price: float, capacity: float):
    resp = client.post(
        "/notifications/quotes",
        json={
            "rfq_id": rfq_id,
            "provider_telegram_id": provider_id,
            "unit_price": unit_price,
            "capacity": capacity,
        },
        headers={"X-Role": "provider", "X-User-Id": f"provider-{provider_id}"},
    )
    assert resp.status_code == 200
    return resp.json()["quote_id"]


def award(client: TestClient, rfq_id: str):
    resp = client.post(
        f"/award/{rfq_id}/auto",
        headers={"X-Role": "operations", "X-User-Id": "ops-settlement"},
    )
    assert resp.status_code == 200
    return resp.json()


def start_settlement(client: TestClient, award_result: dict):
    resp = client.post(
        "/settlement/start",
        json=award_result,
        headers={"X-Role": "operations", "X-User-Id": "ops-settlement"},
    )
    assert resp.status_code == 200
    return resp.json()


def submit_evidence(client: TestClient, settlement_id: str, leg_id: str):
    payload = {
        "evidence": {
            "hash": "a" * 32,
            "issuer": "Bank Example",
            "payer": "Customer",
            "payee": "Provider",
            "amounts": {"fiat": 2_000_000, "usdt": 2_000},
            "txId": "TX123456789",
            "network": "TRC20",
            "claimedConfirmations": 12,
            "file_name": "receipt.pdf",
            "file_size_mb": 1.2,
        }
    }
    response = client.post(
        f"/settlement/{settlement_id}/legs/{leg_id}/evidence",
        json=payload,
        headers={"X-Role": "provider", "X-User-Id": "provider-evidence"},
    )
    assert response.status_code == 200
    return response.json()


def verify_leg(client: TestClient, settlement_id: str, leg_id: str, verified: bool, reason: str | None = None):
    response = client.post(
        f"/settlement/{settlement_id}/legs/{leg_id}/verify",
        json={"verified": verified, "reason": reason},
        headers={"X-Role": "operations", "X-User-Id": "ops-verify"},
    )
    assert response.status_code == 200
    return response.json()


def test_settlement_flow_happy_path():
    c = client()
    create_provider(c, 9001)
    create_provider(c, 9002)
    rfq_id = create_rfq(c, amount=4_000_000)
    submit_quote(c, rfq_id, 9001, 610000, 2_000_000)
    submit_quote(c, rfq_id, 9002, 612000, 2_000_000)
    award_result = award(c, rfq_id)

    settlement = start_settlement(c, award_result)
    settlement_id = settlement["settlement_id"]
    leg_ids = [leg["leg_id"] for leg in settlement["legs"]]
    assert len(leg_ids) == 4

    for leg_id in leg_ids:
        response = submit_evidence(c, settlement_id, leg_id)
        assert response["settlement_id"] == settlement_id

    for leg_id in leg_ids:
        response = verify_leg(c, settlement_id, leg_id, verified=True)
        assert response["status"] in {"in_progress", "settled"}

    final = c.get(
        f"/settlement/{settlement_id}",
        headers={"X-Role": "operations", "X-User-Id": "ops-view"},
    ).json()
    assert final["status"] == "settled"
    assert SETTLEMENT_LOG.exists()


def test_invalid_evidence_escalates_to_dispute():
    c = client()
    create_provider(c, 9101)
    rfq_id = create_rfq(c, amount=1_000_000)
    submit_quote(c, rfq_id, 9101, 620000, 1_000_000)
    award_result = award(c, rfq_id)
    settlement = start_settlement(c, award_result)
    settlement_id = settlement["settlement_id"]
    leg_id = settlement["legs"][0]["leg_id"]

    bad_payload = {
        "evidence": {
            "hash": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "issuer": "Bank",
            "payer": "Customer",
            "payee": "Provider",
            "amounts": {"fiat": 1_000_000, "usdt": 1_000},
            "txId": "TXFAIL",
            "network": "TRC20",
            "claimedConfirmations": 0,
            "file_name": "bad.pdf",
            "file_size_mb": 6.0,
        }
    }
    first = c.post(
        f"/settlement/{settlement_id}/legs/{leg_id}/evidence",
        json=bad_payload,
        headers={"X-Role": "provider", "X-User-Id": "provider-bad"},
    )
    assert first.status_code == 400
    second = c.post(
        f"/settlement/{settlement_id}/legs/{leg_id}/evidence",
        json=bad_payload,
        headers={"X-Role": "provider", "X-User-Id": "provider-bad"},
    )
    assert second.status_code == 400
    assert DISPUTE_LOG.exists()
    events = [
        json.loads(line)
        for line in DISPUTE_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(event["reason"] == "invalid_evidence" for event in events)


def test_deadline_escalation_creates_dispute_entry():
    c = client()
    create_provider(c, 9201)
    rfq_id = create_rfq(c, amount=1_500_000)
    submit_quote(c, rfq_id, 9201, 615000, 1_500_000)
    award_result = award(c, rfq_id)
    settlement = start_settlement(c, award_result)
    settlement_id = settlement["settlement_id"]

    registry = get_settlement_registry()
    record = registry.get(settlement_id)
    for leg in record.legs:
        leg.deadline = datetime.now(timezone.utc) - timedelta(minutes=1)

    resp = c.post(
        "/settlement/deadlines/check",
        headers={"X-Role": "operations", "X-User-Id": "ops-deadline"},
    )
    assert resp.status_code == 200

    refreshed = c.get(
        f"/settlement/{settlement_id}",
        headers={"X-Role": "operations", "X-User-Id": "ops-view"},
    ).json()
    assert refreshed["status"] == "disputed"
    assert DISPUTE_LOG.exists()
    events = [
        json.loads(line)
        for line in DISPUTE_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(event["reason"] == "deadline_missed" for event in events)
