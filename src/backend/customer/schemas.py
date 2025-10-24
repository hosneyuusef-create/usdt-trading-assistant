from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, constr, field_validator

TierType = constr(strip_whitespace=True, to_lower=True)


class PaymentInstrument(BaseModel):
    card_number: constr(strip_whitespace=True, min_length=12, max_length=19)
    card_holder: constr(strip_whitespace=True, min_length=3)
    bank_name: Optional[str] = None


class CustomerRegisterRequest(BaseModel):
    telegram_id: int
    full_name: constr(strip_whitespace=True, min_length=3)
    kyc_tier: TierType
    wallet_address: constr(strip_whitespace=True, min_length=3)
    payment_instrument: PaymentInstrument


class CustomerResponse(BaseModel):
    customer_id: str
    telegram_id: int
    kyc_tier: str
    daily_limit: int
    masked_card: str
    registered_at: datetime

    @field_validator("masked_card")
    def ensure_masked(cls, value: str) -> str:
        if value and value.count("*") < 6:
            raise ValueError("masked_card must be masked")
        return value

