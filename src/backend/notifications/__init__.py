"""Notification and Quote handling for Stage 14."""

from .router import router
from .service import NotificationService, QuoteRegistry, get_notification_service, get_quote_registry

__all__ = [
    "NotificationService",
    "QuoteRegistry",
    "get_notification_service",
    "get_quote_registry",
    "router",
]
