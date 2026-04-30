"""Clipboard integration for incoming text."""

from __future__ import annotations

import pyperclip


class ClipboardService:
    def copy_text(self, text: str) -> None:
        pyperclip.copy(text)
