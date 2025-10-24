from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, condecimal, field_validator, model_validator


class SpecialConditions(BaseModel):
    price_ceiling: Optional[condecimal(gt=0, max_digits=12, decimal_places=2)] = None
    split_allowed: bool = False
    specific_providers: Optional[List[str]] = None
    min_fill_percentage: Optional[condecimal(gt=0, le=100, max_digits=5, decimal_places=2)] = None

    @model_validator(mode="after")
    def _normalise_specific_providers(self) -> "SpecialConditions":
        if self.specific_providers:
            unique = []
            seen = set()
            for provider in self.specific_providers:
                value = provider.strip()
                if len(value) < 3:
                    raise ValueError("specific_providers entries must contain at least 3 characters")
                if value not in seen:
                    unique.append(value)
                    seen.add(value)
            self.specific_providers = unique
        return self


class RFQCreateRequest(BaseModel):
    customer_id: str = Field(..., min_length=5)
    customer_telegram_id: Optional[int] = None
    kyc_tier: Literal["basic", "advanced", "premium"]
    rfq_type: Literal["buy", "sell"]
    network: Literal["TRC20", "BEP20", "ERC20"]
    amount: condecimal(gt=0, max_digits=18, decimal_places=2)
    min_fill_amount: Optional[condecimal(gt=0, max_digits=18, decimal_places=2)] = None
    expires_at: datetime
    special_conditions: Optional[SpecialConditions] = None

    @field_validator("expires_at")
    @classmethod
    def check_future(cls, value: datetime) -> datetime:
        value_utc = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if value_utc <= datetime.now(timezone.utc):
            raise ValueError("expires_at must be in the future")
        return value

    @model_validator(mode="after")
    def check_min_fill(self) -> "RFQCreateRequest":
        if self.min_fill_amount and self.min_fill_amount > self.amount:
            raise ValueError("min_fill_amount cannot exceed amount")
        return self


class RFQUpdateRequest(BaseModel):
    amount: Optional[condecimal(gt=0, max_digits=18, decimal_places=2)] = None
    min_fill_amount: Optional[condecimal(gt=0, max_digits=18, decimal_places=2)] = None
    expires_at: Optional[datetime] = None
    special_conditions: Optional[SpecialConditions] = None

    @model_validator(mode="after")
    def ensure_consistency(self) -> "RFQUpdateRequest":
        if self.min_fill_amount and self.amount and self.min_fill_amount > self.amount:
            raise ValueError("min_fill_amount cannot exceed amount")
        return self


class RFQResponse(BaseModel):
    rfq_id: str
    customer_id: str
    customer_telegram_id: Optional[int]
    kyc_tier: str
    rfq_type: str
    network: str
    amount: float
    min_fill_amount: Optional[float]
    status: str
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    special_conditions: Optional[SpecialConditions]
