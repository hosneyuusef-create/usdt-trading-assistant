import pytest
from fastapi.testclient import TestClient

from src.backend.core.app import create_app
from src.backend.customer.service import get_registry


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://stub")
    monkeypatch.setenv("RABBITMQ_URL", "amqp://stub")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot_stub")
    registry = get_registry()
    registry.clear()
    yield
    registry.clear()


def test_customer_registration_masks_card_and_applies_limit():
    app = create_app()
    client = TestClient(app)

    payload = {
        "telegram_id": 12345,
        "full_name": "Alice Example",
        "kyc_tier": "Advanced",
        "wallet_address": "TRC20-123",
        "payment_instrument": {
            "card_number": "6219861023456789",
            "card_holder": "Alice Example",
            "bank_name": "Test Bank"
        }
    }

    response = client.post("/customer/register", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()

    assert data["telegram_id"] == 12345
    assert data["kyc_tier"] == "advanced"
    assert data["daily_limit"] == 10_000_000
    assert data["masked_card"].endswith("6789")
    assert set(data["masked_card"]) <= {"*", "6", "7", "8", "9"}


def test_duplicate_registration_returns_existing_record():
    app = create_app()
    client = TestClient(app)

    payload = {
        "telegram_id": 67890,
        "full_name": "Bob Example",
        "kyc_tier": "Premium",
        "wallet_address": "BEP20-456",
        "payment_instrument": {
            "card_number": "5022291234567890",
            "card_holder": "Bob Example",
            "bank_name": "Sample Bank"
        }
    }

    first = client.post("/customer/register", json=payload)
    second = client.post("/customer/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["customer_id"] == second.json()["customer_id"]


def test_registration_rejects_unknown_tier():
    app = create_app()
    client = TestClient(app)

    payload = {
        "telegram_id": 111,
        "full_name": "Invalid Tier",
        "kyc_tier": "silver",
        "wallet_address": "ERC20-789",
        "payment_instrument": {
            "card_number": "4111111111111111",
            "card_holder": "Invalid Tier"
        }
    }

    response = client.post("/customer/register", json=payload)
    assert response.status_code == 400
    assert "Unsupported KYC tier" in response.text
