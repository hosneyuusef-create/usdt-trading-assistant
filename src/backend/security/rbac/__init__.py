"""RBAC utilities (Stage 12)."""

from .policy import RBAC_POLICY, ROLE_DESCRIPTIONS, ACTION_DESCRIPTIONS, list_policy_matrix
from .dependencies import require_roles, audit_access, POLICY

__all__ = [
    "RBAC_POLICY",
    "ROLE_DESCRIPTIONS",
    "ACTION_DESCRIPTIONS",
    "list_policy_matrix",
    "require_roles",
    "audit_access",
    "POLICY",
]
