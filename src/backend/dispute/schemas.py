"""
Stage 18: Dispute Schemas
Defines data models for dispute filing, evidence submission, and arbitration decisions.
Enforces SLA timelines and Non-custodial documentation requirements.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class DisputeFileRequest(BaseModel):
    """Request to file a dispute on a settlement."""

    settlement_id: str = Field(..., description="Settlement identifier")
    claimant_telegram_id: int = Field(..., description="Telegram ID of the party filing the dispute")
    reason: str = Field(..., min_length=10, max_length=2000, description="Reason for dispute (10-2000 chars)")
    initial_evidence_summary: Optional[str] = Field(None, description="Brief summary of evidence to be submitted")


class EvidenceSubmission(BaseModel):
    """Evidence document submitted by a party."""

    dispute_id: str = Field(..., description="Dispute identifier")
    submitter_telegram_id: int = Field(..., description="Telegram ID of submitter")
    evidence_type: str = Field(..., description="Type: bank_receipt | tx_proof | screenshot | other")
    storage_url: str = Field(..., description="URL or path to stored evidence")
    hash: str = Field(..., min_length=16, description="SHA-256 hash of evidence file")
    metadata: Optional[dict] = Field(None, description="Additional metadata (timestamps, amounts, etc.)")
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes (max 1000 chars)")


class ArbitrationDecision(BaseModel):
    """Admin decision on a dispute."""

    dispute_id: str = Field(..., description="Dispute identifier")
    admin_telegram_id: int = Field(..., description="Admin making the decision")
    decision: str = Field(..., description="Decision: favor_claimant | favor_respondent | partial_favor | inconclusive")
    decision_reason: str = Field(..., min_length=20, max_length=3000, description="Detailed reasoning (20-3000 chars)")
    awarded_to_claimant: Optional[Decimal] = Field(None, description="Amount awarded to claimant (if partial)")
    awarded_to_respondent: Optional[Decimal] = Field(None, description="Amount awarded to respondent (if partial)")
    evidence_reviewed: List[str] = Field(default_factory=list, description="List of evidence IDs reviewed")
    notes: Optional[str] = Field(None, max_length=1000, description="Internal admin notes")


class DisputeResponse(BaseModel):
    """Response with dispute details."""

    dispute_id: str
    settlement_id: str
    claimant_telegram_id: int
    respondent_telegram_id: int
    reason: str
    status: str  # open | awaiting_evidence | under_review | resolved | escalated
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    opened_at: datetime
    evidence_deadline: datetime
    review_deadline: datetime
    decision_deadline: datetime
    decision_at: Optional[datetime] = None
    evidence_count: int = 0
    created_at: datetime
    updated_at: datetime


class DisputeEvidenceResponse(BaseModel):
    """Response with evidence details."""

    evidence_id: str
    dispute_id: str
    submitter_telegram_id: int
    evidence_type: str
    storage_url: str
    hash: str
    metadata: Optional[dict] = None
    notes: Optional[str] = None
    submitted_at: datetime


class DisputeActionResponse(BaseModel):
    """Response with admin action details."""

    action_id: str
    dispute_id: str
    admin_telegram_id: int
    action_type: str  # request_evidence | review_start | decision | escalate | reopen
    notes: Optional[str] = None
    action_at: datetime
