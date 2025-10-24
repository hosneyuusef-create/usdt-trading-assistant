"""
Stage 18: Dispute Management Tests
Tests dispute filing, evidence submission, SLA enforcement, and arbitration decisions.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.backend.core.app import create_app
from src.backend.dispute.service import get_registry as get_dispute_registry

DISPUTE_LOG = Path("logs/dispute_events.json")
DISPUTE_ACTION_LOG = Path("logs/dispute_action_events.json")


def make_client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def reset_state():
    """Reset dispute registry and clear logs before each test."""
    registry = get_dispute_registry()
    registry.clear()
    for path in (DISPUTE_LOG, DISPUTE_ACTION_LOG):
        if path.exists():
            path.unlink()
    yield
    registry.clear()
    for path in (DISPUTE_LOG, DISPUTE_ACTION_LOG):
        if path.exists():
            path.unlink()


def test_file_dispute_and_submit_evidence_within_window():
    """
    M18-E2E-1: File dispute and submit evidence within allowed window.
    Tests complete happy path: file → evidence → review → decision.
    """
    client = make_client()

    # File dispute
    file_response = client.post(
        "/dispute/file",
        params={"respondent_telegram_id": 444555666},
        json={
            "settlement_id": "S12345",
            "claimant_telegram_id": 111222333,
            "reason": "پرداخت ریالی انجام شد اما USDT دریافت نشد. رسید بانکی شماره 7891011.",
        },
        headers={"X-Role": "customer", "X-User-Id": "cust-111222333"},
    )
    assert file_response.status_code == 200
    dispute_data = file_response.json()
    assert dispute_data["status"] == "awaiting_evidence"
    assert dispute_data["claimant_telegram_id"] == 111222333
    assert dispute_data["respondent_telegram_id"] == 444555666
    dispute_id = dispute_data["dispute_id"]

    # Verify dispute log
    assert DISPUTE_LOG.exists()
    with DISPUTE_LOG.open("r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) >= 1
        first_event = json.loads(lines[0])
        assert first_event["event"] == "dispute_filed"
        assert first_event["dispute_id"] == dispute_id
        assert first_event["settlement_id"] == "S12345"

    # Submit evidence from claimant
    evidence_response_1 = client.post(
        "/dispute/evidence",
        json={
            "dispute_id": dispute_id,
            "submitter_telegram_id": 111222333,
            "evidence_type": "bank_receipt",
            "storage_url": "file://evidence/receipt_7891011.pdf",
            "hash": "5e88489d1b2c8a3f7c9d4e6f8a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b",
            "metadata": {"receipt_number": "7891011", "amount": "2050000"},
            "notes": "رسید بانکی اصل",
        },
        headers={"X-Role": "customer", "X-User-Id": "cust-111222333"},
    )
    assert evidence_response_1.status_code == 200
    evidence_1 = evidence_response_1.json()
    assert evidence_1["evidence_type"] == "bank_receipt"
    assert evidence_1["submitter_telegram_id"] == 111222333

    # Submit evidence from respondent
    evidence_response_2 = client.post(
        "/dispute/evidence",
        json={
            "dispute_id": dispute_id,
            "submitter_telegram_id": 444555666,
            "evidence_type": "tx_proof",
            "storage_url": "file://evidence/tx_abc123.png",
            "hash": "abcdef123456789abcdef123456789abcdef123456789abcdef123456789ab",
            "metadata": {"tx_id": "0xabc123", "network": "TRC20"},
            "notes": "TxID ارسال USDT",
        },
        headers={"X-Role": "provider", "X-User-Id": "prov-444555666"},
    )
    assert evidence_response_2.status_code == 200
    evidence_2 = evidence_response_2.json()
    assert evidence_2["evidence_type"] == "tx_proof"

    # Get dispute details
    get_response = client.get(
        f"/dispute/{dispute_id}",
        headers={"X-Role": "admin", "X-User-Id": "admin-dispute"},
    )
    assert get_response.status_code == 200
    dispute_detail = get_response.json()
    assert dispute_detail["evidence_count"] == 2
    assert dispute_detail["status"] == "awaiting_evidence"

    # Verify evidence logs
    with DISPUTE_LOG.open("r", encoding="utf-8") as f:
        lines = f.readlines()
        evidence_events = [json.loads(line) for line in lines if "evidence_submitted" in line]
        assert len(evidence_events) == 2

    print("✓ M18-E2E-1 PASSED: Dispute filed and evidence submitted successfully.")


def test_reject_evidence_after_deadline():
    """
    M18-E2E-2: Reject evidence submission after evidence deadline (30min).
    Tests SLA enforcement for evidence window.
    """
    # Manually create a dispute with past evidence deadline
    registry = get_dispute_registry()
    from src.backend.dispute.schemas import DisputeFileRequest

    request = DisputeFileRequest(
        settlement_id="S99999",
        claimant_telegram_id=111222333,
        reason="Test dispute for deadline check",
    )
    dispute = registry.file_dispute(request, respondent_telegram_id=444555666)
    dispute_id = dispute.dispute_id

    # Manually set evidence_deadline to past
    record = registry._storage[dispute_id]
    record.evidence_deadline = datetime.now(timezone.utc) - timedelta(minutes=1)

    # Try to submit evidence (should fail)
    client = make_client()
    evidence_response = client.post(
        "/dispute/evidence",
        json={
            "dispute_id": dispute_id,
            "submitter_telegram_id": 111222333,
            "evidence_type": "bank_receipt",
            "storage_url": "file://evidence/late.pdf",
            "hash": "abc123def456789abc123def456789ab",
            "metadata": {},
        },
        headers={"X-Role": "customer", "X-User-Id": "cust-111222333"},
    )
    assert evidence_response.status_code == 400
    assert "deadline passed" in evidence_response.json()["detail"].lower()

    print("✓ M18-E2E-2 PASSED: Late evidence rejected correctly.")


def test_make_decision_within_sla():
    """
    M18-E2E-3: Make arbitration decision within SLA (≤4 hours).
    Tests complete dispute resolution workflow.
    """
    client = make_client()

    # File dispute
    file_response = client.post(
        "/dispute/file",
        params={"respondent_telegram_id": 444555666},
        json={
            "settlement_id": "S55555",
            "claimant_telegram_id": 111222333,
            "reason": "اختلاف در مقدار USDT دریافتی",
        },
        headers={"X-Role": "customer", "X-User-Id": "cust-111222333"},
    )
    assert file_response.status_code == 200
    dispute_id = file_response.json()["dispute_id"]

    # Submit evidence
    client.post(
        "/dispute/evidence",
        json={
            "dispute_id": dispute_id,
            "submitter_telegram_id": 111222333,
            "evidence_type": "screenshot",
            "storage_url": "file://evidence/screen.png",
            "hash": "hash123456789abcdef",
            "metadata": {},
        },
        headers={"X-Role": "customer", "X-User-Id": "cust-111222333"},
    )

    # Manually advance past evidence deadline for review
    registry = get_dispute_registry()
    record = registry._storage[dispute_id]
    record.evidence_deadline = datetime.now(timezone.utc) - timedelta(minutes=1)

    # Start review
    review_response = client.post(
        f"/dispute/review/{dispute_id}",
        params={"admin_telegram_id": 999888777},
        headers={"X-Role": "admin", "X-User-Id": "admin-999888777"},
    )
    assert review_response.status_code == 200
    assert review_response.json()["action_type"] == "review_start"

    # Make decision
    decision_response = client.post(
        "/dispute/decision",
        json={
            "dispute_id": dispute_id,
            "admin_telegram_id": 999888777,
            "decision": "favor_claimant",
            "decision_reason": "بر اساس بررسی مدارک، مشتری حق دارد. پرووایدر مقدار کامل را ارسال نکرده است.",
            "awarded_to_claimant": "1500.00",
            "evidence_reviewed": [],
        },
        headers={"X-Role": "admin", "X-User-Id": "admin-999888777"},
    )
    assert decision_response.status_code == 200
    decision_data = decision_response.json()
    assert decision_data["status"] == "resolved"
    assert decision_data["decision"] == "favor_claimant"
    assert decision_data["decision_at"] is not None

    # Verify decision log
    with DISPUTE_LOG.open("r", encoding="utf-8") as f:
        lines = f.readlines()
        decision_events = [json.loads(line) for line in lines if "decision_made" in line]
        assert len(decision_events) == 1
        decision_event = decision_events[0]
        assert decision_event["decision"] == "favor_claimant"
        assert decision_event["admin_telegram_id"] == 999888777

    print("✓ M18-E2E-3 PASSED: Decision made successfully within SLA.")


def test_escalate_on_decision_deadline_breach():
    """
    M18-E2E-4: Escalate dispute when decision deadline is breached.
    Tests SLA breach handling and escalation workflow.
    """
    # Manually create a dispute with past decision deadline
    registry = get_dispute_registry()
    from src.backend.dispute.schemas import DisputeFileRequest

    request = DisputeFileRequest(
        settlement_id="S88888",
        claimant_telegram_id=111222333,
        reason="Test dispute for SLA breach",
    )
    dispute = registry.file_dispute(request, respondent_telegram_id=444555666)
    dispute_id = dispute.dispute_id

    # Manually set decision_deadline to past
    record = registry._storage[dispute_id]
    record.decision_deadline = datetime.now(timezone.utc) - timedelta(minutes=1)

    # Try to make decision (should fail with SLA breach)
    client = make_client()
    decision_response = client.post(
        "/dispute/decision",
        json={
            "dispute_id": dispute_id,
            "admin_telegram_id": 999888777,
            "decision": "inconclusive",
            "decision_reason": "نیاز به بررسی بیشتر و زمان اضافی برای ارزیابی شواهد",
            "evidence_reviewed": [],
        },
        headers={"X-Role": "admin", "X-User-Id": "admin-999888777"},
    )
    assert decision_response.status_code == 400
    assert "deadline passed" in decision_response.json()["detail"].lower()
    assert "4-hour sla breach" in decision_response.json()["detail"].lower()

    # Escalate
    escalate_response = client.post(
        f"/dispute/escalate/{dispute_id}",
        params={
            "admin_telegram_id": 999888777,
            "reason": "SLA breach: Decision deadline passed. Escalating to senior arbitrator.",
        },
        headers={"X-Role": "admin", "X-User-Id": "admin-999888777"},
    )
    assert escalate_response.status_code == 200
    escalate_data = escalate_response.json()
    assert escalate_data["action_type"] == "escalate"

    # Verify dispute status
    get_response = client.get(
        f"/dispute/{dispute_id}",
        headers={"X-Role": "admin", "X-User-Id": "admin-999888777"},
    )
    assert get_response.status_code == 200
    dispute_detail = get_response.json()
    assert dispute_detail["status"] == "escalated"

    # Verify escalation log
    with DISPUTE_ACTION_LOG.open("r", encoding="utf-8") as f:
        lines = f.readlines()
        escalate_events = [json.loads(line) for line in lines if "escalate" in line]
        assert len(escalate_events) == 1
        escalate_event = escalate_events[0]
        assert escalate_event["action_type"] == "escalate"
        assert "SLA breach" in escalate_event["reason"]

    print("✓ M18-E2E-4 PASSED: Escalation triggered correctly on SLA breach.")
