import os

from fastapi.testclient import TestClient

from src.backend.core.app import create_app


def test_health_endpoint_returns_ok_status(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://stub")
    monkeypatch.setenv("RABBITMQ_URL", "amqp://stub")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot_stub")

    app = create_app()
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "services" in data
    assert data["version"]
    assert response.headers.get("X-Trace-ID")
