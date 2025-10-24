from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, condecimal


class AwardLeg(BaseModel):
    quote_id: str
    provider_telegram_id: int
    awarded_amount: condecimal(gt=0, max_digits=18, decimal_places=2)
    unit_price: condecimal(gt=0, max_digits=12, decimal_places=2)
    submitted_at: datetime


class AwardResult(BaseModel):
    award_id: str
    rfq_id: str
    selection_mode: str = "auto"
    tie_break_rule: str
    total_awarded: condecimal(gt=0, max_digits=18, decimal_places=2)
    remaining_amount: condecimal(ge=0, max_digits=18, decimal_places=2)
    legs: List[AwardLeg]
    generated_at: datetime
