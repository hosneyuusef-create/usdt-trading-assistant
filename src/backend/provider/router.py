from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from .schemas import EligibilitySummary, ProviderRegisterRequest, ProviderResponse
from .service import ProviderRegistry, get_registry
from ..security import require_roles

router = APIRouter(prefix="/provider", tags=["Provider"])


@router.post("/register", response_model=ProviderResponse, status_code=201)
def register_provider(
    request: ProviderRegisterRequest,
    registry: ProviderRegistry = Depends(get_registry),
    _: dict = Depends(require_roles("admin", "operations", action="provider:register", resource="provider")),
) -> ProviderResponse:
    return registry.register(request)


@router.get("/eligible", response_model=List[ProviderResponse])
def list_eligible_providers(
    registry: ProviderRegistry = Depends(get_registry),
    _: dict = Depends(require_roles("admin", "operations", "compliance", action="provider:view", resource="provider")),
) -> List[ProviderResponse]:
    return registry.filter_for_rfq()


@router.get("/{telegram_id}/eligibility", response_model=EligibilitySummary)
def get_provider_eligibility(
    telegram_id: int,
    registry: ProviderRegistry = Depends(get_registry),
    _: dict = Depends(require_roles("admin", "operations", "compliance", action="provider:view", resource="provider")),
) -> EligibilitySummary:
    provider = registry.get(telegram_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider.eligibility
