from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, condecimal, field_validator


class BroadcastResponse(BaseModel):
    rfq_id: str
    recipients: int
    trace_id: str


class QuoteSubmissionRequest(BaseModel):
    rfq_id: str
    provider_telegram_id: int
    unit_price: condecimal(gt=0, max_digits=12, decimal_places=2)
    capacity: condecimal(gt=0, max_digits=18, decimal_places=2)
    message_id: Optional[str] = None


class QuoteResponse(BaseModel):
    quote_id: str
    rfq_id: str
    provider_telegram_id: int
    unit_price: float
    capacity: float
    submitted_at: datetime
    accepted: bool
    reason: Optional[str] = None
    awarded_amount: Optional[float] = None
