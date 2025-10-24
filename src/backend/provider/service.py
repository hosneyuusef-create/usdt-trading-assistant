from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Dict, Iterable, List, Optional, Sequence

from .schemas import EligibilitySummary, ProviderRegisterRequest, ProviderResponse

LOGGER = logging.getLogger("usdt.provider")


def _load_decimal(value: str, fallback: Decimal) -> Decimal:
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return fallback


DEFAULT_MIN_SCORE = Decimal("70")
DEFAULT_MIN_COLLATERAL = 200_000_000

MIN_SCORE = _load_decimal(os.getenv("PROVIDER_MIN_SCORE", "70"), DEFAULT_MIN_SCORE)
MIN_COLLATERAL = int(os.getenv("PROVIDER_MIN_COLLATERAL", DEFAULT_MIN_COLLATERAL))


@dataclass
class ProviderRecord:
    provider_id: str
    telegram_id: int
    display_name: str
    score: float
    collateral_in_rial: int
    is_active: bool
    capabilities: List[str] = field(default_factory=list)
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update(self, request: ProviderRegisterRequest) -> None:
        self.display_name = request.display_name.strip()
        self.score = float(request.score)
        self.collateral_in_rial = int(request.collateral_in_rial)
        self.is_active = request.is_active
        self.capabilities = list(request.capabilities or [])
        self.updated_at = datetime.now(timezone.utc)


class ProviderRegistry:
    """
    In-memory registry for Stage 11 provider workflows.
    """

    def __init__(self, min_score: Decimal = MIN_SCORE, min_collateral: int = MIN_COLLATERAL) -> None:
        self._providers: Dict[int, ProviderRecord] = {}
        self._min_score = Decimal(min_score)
        self._min_collateral = int(min_collateral)

    def clear(self) -> None:
        self._providers.clear()

    def register(self, request: ProviderRegisterRequest) -> ProviderResponse:
        record = self._providers.get(request.telegram_id)
        if record:
            record.update(request)
        else:
            provider_id = uuid.uuid4().hex
            record = ProviderRecord(
                provider_id=provider_id,
                telegram_id=request.telegram_id,
                display_name=request.display_name.strip(),
                score=float(request.score),
                collateral_in_rial=int(request.collateral_in_rial),
                is_active=request.is_active,
                capabilities=list(request.capabilities or []),
            )
            self._providers[request.telegram_id] = record

        decision = self.evaluate(record)
        LOGGER.info(
            "provider_registered",
            extra={
                "provider_id": record.provider_id,
                "telegram_id": record.telegram_id,
                "eligible": decision.is_eligible,
                "reasons": decision.reasons,
                "score": record.score,
                "collateral_in_rial": record.collateral_in_rial,
                "min_score": str(self._min_score),
                "min_collateral": self._min_collateral,
            },
        )
        return self._to_response(record, decision)

    def get(self, telegram_id: int) -> Optional[ProviderResponse]:
        record = self._providers.get(telegram_id)
        if not record:
            return None
        decision = self.evaluate(record)
        return self._to_response(record, decision)

    def evaluate(self, record: ProviderRecord) -> EligibilitySummary:
        reasons: List[str] = []
        if not record.is_active:
            reasons.append("provider_inactive")

        score_value = Decimal(str(record.score))
        if score_value < self._min_score:
            reasons.append("score_below_threshold")

        if record.collateral_in_rial < self._min_collateral:
            reasons.append("insufficient_collateral")

        eligible = len(reasons) == 0
        if eligible:
            LOGGER.debug(
                "provider_eligible",
                extra={
                    "provider_id": record.provider_id,
                    "telegram_id": record.telegram_id,
                    "score": record.score,
                    "collateral_in_rial": record.collateral_in_rial,
                },
            )
        return EligibilitySummary(is_eligible=eligible, reasons=reasons)

    def list_all(self) -> List[ProviderResponse]:
        responses: List[ProviderResponse] = []
        for record in self._providers.values():
            decision = self.evaluate(record)
            responses.append(self._to_response(record, decision))
        return responses

    def filter_for_rfq(self, telegram_ids: Optional[Iterable[int]] = None) -> List[ProviderResponse]:
        if telegram_ids is None:
            candidates: Sequence[ProviderRecord] = list(self._providers.values())
        else:
            candidates = [
                self._providers[telegram_id]
                for telegram_id in telegram_ids
                if telegram_id in self._providers
            ]

        eligible: List[ProviderResponse] = []
        for record in candidates:
            decision = self.evaluate(record)
            LOGGER.info(
                "rfq_eligibility_evaluated",
                extra={
                    "provider_id": record.provider_id,
                    "telegram_id": record.telegram_id,
                    "eligible": decision.is_eligible,
                    "reasons": decision.reasons,
                },
            )
            if decision.is_eligible:
                eligible.append(self._to_response(record, decision))
        return eligible

    def _to_response(self, record: ProviderRecord, decision: EligibilitySummary) -> ProviderResponse:
        return ProviderResponse(
            provider_id=record.provider_id,
            telegram_id=record.telegram_id,
            display_name=record.display_name,
            score=record.score,
            collateral_in_rial=record.collateral_in_rial,
            is_active=record.is_active,
            capabilities=list(record.capabilities),
            registered_at=record.registered_at,
            updated_at=record.updated_at,
            eligibility=decision,
        )


REGISTRY = ProviderRegistry()


def get_registry() -> ProviderRegistry:
    return REGISTRY


def evaluate_eligibility(telegram_id: int) -> Optional[EligibilitySummary]:
    record = REGISTRY._providers.get(telegram_id)  # noqa: SLF001 - internal access for helper
    if not record:
        return None
    return REGISTRY.evaluate(record)


def filter_eligible_providers(telegram_ids: Optional[Iterable[int]] = None) -> List[ProviderResponse]:
    return REGISTRY.filter_for_rfq(telegram_ids)
