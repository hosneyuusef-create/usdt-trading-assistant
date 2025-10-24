from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, conint, confloat, conlist, constr, model_validator


class EvidenceAmounts(BaseModel):
    fiat: confloat(gt=0)
    usdt: confloat(gt=0)


class EvidencePayload(BaseModel):
    hash: constr(min_length=16, max_length=128)
    issuer: constr(min_length=3)
    payer: constr(min_length=3)
    payee: constr(min_length=3)
    amounts: EvidenceAmounts
    txId: constr(min_length=6)
    network: constr(min_length=3)
    claimedConfirmations: conint(ge=0)
    metadata: Optional[dict] = None
    file_name: Optional[str] = Field(default=None, max_length=128)
    file_size_mb: Optional[confloat(gt=0)] = None


class SubmitEvidenceRequest(BaseModel):
    evidence: EvidencePayload


class VerifyLegRequest(BaseModel):
    verified: bool
    reason: Optional[str] = None


class SettlementLegResponse(BaseModel):
    leg_id: str
    provider_telegram_id: int
    leg_type: constr(pattern="^(fiat|usdt)$")
    amount: float
    status: str
    deadline: datetime
    evidence_hash: Optional[str] = None
    attempts: int
    reason: Optional[str] = None


class SettlementResponse(BaseModel):
    settlement_id: str
    rfq_id: str
    award_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    legs: List[SettlementLegResponse]
