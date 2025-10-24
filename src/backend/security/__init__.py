"""Security package providing RBAC utilities for the USDT Auction backend."""

from .rbac.dependencies import require_roles, audit_access, POLICY
from .rbac.policy import RBAC_POLICY, ROLE_DESCRIPTIONS, ACTION_DESCRIPTIONS

__all__ = [
    "require_roles",
    "audit_access",
    "RBAC_POLICY",
    "ROLE_DESCRIPTIONS",
    "ACTION_DESCRIPTIONS",
    "POLICY",
]
