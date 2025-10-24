import logging

import pytest
from fastapi.testclient import TestClient

from src.backend.core.app import create_app
from src.backend.provider.service import get_registry


@pytest.fixture(autouse=True)
def reset_registry():
    registry = get_registry()
    registry.clear()
    yield
    registry.clear()


def _client():
    app = create_app()
    return TestClient(app)


def test_provider_registration_returns_eligibility_summary():
    client = _client()

    payload = {
        "telegram_id": 1001,
        "display_name": "Alpha Liquidity",
        "score": 88.5,
        "collateral_in_rial": 250_000_000,
        "is_active": True,
        "capabilities": ["trc20", "erc20"],
    }

    response = client.post(
        "/provider/register",
        json=payload,
        headers={"X-Role": "admin", "X-User-Id": "tester-admin"},
    )
    assert response.status_code == 201
    data = response.json()

    assert data["provider_id"]
    assert data["telegram_id"] == 1001
    assert data["eligibility"]["is_eligible"] is True
    assert data["eligibility"]["reasons"] == []


def test_registration_flags_insufficient_collateral():
    client = _client()

    response = client.post(
        "/provider/register",
        headers={"X-Role": "admin", "X-User-Id": "tester-admin"},
        json={
            "telegram_id": 2002,
            "display_name": "Beta Liquidity",
            "score": 75,
            "collateral_in_rial": 150_000_000,
            "is_active": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["eligibility"]["is_eligible"] is False
    assert "insufficient_collateral" in data["eligibility"]["reasons"]


def test_filter_for_rfq_returns_only_eligible(caplog):
    client = _client()
    client.post(
        "/provider/register",
        headers={"X-Role": "admin", "X-User-Id": "tester-admin"},
        json={
            "telegram_id": 3003,
            "display_name": "Gamma Liquidity",
            "score": 90,
            "collateral_in_rial": 220_000_000,
            "is_active": True,
        },
    )
    client.post(
        "/provider/register",
        headers={"X-Role": "admin", "X-User-Id": "tester-admin"},
        json={
            "telegram_id": 4004,
            "display_name": "Delta Reserve",
            "score": 68,
            "collateral_in_rial": 210_000_000,
            "is_active": True,
        },
    )

    registry = get_registry()
    caplog.set_level(logging.INFO, logger="usdt.provider")
    caplog.clear()
    eligible = registry.filter_for_rfq()

    assert len(eligible) == 1
    assert eligible[0].telegram_id == 3003

    matched = [
        record
        for record in caplog.records
        if record.getMessage() == "rfq_eligibility_evaluated"
        and getattr(record, "telegram_id", None) == 4004
        and getattr(record, "eligible", None) is False
    ]
    assert matched, "Expected rfq eligibility log for ineligible provider"
