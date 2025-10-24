from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from .schemas import CustomerRegisterRequest, CustomerResponse

LOGGER = logging.getLogger("usdt.customer")
_POLICY_CACHE: Optional[Dict[str, Dict[str, int]]] = None


def _load_policies() -> Dict[str, Dict[str, int]]:
    global _POLICY_CACHE
    if _POLICY_CACHE is None:
        policy_path = Path("artefacts/Verification_Policies.json")
        with policy_path.open("r", encoding="utf-8-sig") as fh:
            payload = json.load(fh)
        _POLICY_CACHE = {
            tier.lower(): info
            for tier, info in payload.get("tiers", {}).items()
        }
    return _POLICY_CACHE


class CustomerRegistry:
    """
    In-memory registry placeholder for Stage 10.
    """

    def __init__(self) -> None:
        self._storage: Dict[int, CustomerResponse] = {}

    def clear(self) -> None:
        self._storage.clear()

    def register(self, request: CustomerRegisterRequest) -> CustomerResponse:
        policies = _load_policies()
        tier_policy = policies.get(request.kyc_tier)
        if tier_policy is None:
            raise ValueError(f"Unsupported KYC tier: {request.kyc_tier}")

        masked_card = self._mask_card(request.payment_instrument.card_number)
        LOGGER.info(
            "Registering customer %s with masked card %s",
            request.telegram_id,
            masked_card,
        )

        response = CustomerResponse(
            customer_id=uuid.uuid4().hex,
            telegram_id=request.telegram_id,
            kyc_tier=request.kyc_tier,
            daily_limit=int(tier_policy["daily_limit"]),
            masked_card=masked_card,
            registered_at=datetime.now(timezone.utc),
        )
        self._storage[request.telegram_id] = response
        return response

    def get(self, telegram_id: int) -> Optional[CustomerResponse]:
        return self._storage.get(telegram_id)

    @staticmethod
    def _mask_card(card_number: str) -> str:
        digits = "".join(ch for ch in card_number if ch.isdigit())
        if len(digits) < 4:
            raise ValueError("card_number must contain at least 4 digits")
        return f"{'*' * (len(digits) - 4)}{digits[-4:]}"


_REGISTRY = CustomerRegistry()


def get_registry() -> CustomerRegistry:
    return _REGISTRY

