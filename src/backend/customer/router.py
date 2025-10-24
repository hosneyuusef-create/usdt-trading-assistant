from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .schemas import CustomerRegisterRequest, CustomerResponse
from .service import CustomerRegistry, get_registry

router = APIRouter(prefix="/customer", tags=["Customer"])


@router.post("/register", response_model=CustomerResponse, status_code=201)
def register_customer(
    request: CustomerRegisterRequest,
    registry: CustomerRegistry = Depends(get_registry),
) -> CustomerResponse:
    try:
        existing = registry.get(request.telegram_id)
        if existing:
            return existing
        return registry.register(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

