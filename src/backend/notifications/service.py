from __future__ import annotations

import json
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..provider.service import get_registry as get_provider_registry
from ..rfq.service import get_registry as get_rfq_registry
from ..rfq.service import RFQRegistry
from ..provider.service import ProviderRegistry
from .schemas import QuoteResponse, QuoteSubmissionRequest

LOGGER = logging.getLogger("usdt.notifications")
QUOTE_LOG = Path("logs/quote_events.json")
NOTIFICATION_LOG = Path("logs/notification_events.json")
_LOG_LOCK = threading.Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _log_event(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=True)
    with _LOG_LOCK:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


class NotificationService:
    """
    Broadcast RFQs to eligible providers (Stage 14 placeholder).
    """

    def __init__(self, provider_registry: ProviderRegistry, rfq_registry: RFQRegistry) -> None:
        self._provider_registry = provider_registry
        self._rfq_registry = rfq_registry

    def broadcast(self, rfq_id: str, trace_id: str) -> int:
        rfq = self._rfq_registry.get(rfq_id)
        candidates = self._provider_registry.filter_for_rfq()
        anonymised = len(candidates)
        payload = {
            "timestamp": _now().isoformat(),
            "rfq_id": rfq_id,
            "candidate_count": anonymised,
            "trace_id": trace_id,
        }
        _log_event(NOTIFICATION_LOG, payload)
        LOGGER.info("rfq_broadcast", extra=payload)
        return anonymised


@dataclass
class QuoteRecord:
    quote_id: str
    rfq_id: str
    provider_telegram_id: int
    unit_price: Decimal
    capacity: Decimal
    submitted_at: datetime = field(default_factory=_now)
    accepted: bool = True
    reason: Optional[str] = None
    awarded_amount: Optional[Decimal] = None


