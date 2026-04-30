"""Best-effort desktop notification wrapper."""

from __future__ import annotations

import logging

try:
    from plyer import notification
except Exception:  # pragma: no cover - optional dependency runtime behavior
    notification = None

logger = logging.getLogger(__name__)


class NotificationService:
    def notify(self, title: str, message: str) -> None:
        if notification is None:
            logger.info("%s: %s", title, message)
            return

        try:
            notification.notify(title=title, message=message, timeout=5)
        except Exception:
            logger.exception("Failed to display desktop notification")
