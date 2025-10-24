from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from ..security import require_roles
from .schemas import BroadcastResponse, QuoteResponse, QuoteSubmissionRequest
from .service import (
    NotificationService,
    QuoteRegistry,
    get_notification_service,
    get_quote_registry,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post(
    "/rfq/{rfq_id}/broadcast",
    response_model=BroadcastResponse,
    dependencies=[Depends(require_roles("operations", "admin", action="notification:broadcast", resource="notification"))],
)
def broadcast_rfq(
    rfq_id: str,
    request: Request,
    service: NotificationService = Depends(get_notification_service),
) -> BroadcastResponse:
    trace_id = request.headers.get("X-Trace-ID", "n/a")
    recipient_count = service.broadcast(rfq_id, trace_id=trace_id)
    return BroadcastResponse(rfq_id=rfq_id, recipients=recipient_count, trace_id=trace_id)


@router.post(
    "/quotes",
    response_model=QuoteResponse,
    dependencies=[Depends(require_roles("provider", "operations", "admin", action="quote:submit", resource="notification"))],
)
def submit_quote(
    payload: QuoteSubmissionRequest,
    registry: QuoteRegistry = Depends(get_quote_registry),
) -> QuoteResponse:
    try:
        return registry.submit(payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="RFQ not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/quotes",
    response_model=List[QuoteResponse],
    dependencies=[Depends(require_roles("operations", "admin", "compliance", action="quote:view", resource="notification"))],
)
def list_quotes(
    rfq_id: Optional[str] = None,
    registry: QuoteRegistry = Depends(get_quote_registry),
) -> List[QuoteResponse]:
    return registry.list(rfq_id=rfq_id)
