from __future__ import annotations

import json
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from ..customer.service import _load_policies as load_kyc_policies  # type: ignore  # reuse Stage 10 loader
from .schemas import RFQCreateRequest, RFQResponse, RFQUpdateRequest, SpecialConditions

LOGGER = logging.getLogger("usdt.rfq")
EVENT_LOG = Path("logs/rfq_events.json")
_LOG_LOCK = threading.Lock()


def _write_event(event: Dict[str, object]) -> None:
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=True)
    with _LOG_LOCK:
        with EVENT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def _get_kyc_limit(tier: str) -> Decimal:
    policies = load_kyc_policies()
    policy = policies.get(tier.lower())
    if not policy:
        raise ValueError(f"KYC tier '{tier}' is not recognised")
    return Decimal(str(policy["daily_limit"]))


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RFQRecord:
    rfq_id: str
    customer_id: str
    customer_telegram_id: Optional[int]
    kyc_tier: str
    rfq_type: str
    network: str
    amount: Decimal
    min_fill_amount: Optional[Decimal]
    status: str
    expires_at: datetime
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    special_conditions: Optional[SpecialConditions] = None

    def touch_expiry(self) -> None:
        if self.status == "open" and self.expires_at <= _now():
            self.status = "expired"


class RFQRegistry:
    """
    In-memory RFQ registry for Stage 13.
    """

    def __init__(self) -> None:
        self._storage: Dict[str, RFQRecord] = {}

    def clear(self) -> None:
        self._storage.clear()

    def create(self, payload: RFQCreateRequest) -> RFQResponse:
        limit = _get_kyc_limit(payload.kyc_tier)
        if Decimal(payload.amount) > limit:
            raise ValueError("RFQ amount exceeds KYC tier limit")

        rfq_id = uuid.uuid4().hex
        record = RFQRecord(
            rfq_id=rfq_id,
            customer_id=payload.customer_id,
            customer_telegram_id=payload.customer_telegram_id,
            kyc_tier=payload.kyc_tier,
            rfq_type=payload.rfq_type,
            network=payload.network,
            amount=Decimal(payload.amount),
            min_fill_amount=Decimal(payload.min_fill_amount) if payload.min_fill_amount else None,
            status="open",
            expires_at=payload.expires_at.astimezone(timezone.utc),
            special_conditions=payload.special_conditions,
        )
        self._storage[rfq_id] = record
        LOGGER.info(
            "rfq_created",
            extra={
                "rfq_id": rfq_id,
                "customer_id": record.customer_id,
                "amount": float(record.amount),
                "kyc_tier": record.kyc_tier,
                "expires_at": record.expires_at.isoformat(),
            },
        )
        return self._to_response(record)

    def update(self, rfq_id: str, payload: RFQUpdateRequest) -> RFQResponse:
        record = self._storage.get(rfq_id)
        if not record:
            raise KeyError("RFQ not found")
        record.touch_expiry()
        if record.status != "open":
            raise ValueError("Only open RFQs can be updated")

        if payload.amount is not None:
            limit = _get_kyc_limit(record.kyc_tier)
            if Decimal(payload.amount) > limit:
                raise ValueError("RFQ amount exceeds KYC tier limit")
            record.amount = Decimal(payload.amount)
        if payload.min_fill_amount is not None:
            min_fill = Decimal(payload.min_fill_amount)
            if min_fill > record.amount:
                raise ValueError("min_fill_amount cannot exceed amount")
            record.min_fill_amount = min_fill
        if payload.expires_at is not None:
            new_expiry = payload.expires_at.astimezone(timezone.utc) if payload.expires_at.tzinfo else payload.expires_at.replace(tzinfo=timezone.utc)
            if new_expiry <= datetime.now(timezone.utc):
                raise ValueError("expires_at must be in the future")
            record.expires_at = new_expiry
        if payload.special_conditions is not None:
            record.special_conditions = payload.special_conditions

        record.updated_at = _now()
        LOGGER.info(
            "rfq_updated",
            extra={
                "rfq_id": rfq_id,
                "amount": float(record.amount),
                "min_fill_amount": float(record.min_fill_amount) if record.min_fill_amount else None,
                "expires_at": record.expires_at.isoformat(),
            },
        )
        return self._to_response(record)

    def cancel(self, rfq_id: str, reason: str, actor: str) -> RFQResponse:
        record = self._storage.get(rfq_id)
        if not record:
            raise KeyError("RFQ not found")
        record.touch_expiry()
        if record.status != "open":
            raise ValueError("Only open RFQs can be cancelled")

        record.status = "cancelled"
        record.updated_at = _now()
        event = {
            "timestamp": record.updated_at.isoformat(),
            "rfq_id": rfq_id,
            "customer_id": record.customer_id,
            "actor": actor,
            "reason": reason,
            "event": "rfq_cancelled",
        }
        _write_event(event)
        LOGGER.warning("rfq_cancelled", extra=event)
        return self._to_response(record)

    def get(self, rfq_id: str) -> RFQResponse:
        record = self._storage.get(rfq_id)
        if not record:
            raise KeyError("RFQ not found")
        record.touch_expiry()
        return self._to_response(record)

    def list(self) -> List[RFQResponse]:
        responses: List[RFQResponse] = []
        for record in self._storage.values():
            record.touch_expiry()
            responses.append(self._to_response(record))
        return sorted(responses, key=lambda item: item.created_at, reverse=True)

    def mark_awarded(self, rfq_id: str) -> None:
        record = self._storage.get(rfq_id)
        if not record:
            raise KeyError("RFQ not found")
        record.status = "awarded"
        record.updated_at = _now()


    def _to_response(self, record: RFQRecord) -> RFQResponse:
        return RFQResponse(
            rfq_id=record.rfq_id,
            customer_id=record.customer_id,
            customer_telegram_id=record.customer_telegram_id,
            kyc_tier=record.kyc_tier,
            rfq_type=record.rfq_type,
            network=record.network,
            amount=float(record.amount),
            min_fill_amount=float(record.min_fill_amount) if record.min_fill_amount else None,
            status=record.status,
            expires_at=record.expires_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
            special_conditions=record.special_conditions,
        )


REGISTRY = RFQRegistry()


def get_registry() -> RFQRegistry:
    return REGISTRY
