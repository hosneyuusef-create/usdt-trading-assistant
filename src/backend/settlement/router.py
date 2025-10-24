from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..security import require_roles
from ..award_engine.schemas import AwardResult
from .schemas import SettlementResponse, SubmitEvidenceRequest, VerifyLegRequest
from .service import get_registry, to_response

router = APIRouter(prefix="/settlement", tags=["Settlement"])


@router.post(
    "/start",
    response_model=SettlementResponse,
    dependencies=[Depends(require_roles("operations", "admin", action="settlement:start", resource="settlement"))],
)
def start_settlement(
    award: AwardResult,
):
    registry = get_registry()
    record = registry.start(award)
    return to_response(record)


@router.post(
    "/{settlement_id}/legs/{leg_id}/evidence",
    response_model=SettlementResponse,
    dependencies=[Depends(require_roles("provider", action="settlement:submit_evidence", resource="settlement"))],
)
def submit_evidence(
    settlement_id: str,
    leg_id: str,
    request: SubmitEvidenceRequest,
):
    registry = get_registry()
    try:
        record = registry.submit_evidence(settlement_id, leg_id, request.evidence)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return to_response(record)


@router.post(
    "/{settlement_id}/legs/{leg_id}/verify",
    response_model=SettlementResponse,
    dependencies=[Depends(require_roles("operations", "admin", action="settlement:verify", resource="settlement"))],
)
def verify_leg(
    settlement_id: str,
    leg_id: str,
    request: VerifyLegRequest,
):
    registry = get_registry()
    try:
        record = registry.verify_leg(settlement_id, leg_id, request.verified, request.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return to_response(record)


@router.post(
    "/deadlines/check",
    response_model=List[SettlementResponse],
    dependencies=[Depends(require_roles("operations", "admin", action="settlement:verify", resource="settlement"))],
)
def check_deadlines():
    registry = get_registry()
    updated = registry.check_deadlines()
    return [to_response(record) for record in updated]


@router.get(
    "/{settlement_id}",
    response_model=SettlementResponse,
    dependencies=[Depends(require_roles("operations", "admin", "compliance", action="settlement:view", resource="settlement"))],
)
def get_settlement(settlement_id: str):
    registry = get_registry()
    try:
        record = registry.get(settlement_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Settlement not found") from None
    return to_response(record)


@router.get(
    "",
    response_model=List[SettlementResponse],
    dependencies=[Depends(require_roles("operations", "admin", "compliance", action="settlement:view", resource="settlement"))],
)
def list_settlements():
    registry = get_registry()
    return [to_response(record) for record in registry.list()]
