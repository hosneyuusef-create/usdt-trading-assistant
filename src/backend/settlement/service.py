from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from ..award_engine.schemas import AwardResult
from ..notifications.service import get_quote_registry
from .schemas import EvidencePayload, SettlementLegResponse, SettlementResponse

SETTLEMENT_LOG = Path("logs/settlement_events.json")
DISPUTE_LOG = Path("logs/dispute_events.json")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _log(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=True) + "\n")


@dataclass
class SettlementLeg:
    leg_id: str
    provider_telegram_id: int
    leg_type: str  # fiat/usdt
    amount: Decimal
    status: str = "pending"
    deadline: datetime = field(default_factory=lambda: _now() + timedelta(minutes=45))
    evidence: Optional[EvidencePayload] = None
    attempts: int = 0
    reason: Optional[str] = None


@dataclass
class SettlementRecord:
    settlement_id: str
    rfq_id: str
    award_id: str
    status: str = "pending"
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    legs: List[SettlementLeg] = field(default_factory=list)

    def refresh_status(self) -> None:
        statuses = {leg.status for leg in self.legs}
        if statuses == {"verified"}:
            self.status = "settled"
        elif "escalated" in statuses:
            self.status = "disputed"
        elif "submitted" in statuses or "pending" in statuses:
            self.status = "in_progress"
        else:
            self.status = "pending"
        self.updated_at = _now()


class SettlementRegistry:
    """
    Manage settlement lifecycle for Stage 16.
    """

    def __init__(self) -> None:
        self._storage: Dict[str, SettlementRecord] = {}

    def start(self, award: AwardResult) -> SettlementRecord:
        settlement_id = uuid.uuid4().hex
        record = SettlementRecord(
            settlement_id=settlement_id,
            rfq_id=award.rfq_id,
            award_id=award.award_id,
            status="pending",
        )
        for leg in award.legs:
            amount = Decimal(str(leg.awarded_amount))
            fiat_leg = SettlementLeg(
                leg_id=f"{leg.quote_id}-fiat",
                provider_telegram_id=leg.provider_telegram_id,
                leg_type="fiat",
                amount=amount,
                deadline=_now() + timedelta(minutes=45),
            )
            usdt_leg = SettlementLeg(
                leg_id=f"{leg.quote_id}-usdt",
                provider_telegram_id=leg.provider_telegram_id,
                leg_type="usdt",
                amount=amount,
                deadline=_now() + timedelta(minutes=45),
            )
            record.legs.extend([fiat_leg, usdt_leg])
        self._storage[settlement_id] = record
        record.refresh_status()
        _log(
            SETTLEMENT_LOG,
            {
                "event": "settlement_started",
                "settlement_id": settlement_id,
                "rfq_id": award.rfq_id,
                "award_id": award.award_id,
                "legs": [leg.leg_type for leg in record.legs],
                "timestamp": record.created_at.isoformat(),
            },
        )
        return record

    def submit_evidence(self, settlement_id: str, leg_id: str, evidence: EvidencePayload) -> SettlementRecord:
        record = self._storage.get(settlement_id)
        if not record:
            raise KeyError("Settlement not found")
        leg = self._find_leg(record, leg_id)
        if leg.status in {"verified", "escalated"}:
            raise ValueError("leg_already_closed")

        leg.attempts += 1
        errors: List[str] = []
        if evidence.file_size_mb is None or evidence.file_size_mb > 5:
            errors.append("file_size_exceeds_limit")
        if len(evidence.hash) < 16:
            errors.append("hash_too_short")

        if errors:
            if leg.attempts >= 2:
                leg.status = "escalated"
                leg.reason = "invalid_evidence"
                self._escalate(record, leg, "invalid_evidence")
            else:
                leg.status = "pending"
                leg.reason = "invalid_evidence"
            raise ValueError("invalid_evidence")

        leg.evidence = evidence
        leg.status = "submitted"
        leg.reason = None
        record.refresh_status()
        _log(
            SETTLEMENT_LOG,
            {
                "event": "evidence_submitted",
                "settlement_id": settlement_id,
                "leg_id": leg_id,
                "provider": leg.provider_telegram_id,
                "hash": evidence.hash,
                "timestamp": _now().isoformat(),
            },
        )
        return record

    def verify_leg(self, settlement_id: str, leg_id: str, verified: bool, reason: Optional[str]) -> SettlementRecord:
        record = self._storage.get(settlement_id)
        if not record:
            raise KeyError("Settlement not found")
        leg = self._find_leg(record, leg_id)
        if leg.evidence is None:
            raise ValueError("no_evidence_submitted")
        if verified:
            leg.status = "verified"
            leg.reason = None
        else:
            leg.status = "escalated"
            leg.reason = reason or "rejected"
            self._escalate(record, leg, reason or "evidence_rejected")
        record.refresh_status()
        return record

    def check_deadlines(self) -> List[SettlementRecord]:
        updated: List[SettlementRecord] = []
        for record in self._storage.values():
            changed = False
            for leg in record.legs:
                if leg.status in {"pending", "submitted"} and leg.deadline <= _now():
                    leg.status = "escalated"
                    leg.reason = "deadline_missed"
                    changed = True
                    self._escalate(record, leg, "deadline_missed")
            if changed:
                record.refresh_status()
                updated.append(record)
        return updated

    def list(self) -> List[SettlementRecord]:
        return list(self._storage.values())

    def get(self, settlement_id: str) -> SettlementRecord:
        record = self._storage.get(settlement_id)
        if not record:
            raise KeyError("Settlement not found")
        return record

    def _find_leg(self, record: SettlementRecord, leg_id: str) -> SettlementLeg:
        for leg in record.legs:
            if leg.leg_id == leg_id:
                return leg
        raise KeyError("Leg not found")

    def _escalate(self, record: SettlementRecord, leg: SettlementLeg, reason: str) -> None:
        payload = {
            "event": "settlement_escalated",
            "settlement_id": record.settlement_id,
            "rfq_id": record.rfq_id,
            "leg_id": leg.leg_id,
            "provider": leg.provider_telegram_id,
            "reason": reason,
            "timestamp": _now().isoformat(),
        }
        _log(SETTLEMENT_LOG, payload)
        _log(DISPUTE_LOG, payload)


REGISTRY = SettlementRegistry()


def get_registry() -> SettlementRegistry:
    return REGISTRY


def to_response(record: SettlementRecord) -> SettlementResponse:
    return SettlementResponse(
        settlement_id=record.settlement_id,
        rfq_id=record.rfq_id,
        award_id=record.award_id,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        legs=[
            SettlementLegResponse(
                leg_id=leg.leg_id,
                provider_telegram_id=leg.provider_telegram_id,
                leg_type=leg.leg_type,
                amount=float(leg.amount),
                status=leg.status,
                deadline=leg.deadline,
                evidence_hash=leg.evidence.hash if leg.evidence else None,
                attempts=leg.attempts,
                reason=leg.reason,
            )
            for leg in record.legs
        ],
    )
