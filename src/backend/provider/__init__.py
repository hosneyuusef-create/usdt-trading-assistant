"""Provider module implementing Stage 11 eligibility workflows."""

from .router import router
from .service import (
    ProviderRegistry,
    evaluate_eligibility,
    filter_eligible_providers,
    get_registry,
)

__all__ = [
    "ProviderRegistry",
    "evaluate_eligibility",
    "filter_eligible_providers",
    "get_registry",
    "router",
]
