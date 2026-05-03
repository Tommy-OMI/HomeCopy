"""Best-effort desktop notification wrapper."""

from __future__ import annotations

import logging
import os
import subprocess

try:
    from plyer import notification
except Exception:  # pragma: no cover - optional dependency runtime behavior
    notification = None

logger = logging.getLogger(__name__)

POWERSHELL_TOAST_SCRIPT = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null

$title = [System.Security.SecurityElement]::Escape($env:HOMECOPY_NOTIFY_TITLE)
$message = [System.Security.SecurityElement]::Escape($env:HOMECOPY_NOTIFY_MESSAGE)

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml(@"
<toast>
  <visual>
    <binding template="ToastGeneric">
      <text>$title</text>
      <text>$message</text>
    </binding>
  </visual>
</toast>
"@)

$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("HomeCopy")
$notifier.Show($toast)
"""


class NotificationService:
    def notify(self, title: str, message: str) -> None:
        if self._notify_with_powershell(title, message):
            return

        if notification is None:
            logger.info("%s: %s", title, message)
            return

        try:
            notification.notify(title=title, message=message, timeout=5)
        except Exception:
            logger.exception("Failed to display desktop notification")

    def _notify_with_powershell(self, title: str, message: str) -> bool:
        env = os.environ.copy()
        env["HOMECOPY_NOTIFY_TITLE"] = title
        env["HOMECOPY_NOTIFY_MESSAGE"] = message
        try:
            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    POWERSHELL_TOAST_SCRIPT,
                ],
                check=False,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            logger.debug("PowerShell toast notification unavailable", exc_info=True)
            return False
        return completed.returncode == 0
