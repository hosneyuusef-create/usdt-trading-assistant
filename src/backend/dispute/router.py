"""
Stage 18: Dispute Router
FastAPI endpoints for dispute management, evidence submission, and arbitration decisions.
Enforces RBAC and SLA validation.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from ..security.rbac.dependencies import require_roles
from .schemas import (
    ArbitrationDecision,
    DisputeActionResponse,
    DisputeEvidenceResponse,
    DisputeFileRequest,
    DisputeResponse,
    EvidenceSubmission,
)
from .service import get_registry

router = APIRouter(prefix="/dispute", tags=["dispute"])


@router.post("/file", response_model=DisputeResponse)
def file_dispute(
    request: DisputeFileRequest,
    respondent_telegram_id: int,
    _auth: dict = Depends(require_roles("customer", "provider", action="dispute:file", resource="dispute")),
):
    """
    File a new dispute on a settlement.
    Immediately triggers evidence request to both parties.
    SLA: Evidence window opens for 30 minutes.
    """
    try:
        registry = get_registry()
        return registry.file_dispute(request, respondent_telegram_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/evidence", response_model=DisputeEvidenceResponse)
def submit_evidence(
    submission: EvidenceSubmission,
    _auth: dict = Depends(require_roles("customer", "provider", action="dispute:submit_evidence", resource="dispute")),
):
    """
    Submit evidence for a dispute.
    Must be within 30-minute evidence window.
    Non-custodial: System stores hash and metadata only.
    """
    try:
        registry = get_registry()
        return registry.submit_evidence(submission)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/review/{dispute_id}", response_model=DisputeActionResponse)
def start_review(
    dispute_id: str,
    admin_telegram_id: int,
    _auth: dict = Depends(require_roles("admin", action="dispute:review", resource="dispute")),
):
    """
    Start review process on a dispute.
    Must be after evidence deadline and before review deadline.
    SLA: Review window is 30-90 minutes from filing.
    """
    try:
        registry = get_registry()
        return registry.start_review(dispute_id, admin_telegram_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/decision", response_model=DisputeResponse)
def make_decision(
    decision: ArbitrationDecision,
    _auth: dict = Depends(require_roles("admin", action="dispute:decide", resource="dispute")),
):
    """
    Make arbitration decision on a dispute.
    Must be within 4-hour decision deadline from filing.
    SLA: Final decision ≤4 hours from dispute filing.
    """
    try:
        registry = get_registry()
        return registry.make_decision(decision)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/escalate/{dispute_id}", response_model=DisputeActionResponse)
def escalate_dispute(
    dispute_id: str,
    admin_telegram_id: int,
    reason: str,
    _auth: dict = Depends(require_roles("admin", action="dispute:escalate", resource="dispute")),
):
    """
    Escalate dispute to higher authority.
    Used when SLA is breached or resolution is inconclusive.
    """
    try:
        registry = get_registry()
        return registry.escalate(dispute_id, admin_telegram_id, reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{dispute_id}", response_model=DisputeResponse)
def get_dispute(
    dispute_id: str,
    _auth: dict = Depends(require_roles("admin", "customer", "provider", action="dispute:get", resource="dispute")),
):
    """
    Get dispute details.
    Returns complete dispute record including SLA deadlines and current status.
    """
    try:
        registry = get_registry()
        return registry.get_dispute(dispute_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/", response_model=List[DisputeResponse])
def list_disputes(
    status: Optional[str] = None,
    _auth: dict = Depends(require_roles("admin", action="dispute:list", resource="dispute")),
):
    """
    List all disputes, optionally filtered by status.
    Status values: open | awaiting_evidence | under_review | resolved | escalated
    """
    registry = get_registry()
    return registry.list_disputes(status)


@router.get("/{dispute_id}/evidence", response_model=List[DisputeEvidenceResponse])
def get_evidence(
    dispute_id: str,
    _auth: dict = Depends(require_roles("admin", action="dispute:get_evidence", resource="dispute")),
):
    """
    Get all evidence submitted for a dispute.
    Returns hash and metadata only (Non-custodial principle).
    """
    registry = get_registry()
    return registry.get_evidence(dispute_id)
