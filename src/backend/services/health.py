"""
Utility helpers for service health checks.

The real implementations will be provided in later stages when database,
messaging and external integrations are available.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from ..config import Settings


def build_health_payload(settings: Settings) -> Dict[str, object]:
    """
    Prepare a simple health payload.

    Parameters
    ----------
    settings:
        Application settings used to surface configuration metadata.

    Returns
    -------
    dict
        JSON-serialisable dictionary with minimal liveness information.
    """

    return {
        "status": "ok",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "services": {
            "database": "not_checked",
            "rabbitmq": "not_checked",
            "telegram": "not_checked",
        },
        "version": settings.api_version,
    }

