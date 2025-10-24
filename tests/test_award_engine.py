import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.backend.core.app import create_app
from src.backend.provider.service import get_registry as get_provider_registry
from src.backend.rfq.service import get_registry as get_rfq_registry
from src.backend.notifications.service import get_quote_registry

AWARD_LOG = Path("logs/award_events.json")
QUOTE_LOG = Path("logs/quote_events.json")


def make_client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def reset_state():
    get_provider_registry().clear()
    get_rfq_registry().clear()
    quote_registry = get_quote_registry()
    quote_registry._quotes.clear()  # type: ignore[attr-defined]
    quote_registry._submission_times.clear()  # type: ignore[attr-defined]
    for path in (AWARD_LOG, QUOTE_LOG):
        if path.exists():
            path.unlink()
    yield
    get_provider_registry().clear()
    get_rfq_registry().clear()
    quote_registry._quotes.clear()  # type: ignore[attr-defined]
    quote_registry._submission_times.clear()  # type: ignore[attr-defined]
    for path in (AWARD_LOG, QUOTE_LOG):
        if path.exists():
            path.unlink()


def create_provider(client: TestClient, telegram_id: int, score: float = 85, collateral: int = 250_000_000):
    client.post(
        "/provider/register",
        json={
            "telegram_id": telegram_id,
            "display_name": f"Provider {telegram_id}",
            "score": score,
            "collateral_in_rial": collateral,
            "is_active": True,
        },
        headers={"X-Role": "admin", "X-User-Id": "admin-award"},
    )


def create_rfq(client: TestClient, amount: float, split_allowed: bool) -> str:
    payload = {
        "customer_id": "cust-award",
        "kyc_tier": "advanced",
        "rfq_type": "buy",
        "network": "TRC20",
        "amount": amount,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
        "special_conditions": {"split_allowed": split_allowed},
    }
    response = client.post(
        "/rfq",
        json=payload,
        headers={"X-Role": "operations", "X-User-Id": "ops-award"},
    )
    assert response.status_code == 201
    return response.json()["rfq_id"]


def submit_quote(
    client: TestClient,
    rfq_id: str,
    provider_id: int,
    unit_price: float,
    capacity: float,
    submitted_at_delta: int = 0,
) -> str:
    response = client.post(
        "/notifications/quotes",
        json={
            "rfq_id": rfq_id,
            "provider_telegram_id": provider_id,
            "unit_price": unit_price,
            "capacity": capacity,
        },
        headers={"X-Role": "provider", "X-User-Id": f"provider-{provider_id}"},
    )
    assert response.status_code == 200
    quote_id = response.json()["quote_id"]
    if submitted_at_delta:
        registry = get_quote_registry()
        record_list = registry._quotes[rfq_id]  # type: ignore[attr-defined]
        target = next(rec for rec in record_list if rec.quote_id == quote_id)
        target.submitted_at -= timedelta(seconds=submitted_at_delta)
    return quote_id


def test_tie_break_prefers_earlier_submission():
    client = make_client()
    create_provider(client, 8001)
    create_provider(client, 8002)
    rfq_id = create_rfq(client, amount=2_000_000, split_allowed=False)
    submit_quote(client, rfq_id, provider_id=8001, unit_price=615000, capacity=2_000_000, submitted_at_delta=5)
    submit_quote(client, rfq_id, provider_id=8002, unit_price=615000, capacity=2_000_000)

    resp = client.post(
        f"/award/{rfq_id}/auto",
        headers={"X-Role": "operations", "X-User-Id": "ops-award"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["legs"][0]["provider_telegram_id"] == 8001
    assert Path("artefacts/Award_Audit.xlsx").exists()


def test_partial_fill_when_split_allowed():
    client = make_client()
    create_provider(client, 8101)
    create_provider(client, 8102)
    rfq_id = create_rfq(client, amount=3_000_000, split_allowed=True)
    submit_quote(client, rfq_id, provider_id=8101, unit_price=610000, capacity=1_500_000)
    submit_quote(client, rfq_id, provider_id=8102, unit_price=612000, capacity=1_800_000)

    resp = client.post(
        f"/award/{rfq_id}/auto",
        headers={"X-Role": "admin", "X-User-Id": "admin-award"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["legs"]) == 2
    total_awarded = sum(float(leg["awarded_amount"]) for leg in data["legs"])
    assert total_awarded == 3_000_000

    quote_registry = get_quote_registry()
    records = quote_registry.list(rfq_id)
    winners = [r for r in records if r.accepted]
    assert len(winners) == 2
    amounts = sorted(getattr(rec, "awarded_amount", 0) for rec in winners if getattr(rec, "awarded_amount", None) is not None)
    assert amounts == [1_500_000, 1_500_000]

    assert AWARD_LOG.exists()
    events = [
        json.loads(line)
        for line in AWARD_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert events
