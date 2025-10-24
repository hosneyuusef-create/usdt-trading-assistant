from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, conint, confloat, constr


class ProviderRegisterRequest(BaseModel):
    telegram_id: int
    display_name: constr(strip_whitespace=True, min_length=3)
    score: confloat(ge=0, le=100)
    collateral_in_rial: conint(ge=0)
    is_active: bool = True
    capabilities: Optional[List[constr(strip_whitespace=True, min_length=2)]] = None


class EligibilitySummary(BaseModel):
    is_eligible: bool
    reasons: List[str] = Field(default_factory=list)


class ProviderResponse(BaseModel):
    provider_id: str
    telegram_id: int
    display_name: str
    score: float
    collateral_in_rial: int
    is_active: bool
    capabilities: List[str] = Field(default_factory=list)
    registered_at: datetime
    updated_at: datetime
    eligibility: EligibilitySummary
