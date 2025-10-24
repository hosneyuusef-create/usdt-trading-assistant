from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..security import require_roles
from ..award_engine.schemas import AwardResult
from .schemas import CancelRequest, PartialFillResponse, ReallocateRequest
from .service import get_registry, to_response

router = APIRouter(prefix="/partial-fill", tags=["Partial Fill"])


@router.post(
    "/start",
    response_model=PartialFillResponse,
    dependencies=[Depends(require_roles("operations", "admin", action="partial_fill:reallocate", resource="partial_fill"))],
)
def start_partial_fill(award: AwardResult):
    record = get_registry().start(award)
    return to_response(record)


@router.post(
    "/{rfq_id}/reallocate",
    response_model=PartialFillResponse,
    dependencies=[Depends(require_roles("operations", "admin", action="partial_fill:reallocate", resource="partial_fill"))],
)
def reallocate(rfq_id: str, request: ReallocateRequest):
    try:
        record = get_registry().reallocate(rfq_id, request)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return to_response(record)


@router.post(
    "/{rfq_id}/cancel",
    response_model=PartialFillResponse,
    dependencies=[Depends(require_roles("operations", "admin", action="partial_fill:cancel", resource="partial_fill"))],
)
def cancel_leg(rfq_id: str, request: CancelRequest):
    try:
        record = get_registry().cancel_leg(rfq_id, request)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return to_response(record)


@router.get(
    "/{rfq_id}",
    response_model=PartialFillResponse,
    dependencies=[Depends(require_roles("operations", "admin", "compliance", action="partial_fill:view", resource="partial_fill"))],
)
def get_partial_fill(rfq_id: str):
    try:
        record = get_registry().get(rfq_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="RFQ not found") from None
    return to_response(record)


@router.get(
    "",
    response_model=List[PartialFillResponse],
    dependencies=[Depends(require_roles("operations", "admin", "compliance", action="partial_fill:view", resource="partial_fill"))],
)
def list_partial_fill():
    registry = get_registry()
    return [to_response(record) for record in registry.list()]

