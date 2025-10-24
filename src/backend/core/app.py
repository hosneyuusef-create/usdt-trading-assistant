from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import Settings, get_settings
from ..services import build_health_payload
from ..customer import router as customer_router
from ..provider import router as provider_router
from ..rfq import router as rfq_router
from ..notifications import router as notifications_router
from ..award_engine import router as award_router
from ..settlement import router as settlement_router
from ..partial_fill import router as partial_fill_router
from ..dispute.router import router as dispute_router

TRACE_HEADER = "X-Trace-ID"


def _generate_trace_id() -> str:
    return uuid.uuid4().hex


class TraceIDMiddleware(BaseHTTPMiddleware):
    """Attach a Trace-ID header to every request/response cycle."""

    async def dispatch(self, request: Request, call_next: Callable):
        trace_id = request.headers.get(TRACE_HEADER, _generate_trace_id())
        request.state.trace_id = trace_id
        response: JSONResponse = await call_next(request)
        response.headers[TRACE_HEADER] = trace_id
        return response


def create_app() -> FastAPI:
    """
    Build the FastAPI application with common middleware and routes.
    """

    app = FastAPI(title="USDT Auction Backend", version="0.1.0")
    app.include_router(customer_router)
    app.include_router(provider_router)
    app.add_middleware(TraceIDMiddleware)

    @app.get("/health", tags=["Internal"])
    def health_check(settings: Settings = Depends(get_settings)):
        """
        Return basic health information. Downstream stages will enrich the
        payload with live dependency checks.
        """

        payload = build_health_payload(settings)
        return payload

    app.include_router(rfq_router)
    app.include_router(notifications_router)
    app.include_router(award_router)
    app.include_router(settlement_router)
    app.include_router(partial_fill_router)
    app.include_router(dispute_router)
    return app