class QuoteRegistry:
    """
    Handle quote submissions with rate limiting and expiry enforcement.
    """

    RATE_LIMIT_WINDOW = timedelta(seconds=45)
    MAX_QUOTES_PER_WINDOW = 1

    def __init__(self, provider_registry: ProviderRegistry, rfq_registry: RFQRegistry) -> None:
        self._provider_registry = provider_registry
        self._rfq_registry = rfq_registry
        self._quotes: Dict[str, List[QuoteRecord]] = {}
        self._submission_times: Dict[Tuple[int, str], List[datetime]] = {}

    def submit(self, payload: QuoteSubmissionRequest) -> QuoteResponse:
        provider = self._provider_registry.get(payload.provider_telegram_id)
        if not provider or not provider.eligibility.is_eligible:
            raise ValueError("provider_not_eligible")

        rfq = self._rfq_registry.get(payload.rfq_id)
        if rfq.expires_at <= _now():
            record = QuoteRecord(
                quote_id=uuid.uuid4().hex,
                rfq_id=payload.rfq_id,
                provider_telegram_id=payload.provider_telegram_id,
                unit_price=Decimal(payload.unit_price),
                capacity=Decimal(payload.capacity),
                accepted=False,
                reason="rfq_expired",
            )
            self._store(record)
            self._emit_event(record, message_id=payload.message_id)
            raise ValueError("rfq_expired")

        if rfq.status != "open":
            record = QuoteRecord(
                quote_id=uuid.uuid4().hex,
                rfq_id=payload.rfq_id,
                provider_telegram_id=payload.provider_telegram_id,
                unit_price=Decimal(payload.unit_price),
                capacity=Decimal(payload.capacity),
                accepted=False,
                reason="rfq_closed",
            )
            self._store(record)
            self._emit_event(record, message_id=payload.message_id)
            raise ValueError("rfq_closed")

        if Decimal(payload.capacity) > Decimal(rfq.amount):
            raise ValueError("capacity_exceeds_amount")

        if not self._is_within_rate_limit(payload.provider_telegram_id, payload.rfq_id):
            record = QuoteRecord(
                quote_id=uuid.uuid4().hex,
                rfq_id=payload.rfq_id,
                provider_telegram_id=payload.provider_telegram_id,
                unit_price=Decimal(payload.unit_price),
                capacity=Decimal(payload.capacity),
                accepted=False,
                reason="rate_limited",
            )
            self._store(record)
            self._emit_event(record, message_id=payload.message_id)
            raise ValueError("rate_limited")

        record = QuoteRecord(
            quote_id=uuid.uuid4().hex,
            rfq_id=payload.rfq_id,
            provider_telegram_id=payload.provider_telegram_id,
            unit_price=Decimal(payload.unit_price),
            capacity=Decimal(payload.capacity),
        )
        self._store(record)
        self._emit_event(record, message_id=payload.message_id)
        LOGGER.info(
            "quote_submitted",
            extra={
                "quote_id": record.quote_id,
                "rfq_id": record.rfq_id,
                "provider_telegram_id": record.provider_telegram_id,
                "unit_price": float(record.unit_price),
                "capacity": float(record.capacity),
            },
        )
        return self._to_response(record)

    def list(self, rfq_id: Optional[str] = None) -> List[QuoteResponse]:
        records: List[QuoteRecord] = []
        if rfq_id:
            records.extend(self._quotes.get(rfq_id, []))
        else:
            for recs in self._quotes.values():
                records.extend(recs)
        return [self._to_response(record) for record in records]

    def list_records(self, rfq_id: str) -> List[QuoteRecord]:
        return list(self._quotes.get(rfq_id, []))

    def mark_awards(self, rfq_id: str, awards: Dict[str, Decimal]) -> None:
        records = self._quotes.get(rfq_id, [])
        award_ids = set(awards.keys())
        for record in records:
            if record.quote_id in award_ids:
                record.accepted = True
                record.awarded_amount = awards[record.quote_id]
                record.reason = None
            else:
                record.accepted = False
                record.awarded_amount = None
                if record.reason is None:
                    record.reason = "not_selected"
        # refresh log entries for auditing
        for record in records:
            self._emit_event(record, message_id=None)

    def _is_within_rate_limit(self, provider_telegram_id: int, rfq_id: str) -> bool:
        window_start = _now() - self.RATE_LIMIT_WINDOW
        key = (provider_telegram_id, rfq_id)
        timestamps = self._submission_times.setdefault(key, [])
        # prune
        timestamps[:] = [ts for ts in timestamps if ts >= window_start]
        if len(timestamps) >= self.MAX_QUOTES_PER_WINDOW:
            return False
        timestamps.append(_now())
        return True

    def _store(self, record: QuoteRecord) -> None:
        bucket = self._quotes.setdefault(record.rfq_id, [])
        bucket.append(record)

    def _emit_event(self, record: QuoteRecord, message_id: Optional[str]) -> None:
        payload = {
            "timestamp": record.submitted_at.isoformat(),
            "quote_id": record.quote_id,
            "rfq_id": record.rfq_id,
            "provider_telegram_id": record.provider_telegram_id,
            "unit_price": float(record.unit_price),
            "capacity": float(record.capacity),
            "accepted": record.accepted,
            "reason": record.reason,
        }
        if message_id:
            payload["message_id"] = message_id
        _log_event(QUOTE_LOG, payload)

    def _to_response(self, record: QuoteRecord) -> QuoteResponse:
        return QuoteResponse(
            quote_id=record.quote_id,
            rfq_id=record.rfq_id,
            provider_telegram_id=record.provider_telegram_id,
            unit_price=float(record.unit_price),
            capacity=float(record.capacity),
            submitted_at=record.submitted_at,
            accepted=record.accepted,
            reason=record.reason,
            awarded_amount=float(record.awarded_amount) if record.awarded_amount is not None else None,
        )


_NOTIFICATION_SERVICE = NotificationService(get_provider_registry(), get_rfq_registry())
_QUOTE_REGISTRY = QuoteRegistry(get_provider_registry(), get_rfq_registry())


def get_notification_service() -> NotificationService:
    return _NOTIFICATION_SERVICE


def get_quote_registry() -> QuoteRegistry:
    return _QUOTE_REGISTRY
