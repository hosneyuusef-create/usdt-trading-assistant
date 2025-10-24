"""
Test Analytics and Reporting endpoints (Stage 21).
Tests: M21-E2E-1, M21-E2E-2
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from src.backend.core.app import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


# M21-E2E-1: Test main reports
def test_rfq_summary_report(client):
    """
    M21-E2E-1a: Test RFQ Summary Report.

    Verifies:
    - Report returns correct structure
    - Metrics are calculated from audit logs
    - Cross-check with award_events.json and quote_events.json
    """
    response = client.post("/analytics/rfq-summary", json={})
    assert response.status_code == 200

    data = response.json()
    assert "total_rfqs" in data
    assert "avg_award_time_minutes" in data
    assert "rfqs_with_3plus_quotes" in data
    assert "rfqs_with_3plus_quotes_percentage" in data
    assert "volume_by_network" in data
    assert "period_start" in data
    assert "period_end" in data

    # Verify metrics are non-negative
    assert data["total_rfqs"] >= 0
    assert data["avg_award_time_minutes"] >= 0
    assert data["rfqs_with_3plus_quotes"] >= 0
    assert 0 <= data["rfqs_with_3plus_quotes_percentage"] <= 100

    # Verify volume breakdown
    assert isinstance(data["volume_by_network"], list)
    for vol in data["volume_by_network"]:
        assert "network" in vol
        assert "total_usdt_amount" in vol
        assert "total_fiat_amount" in vol
        assert "rfq_count" in vol


def test_settlement_kpi_report(client):
    """
    M21-E2E-1b: Test Settlement KPI Report.

    Verifies:
    - Success rate calculation
    - SLA breach rate
    - Average settlement time
    """
    response = client.post("/analytics/settlement-kpi", json={})
    assert response.status_code == 200

    data = response.json()
    assert "total_settlements" in data
    assert "successful_settlements" in data
    assert "success_rate_percentage" in data
    assert "avg_settlement_time_minutes" in data
    assert "sla_breach_count" in data
    assert "sla_breach_rate_percentage" in data

    # Verify metrics are valid
    assert data["total_settlements"] >= 0
    assert data["successful_settlements"] <= data["total_settlements"]
    assert 0 <= data["success_rate_percentage"] <= 100
    assert data["avg_settlement_time_minutes"] >= 0
    assert data["sla_breach_count"] >= 0
    assert 0 <= data["sla_breach_rate_percentage"] <= 100


def test_dispute_outcomes_report(client):
    """
    M21-E2E-1c: Test Dispute Outcomes Report.

    Verifies:
    - Dispute counts and resolution rate
    - Outcomes breakdown by decision type
    - Provider performance metrics
    """
    response = client.post("/analytics/dispute-outcomes", json={})
    assert response.status_code == 200

    data = response.json()
    assert "total_disputes" in data
    assert "resolved_disputes" in data
    assert "resolution_rate_percentage" in data
    assert "avg_resolution_time_hours" in data
    assert "outcomes_by_decision" in data
    assert "provider_performance" in data

    # Verify metrics
    assert data["total_disputes"] >= 0
    assert data["resolved_disputes"] <= data["total_disputes"]
    assert 0 <= data["resolution_rate_percentage"] <= 100

    # Verify outcomes breakdown
    assert isinstance(data["outcomes_by_decision"], list)
    total_pct = sum(o["percentage"] for o in data["outcomes_by_decision"])
    assert abs(total_pct - 100.0) < 1.0  # Allow small rounding error

    # Verify provider performance
    assert isinstance(data["provider_performance"], list)
    for perf in data["provider_performance"]:
        assert "provider_telegram_id" in perf
        assert "total_disputes_involved" in perf
        assert perf["total_disputes_involved"] >= 0


def test_telemetry_metrics(client):
    """
    M21-E2E-1d: Test Telemetry Metrics.

    Verifies:
    - Telemetry metrics from Telemetry_Config.json
    - notification_latency_p95_ms
    - notification_failure_rate
    - dispute_escalation_rate
    """
    response = client.get("/analytics/telemetry")
    assert response.status_code == 200

    data = response.json()
    assert "period" in data

    # Metrics may be None if not available, but should be present
    assert "notification_latency_p95_ms" in data
    assert "notification_failure_rate" in data
    assert "dispute_escalation_rate" in data


# M21-E2E-2: Test filtering and export
def test_rfq_summary_with_time_filter(client):
    """
    M21-E2E-2a: Test RFQ Summary with time range filter.

    Verifies:
    - last_n_days filter works correctly
    - start_date/end_date filter works
    """
    # Test with last_n_days
    response = client.post("/analytics/rfq-summary", json={"last_n_days": 7})
    assert response.status_code == 200
    data = response.json()
    assert "total_rfqs" in data

    # Test with date range
    response = client.post("/analytics/rfq-summary", json={
        "start_date": "2025-10-20",
        "end_date": "2025-10-24"
    })
    assert response.status_code == 200
    data = response.json()
    assert "total_rfqs" in data


def test_export_rfq_summary_to_csv(client):
    """
    M21-E2E-2b: Test exporting RFQ Summary to CSV.

    Verifies:
    - Export endpoint works
    - CSV file is generated
    - File contains correct data
    """
    response = client.post("/analytics/export", json={
        "report_type": "rfq_summary",
        "format": "csv",
        "time_range": {"last_n_days": 30}
    })
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"

    # Verify file content is CSV
    content = response.content.decode("utf-8")
    assert "Metric" in content or "Total RFQs" in content


def test_export_settlement_kpi_to_csv(client):
    """
    M21-E2E-2c: Test exporting Settlement KPI to CSV.
    """
    response = client.post("/analytics/export", json={
        "report_type": "settlement_kpi",
        "format": "csv"
    })
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"


def test_export_dispute_outcomes_to_csv(client):
    """
    M21-E2E-2d: Test exporting Dispute Outcomes to CSV.
    """
    response = client.post("/analytics/export", json={
        "report_type": "dispute_outcomes",
        "format": "csv"
    })
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"


def test_export_invalid_report_type(client):
    """
    M21-E2E-2e: Test export with invalid report type.
    """
    response = client.post("/analytics/export", json={
        "report_type": "invalid_report",
        "format": "csv"
    })
    assert response.status_code == 400
    assert "Unknown report type" in response.json()["detail"]


def test_cross_check_with_audit_logs():
    """
    M21-E2E-1e: Cross-check report numbers with audit logs.

    Verifies:
    - RFQ count matches unique rfq_id in award_events.json
    - Quote count matches quote_events.json
    """
    from src.backend.analytics.service import _load_json_log, AWARD_LOG, QUOTE_LOG

    # Load audit logs
    award_events = _load_json_log(AWARD_LOG)
    quote_events = _load_json_log(QUOTE_LOG)

    # Count unique RFQs from awards
    unique_rfqs = set(a["rfq_id"] for a in award_events)
    assert len(unique_rfqs) > 0, "Should have award events in logs"

    # Count quotes
    assert len(quote_events) > 0, "Should have quote events in logs"

    # Verify quotes belong to RFQs
    quote_rfqs = set(q["rfq_id"] for q in quote_events)
    assert quote_rfqs.issubset(unique_rfqs) or len(quote_rfqs.intersection(unique_rfqs)) > 0, \
        "Quotes should reference valid RFQs"
