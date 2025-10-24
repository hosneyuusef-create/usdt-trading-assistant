from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, condecimal, constr


class PartialLeg(BaseModel):
    leg_id: str
    quote_id: str
    provider_telegram_id: int
    amount: condecimal(ge=0, max_digits=18, decimal_places=2)
    status: constr(pattern="^(active|partial|reallocated|cancelled)$")
    updated_at: datetime


class PartialFillResponse(BaseModel):
    rfq_id: str
    award_id: str
    status: str
    remaining_amount: condecimal(ge=0, max_digits=18, decimal_places=2)
    legs: List[PartialLeg]


class ReallocateRequest(BaseModel):
    from_quote_id: str
    to_provider_telegram_id: int
    reallocated_amount: condecimal(ge=0, max_digits=18, decimal_places=2)
    unit_price: condecimal(gt=0, max_digits=12, decimal_places=2)


class CancelRequest(BaseModel):
    quote_id: str
    reason: Optional[str] = None

