"""
Stage 18: Dispute Service
Manages dispute lifecycle, evidence collection, SLA enforcement, and arbitration workflow.

SLA Timeline:
1. File dispute → Request evidence: immediate
2. Evidence submission window: 30 minutes from filing
3. Review period: 60 minutes after evidence deadline
4. Final decision: ≤4 hours from filing

Non-custodial principle: System stores hash and metadata only; actual files remain with parties.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from .schemas import (
    ArbitrationDecision,
    DisputeActionResponse,
    DisputeEvidenceResponse,
    DisputeFileRequest,
    DisputeResponse,
    EvidenceSubmission,
)

DISPUTE_LOG = Path("logs/dispute_events.json")
DISPUTE_ACTION_LOG = Path("logs/dispute_action_events.json")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _log(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


@dataclass
class EvidenceRecord:
    evidence_id: str
    dispute_id: str
    submitter_telegram_id: int
    evidence_type: str
    storage_url: str
    hash: str
    metadata: Optional[dict] = None
    notes: Optional[str] = None
    submitted_at: datetime = field(default_factory=_now)


@dataclass
class DisputeActionRecord:
    action_id: str
    dispute_id: str
    admin_telegram_id: int
    action_type: str
    notes: Optional[str] = None
    action_at: datetime = field(default_factory=_now)


@dataclass
class DisputeRecord:
    dispute_id: str
    settlement_id: str
    claimant_telegram_id: int
    respondent_telegram_id: int
    reason: str
    status: str = "open"
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    opened_at: datetime = field(default_factory=_now)
    evidence_deadline: datetime = field(default_factory=lambda: _now() + timedelta(minutes=30))
    review_deadline: datetime = field(default_factory=lambda: _now() + timedelta(minutes=90))
    decision_deadline: datetime = field(default_factory=lambda: _now() + timedelta(hours=4))
    decision_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    evidence: List[EvidenceRecord] = field(default_factory=list)
    actions: List[DisputeActionRecord] = field(default_factory=list)


class DisputeRegistry:
    """
    Manage dispute lifecycle for Stage 18.
    Enforces SLA timelines and Non-custodial evidence handling.
    """

    def __init__(self) -> None:
        self._storage: Dict[str, DisputeRecord] = {}
        self._evidence_storage: Dict[str, List[EvidenceRecord]] = {}

    def file_dispute(
        self, request: DisputeFileRequest, respondent_telegram_id: int
    ) -> DisputeResponse:
        """
        File a new dispute on a settlement.
        Immediately sends evidence request to both parties.
        """
        dispute_id = uuid.uuid4().hex
        record = DisputeRecord(
            dispute_id=dispute_id,
            settlement_id=request.settlement_id,
            claimant_telegram_id=request.claimant_telegram_id,
            respondent_telegram_id=respondent_telegram_id,
            reason=request.reason,
            status="open",
        )

        # Log dispute filing
        _log(
            DISPUTE_LOG,
            {
                "event": "dispute_filed",
                "dispute_id": dispute_id,
                "settlement_id": request.settlement_id,
                "claimant_telegram_id": request.claimant_telegram_id,
                "respondent_telegram_id": respondent_telegram_id,
                "reason": request.reason,
                "evidence_deadline": record.evidence_deadline.isoformat(),
                "review_deadline": record.review_deadline.isoformat(),
                "decision_deadline": record.decision_deadline.isoformat(),
                "timestamp": record.opened_at.isoformat(),
            },
        )

        # Record action: evidence request sent
        action = DisputeActionRecord(
            action_id=uuid.uuid4().hex,
            dispute_id=dispute_id,
            admin_telegram_id=0,  # System action
            action_type="request_evidence",
            notes=f"Evidence requested from both parties. Deadline: {record.evidence_deadline.isoformat()}",
        )
        record.actions.append(action)

        _log(
            DISPUTE_ACTION_LOG,
            {
                "action_id": action.action_id,
                "dispute_id": dispute_id,
                "action_type": "request_evidence",
                "notes": action.notes,
                "timestamp": action.action_at.isoformat(),
            },
        )

        # Update status
        record.status = "awaiting_evidence"
        record.updated_at = _now()

        self._storage[dispute_id] = record
        self._evidence_storage[dispute_id] = []

        return self._to_response(record)

    def submit_evidence(self, submission: EvidenceSubmission) -> DisputeEvidenceResponse:
        """
        Submit evidence for a dispute.
        Validates submission window (30 minutes from filing).
        """
        dispute_id = submission.dispute_id
        if dispute_id not in self._storage:
            raise ValueError(f"Dispute {dispute_id} not found")

        record = self._storage[dispute_id]

        # Check evidence deadline
        if _now() > record.evidence_deadline:
            raise ValueError(
                f"Evidence submission deadline passed. "
                f"Deadline was {record.evidence_deadline.isoformat()}"
            )

        # Create evidence record
        evidence_id = uuid.uuid4().hex
        evidence = EvidenceRecord(
            evidence_id=evidence_id,
            dispute_id=dispute_id,
            submitter_telegram_id=submission.submitter_telegram_id,
            evidence_type=submission.evidence_type,
            storage_url=submission.storage_url,
            hash=submission.hash,
            metadata=submission.metadata,
            notes=submission.notes,
        )

        record.evidence.append(evidence)
        self._evidence_storage[dispute_id].append(evidence)

        # Log evidence submission
        _log(
            DISPUTE_LOG,
            {
                "event": "evidence_submitted",
                "evidence_id": evidence_id,
                "dispute_id": dispute_id,
                "submitter_telegram_id": submission.submitter_telegram_id,
                "evidence_type": submission.evidence_type,
                "hash": submission.hash,
                "timestamp": evidence.submitted_at.isoformat(),
            },
        )

        record.updated_at = _now()

        return DisputeEvidenceResponse(
            evidence_id=evidence.evidence_id,
            dispute_id=evidence.dispute_id,
            submitter_telegram_id=evidence.submitter_telegram_id,
            evidence_type=evidence.evidence_type,
            storage_url=evidence.storage_url,
            hash=evidence.hash,
            metadata=evidence.metadata,
            notes=evidence.notes,
            submitted_at=evidence.submitted_at,
        )

    def start_review(self, dispute_id: str, admin_telegram_id: int) -> DisputeActionResponse:
        """
        Start review process after evidence deadline.
        Validates review window (30-90 minutes from filing).
        """
        if dispute_id not in self._storage:
            raise ValueError(f"Dispute {dispute_id} not found")

        record = self._storage[dispute_id]

        # Check evidence deadline has passed
        if _now() < record.evidence_deadline:
            raise ValueError(
                f"Evidence submission window still open. "
                f"Deadline: {record.evidence_deadline.isoformat()}"
            )

        # Check review deadline
        if _now() > record.review_deadline:
            raise ValueError(
                f"Review deadline passed. Escalation may be required. "
                f"Deadline was {record.review_deadline.isoformat()}"
            )

        # Record action: review started
        action = DisputeActionRecord(
            action_id=uuid.uuid4().hex,
            dispute_id=dispute_id,
            admin_telegram_id=admin_telegram_id,
            action_type="review_start",
            notes=f"Review started. Evidence count: {len(record.evidence)}",
        )
        record.actions.append(action)

        _log(
            DISPUTE_ACTION_LOG,
            {
                "action_id": action.action_id,
                "dispute_id": dispute_id,
                "admin_telegram_id": admin_telegram_id,
                "action_type": "review_start",
                "evidence_count": len(record.evidence),
                "timestamp": action.action_at.isoformat(),
            },
        )

        # Update status
        record.status = "under_review"
        record.updated_at = _now()

        return DisputeActionResponse(
            action_id=action.action_id,
            dispute_id=dispute_id,
            admin_telegram_id=admin_telegram_id,
            action_type=action.action_type,
            notes=action.notes,
            action_at=action.action_at,
        )

    def make_decision(
        self, decision: ArbitrationDecision
    ) -> DisputeResponse:
        """
        Make arbitration decision on a dispute.
        Validates decision window (≤4 hours from filing).
        Enforces Non-custodial principle: decision references evidence hashes only.
        """
        dispute_id = decision.dispute_id
        if dispute_id not in self._storage:
            raise ValueError(f"Dispute {dispute_id} not found")

        record = self._storage[dispute_id]

        # Check decision deadline
        if _now() > record.decision_deadline:
            raise ValueError(
                f"Decision deadline passed (4-hour SLA breach). "
                f"Deadline was {record.decision_deadline.isoformat()}"
            )

        # Check status
        if record.status not in ("under_review", "awaiting_evidence"):
            raise ValueError(
                f"Cannot make decision. Current status: {record.status}. "
                f"Expected: under_review or awaiting_evidence"
            )

        # Record decision
        record.decision = decision.decision
        record.decision_reason = decision.decision_reason
        record.decision_at = _now()
        record.status = "resolved"
        record.updated_at = _now()

        # Record action: decision made
        action = DisputeActionRecord(
            action_id=uuid.uuid4().hex,
            dispute_id=dispute_id,
            admin_telegram_id=decision.admin_telegram_id,
            action_type="decision",
            notes=f"Decision: {decision.decision}. Evidence reviewed: {len(decision.evidence_reviewed)}",
        )
        record.actions.append(action)

        _log(
            DISPUTE_LOG,
            {
                "event": "decision_made",
                "dispute_id": dispute_id,
                "admin_telegram_id": decision.admin_telegram_id,
                "decision": decision.decision,
                "decision_reason": decision.decision_reason,
                "awarded_to_claimant": str(decision.awarded_to_claimant) if decision.awarded_to_claimant else None,
                "awarded_to_respondent": str(decision.awarded_to_respondent) if decision.awarded_to_respondent else None,
                "evidence_reviewed": decision.evidence_reviewed,
                "timestamp": record.decision_at.isoformat(),
            },
        )

        _log(
            DISPUTE_ACTION_LOG,
            {
                "action_id": action.action_id,
                "dispute_id": dispute_id,
                "admin_telegram_id": decision.admin_telegram_id,
                "action_type": "decision",
                "decision": decision.decision,
                "timestamp": action.action_at.isoformat(),
            },
        )

        return self._to_response(record)

    def escalate(self, dispute_id: str, admin_telegram_id: int, reason: str) -> DisputeActionResponse:
        """
        Escalate dispute to higher authority when SLA is breached or resolution is inconclusive.
        """
        if dispute_id not in self._storage:
            raise ValueError(f"Dispute {dispute_id} not found")

        record = self._storage[dispute_id]

        # Record action: escalation
        action = DisputeActionRecord(
            action_id=uuid.uuid4().hex,
            dispute_id=dispute_id,
            admin_telegram_id=admin_telegram_id,
            action_type="escalate",
            notes=reason,
        )
        record.actions.append(action)

        _log(
            DISPUTE_ACTION_LOG,
            {
                "action_id": action.action_id,
                "dispute_id": dispute_id,
                "admin_telegram_id": admin_telegram_id,
                "action_type": "escalate",
                "reason": reason,
                "timestamp": action.action_at.isoformat(),
            },
        )

        # Update status
        record.status = "escalated"
        record.updated_at = _now()

        return DisputeActionResponse(
            action_id=action.action_id,
            dispute_id=dispute_id,
            admin_telegram_id=admin_telegram_id,
            action_type=action.action_type,
            notes=action.notes,
            action_at=action.action_at,
        )

    def get_dispute(self, dispute_id: str) -> DisputeResponse:
        """Get dispute details."""
        if dispute_id not in self._storage:
            raise ValueError(f"Dispute {dispute_id} not found")
        return self._to_response(self._storage[dispute_id])

    def list_disputes(self, status: Optional[str] = None) -> List[DisputeResponse]:
        """List all disputes, optionally filtered by status."""
        records = self._storage.values()
        if status:
            records = [r for r in records if r.status == status]
        return [self._to_response(r) for r in records]

    def get_evidence(self, dispute_id: str) -> List[DisputeEvidenceResponse]:
        """Get all evidence for a dispute."""
        if dispute_id not in self._evidence_storage:
            return []
        return [
            DisputeEvidenceResponse(
                evidence_id=e.evidence_id,
                dispute_id=e.dispute_id,
                submitter_telegram_id=e.submitter_telegram_id,
                evidence_type=e.evidence_type,
                storage_url=e.storage_url,
                hash=e.hash,
                metadata=e.metadata,
                notes=e.notes,
                submitted_at=e.submitted_at,
            )
            for e in self._evidence_storage[dispute_id]
        ]

    def _to_response(self, record: DisputeRecord) -> DisputeResponse:
        return DisputeResponse(
            dispute_id=record.dispute_id,
            settlement_id=record.settlement_id,
            claimant_telegram_id=record.claimant_telegram_id,
            respondent_telegram_id=record.respondent_telegram_id,
            reason=record.reason,
            status=record.status,
            decision=record.decision,
            decision_reason=record.decision_reason,
            opened_at=record.opened_at,
            evidence_deadline=record.evidence_deadline,
            review_deadline=record.review_deadline,
            decision_deadline=record.decision_deadline,
            decision_at=record.decision_at,
            evidence_count=len(record.evidence),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def clear(self) -> None:
        """Clear all disputes (for testing)."""
        self._storage.clear()
        self._evidence_storage.clear()


# Singleton registry
_registry: Optional[DisputeRegistry] = None


def get_registry() -> DisputeRegistry:
    global _registry
    if _registry is None:
        _registry = DisputeRegistry()
    return _registry
