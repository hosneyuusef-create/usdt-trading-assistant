from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Header

from ..security import require_roles
from .schemas import RFQCreateRequest, RFQResponse, RFQUpdateRequest
from .service import RFQRegistry, get_registry

router = APIRouter(prefix="/rfq", tags=["RFQ"])


@router.post(
    "",
    response_model=RFQResponse,
    status_code=201,
    dependencies=[Depends(require_roles("customer", "operations", "admin", action="rfq:create", resource="rfq"))],
)
def create_rfq(
    request: RFQCreateRequest,
    registry: RFQRegistry = Depends(get_registry),
) -> RFQResponse:
    try:
        return registry.create(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put(
    "/{rfq_id}",
    response_model=RFQResponse,
    dependencies=[Depends(require_roles("operations", "admin", action="rfq:update", resource="rfq"))],
)
def update_rfq(
    rfq_id: str,
    request: RFQUpdateRequest,
    registry: RFQRegistry = Depends(get_registry),
) -> RFQResponse:
    try:
        return registry.update(rfq_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/{rfq_id}/cancel",
    response_model=RFQResponse,
    dependencies=[Depends(require_roles("operations", "admin", action="rfq:cancel", resource="rfq"))],
)
def cancel_rfq(
    rfq_id: str,
    reason: str,
    registry: RFQRegistry = Depends(get_registry),
    x_user_id: str = Header(default="anonymous", alias="X-User-Id"),
) -> RFQResponse:
    try:
        return registry.cancel(rfq_id, reason=reason, actor=x_user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/{rfq_id}",
    response_model=RFQResponse,
    dependencies=[Depends(require_roles("customer", "operations", "admin", "compliance", action="rfq:view", resource="rfq"))],
)
def get_rfq(
    rfq_id: str,
    registry: RFQRegistry = Depends(get_registry),
) -> RFQResponse:
    try:
        return registry.get(rfq_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="RFQ not found") from None


@router.get(
    "",
    response_model=List[RFQResponse],
    dependencies=[Depends(require_roles("operations", "admin", "compliance", action="rfq:view", resource="rfq"))],
)
def list_rfqs(
    registry: RFQRegistry = Depends(get_registry),
) -> List[RFQResponse]:
    return registry.list()
