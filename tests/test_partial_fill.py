import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.backend.core.app import create_app
from src.backend.provider.service import get_registry as get_provider_registry
from src.backend.rfq.service import get_registry as get_rfq_registry
from src.backend.notifications.service import get_quote_registry
from src.backend.partial_fill.service import get_registry as get_partial_registry

PARTIAL_LOG = Path("logs/partial_fill_events.json")


@pytest.fixture(autouse=True)
def reset_state():
    get_provider_registry().clear()
    get_rfq_registry().clear()
    quote_registry = get_quote_registry()
    quote_registry._quotes.clear()  # type: ignore[attr-defined]
    quote_registry._submission_times.clear()  # type: ignore[attr-defined]
    get_partial_registry()._records.clear()  # type: ignore[attr-defined]
    if PARTIAL_LOG.exists():
        PARTIAL_LOG.unlink()
    yield
    get_provider_registry().clear()
    get_rfq_registry().clear()
    quote_registry._quotes.clear()  # type: ignore[attr-defined]
    quote_registry._submission_times.clear()  # type: ignore[attr-defined]
    get_partial_registry()._records.clear()  # type: ignore[attr-defined]
    if PARTIAL_LOG.exists():
        PARTIAL_LOG.unlink()


def client() -> TestClient:
    return TestClient(create_app())


def create_provider(client: TestClient, telegram_id: int, score: float = 85.0):
    resp = client.post(
        "/provider/register",
        json={
            "telegram_id": telegram_id,
            "display_name": f"Provider {telegram_id}",
            "score": score,
            "collateral_in_rial": 250_000_000,
            "is_active": True,
        },
        headers={"X-Role": "admin", "X-User-Id": "admin-partial"},
    )
    assert resp.status_code == 201


def create_rfq(client: TestClient, amount: float):
    payload = {
        "customer_id": "cust-partial",
        "kyc_tier": "advanced",
        "rfq_type": "buy",
        "network": "TRC20",
        "amount": amount,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
        "special_conditions": {"split_allowed": True},
    }
    resp = client.post(
        "/rfq",
        json=payload,
        headers={"X-Role": "operations", "X-User-Id": "ops-partial"},
    )
    assert resp.status_code == 201
    return resp.json()["rfq_id"]


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
        headers={"X-Role": "operations", "X-User-Id": "ops-partial"},
    )
    assert resp.status_code == 200
    return resp.json()


def start_partial(client: TestClient, award_result: dict):
    resp = client.post(
        "/partial-fill/start",
        json=award_result,
        headers={"X-Role": "operations", "X-User-Id": "ops-partial"},
    )
    assert resp.status_code == 200
    return resp.json()


def test_reallocate_partial_fill_creates_new_leg():
    c = client()
    create_provider(c, 9301)
    create_provider(c, 9302)
    rfq_id = create_rfq(c, amount=3_000_000)
    submit_quote(c, rfq_id, 9301, 610000, 3_000_000)
    award_result = award(c, rfq_id)
    start_partial(c, award_result)

    request = {
        "from_quote_id": award_result["legs"][0]["quote_id"],
        "to_provider_telegram_id": 9302,
        "reallocated_amount": 1_200_000,
        "unit_price": 612000,
    }
    resp = c.post(
        f"/partial-fill/{rfq_id}/reallocate",
        json=request,
        headers={"X-Role": "operations", "X-User-Id": "ops-partial"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["remaining_amount"]) == 0
    assert len(data["legs"]) == 2
    assert any(leg["status"] == "partial" for leg in data["legs"])
    assert any(leg["provider_telegram_id"] == 9302 for leg in data["legs"])
    assert PARTIAL_LOG.exists()


def test_cancel_leg_marks_status_and_updates_sheet():
    c = client()
    create_provider(c, 9401)
    rfq_id = create_rfq(c, amount=2_000_000)
    submit_quote(c, rfq_id, 9401, 620000, 2_000_000)
    award_result = award(c, rfq_id)
    start_partial(c, award_result)
    quote_id = award_result["legs"][0]["quote_id"]
    resp = c.post(
        f"/partial-fill/{rfq_id}/cancel",
        json={"quote_id": quote_id, "reason": "provider_failure"},
        headers={"X-Role": "operations", "X-User-Id": "ops-partial"},
    )
    assert resp.status_code == 200
    data = resp.json()
    cancelled = next(leg for leg in data["legs"] if leg["quote_id"] == quote_id)
    assert cancelled["status"] == "cancelled"
    assert Path("artefacts/Order_Reconciliation.xlsx").exists()





