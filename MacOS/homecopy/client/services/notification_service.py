"""Best-effort desktop notification wrapper."""

from __future__ import annotations

import logging
import subprocess

try:
    from plyer import notification
except Exception:  # pragma: no cover - optional dependency runtime behavior
    notification = None

logger = logging.getLogger(__name__)


def _apple_script_literal(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


class NotificationService:
    def notify(self, title: str, message: str) -> None:
        if self._notify_with_osascript(title, message):
            return

        if notification is None:
            logger.info("%s: %s", title, message)
            return

        try:
            notification.notify(title=title, message=message, timeout=5)
        except Exception:
            logger.exception("Failed to display desktop notification")

    def _notify_with_osascript(self, title: str, message: str) -> bool:
        script = f"display notification {_apple_script_literal(message)} with title {_apple_script_literal(title)}"
        try:
            completed = subprocess.run(
                ["osascript", "-e", script],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            logger.debug("osascript notification unavailable", exc_info=True)
            return False
        return completed.returncode == 0
