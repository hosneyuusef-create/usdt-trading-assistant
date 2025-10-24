from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional, Set

from fastapi import Header, HTTPException, status

from .policy import RBAC_POLICY

AUDIT_LOG_PATH = Path("logs/access_audit.json")
_LOCK = threading.Lock()

POLICY = RBAC_POLICY


def audit_access(
    role: Optional[str],
    action: str,
    resource: str,
    success: bool,
    user_id: str,
    reason: Optional[str] = None,
) -> None:
    """
    Append an access audit entry to logs/access_audit.json (JSON Lines format).
    """

    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "role": role,
        "action": action,
        "resource": resource,
        "success": success,
        "user_id": user_id,
    }
    if reason:
        entry["reason"] = reason

    line = json.dumps(entry, ensure_ascii=True)
    with _LOCK:
        with AUDIT_LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def require_roles(*roles: str, action: str, resource: str = "api"):
    """
    FastAPI dependency enforcing RBAC authorisation.

    Parameters
    ----------
    roles:
        Allowed roles for the protected action.
    action:
        Action name matching RBAC_POLICY.
    resource:
        Logical resource identifier for audit logging.
    """

    allowed: Set[str] = {role.lower() for role in roles}

    def dependency(
        x_role: Optional[str] = Header(default=None, alias="X-Role"),
        user_id: str = Header(default="anonymous", alias="X-User-Id"),
    ):
        if not x_role:
            audit_access(None, action, resource, False, user_id, reason="missing_role_header")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-Role header")

        role = x_role.strip().lower()
        if role not in RBAC_POLICY:
            audit_access(role, action, resource, False, user_id, reason="unknown_role")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not recognised")

        if role not in allowed or action not in RBAC_POLICY[role]:
            audit_access(role, action, resource, False, user_id, reason="forbidden")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        audit_access(role, action, resource, True, user_id)
        return {"role": role, "user_id": user_id}

    return dependency
