"""Global hotkey registration for the HomeCopy desktop client."""

from __future__ import annotations

import ctypes
import sys
import threading
from typing import Callable

from PySide6.QtCore import QObject, Signal

if sys.platform == "darwin":
    keyboard = None
    try:
        from AppKit import (
            NSEvent,
            NSEventMaskKeyDown,
            NSEventModifierFlagCommand,
            NSEventModifierFlagControl,
            NSEventModifierFlagOption,
            NSEventModifierFlagShift,
        )
    except Exception:  # pragma: no cover - optional runtime dependency behavior
        NSEvent = None
        NSEventMaskKeyDown = 0
        NSEventModifierFlagCommand = 0
        NSEventModifierFlagControl = 0
        NSEventModifierFlagOption = 0
        NSEventModifierFlagShift = 0
else:
    try:
        from pynput import keyboard
    except Exception:  # pragma: no cover - optional runtime dependency behavior
        keyboard = None


_KEY_NAME_MAP = {
    "Ctrl": "<ctrl>",
    "Alt": "<alt>",
    "Option": "<alt>",
    "Shift": "<shift>",
    "Meta": "<cmd>",
    "Cmd": "<cmd>",
    "Command": "<cmd>",
    "Win": "<cmd>",
    "Space": "<space>",
    "Tab": "<tab>",
    "Esc": "<esc>",
    "Escape": "<esc>",
    "Enter": "<enter>",
    "Return": "<enter>",
    "Delete": "<delete>",
    "Backspace": "<backspace>",
    "Up": "<up>",
    "Down": "<down>",
    "Left": "<left>",
    "Right": "<right>",
    "Home": "<home>",
    "End": "<end>",
    "PageUp": "<page_up>",
    "PageDown": "<page_down>",
    "Insert": "<insert>",
}

_MACOS_KEY_CODE_MAP = {
    "A": 0,
    "S": 1,
    "D": 2,
    "F": 3,
    "H": 4,
    "G": 5,
    "Z": 6,
    "X": 7,
    "C": 8,
    "V": 9,
    "B": 11,
    "Q": 12,
    "W": 13,
    "E": 14,
    "R": 15,
    "Y": 16,
    "T": 17,
    "1": 18,
    "2": 19,
    "3": 20,
    "4": 21,
    "6": 22,
    "5": 23,
    "9": 25,
    "7": 26,
    "8": 28,
    "0": 29,
    "O": 31,
    "U": 32,
    "I": 34,
    "P": 35,
    "L": 37,
    "J": 38,
    "K": 40,
    ";": 41,
    "\\": 42,
    ",": 43,
    "/": 44,
    "N": 45,
    "M": 46,
    ".": 47,
    "TAB": 48,
    "SPACE": 49,
    "`": 50,
    "ESC": 53,
    "ESCAPE": 53,
    "ENTER": 36,
    "RETURN": 36,
    "DELETE": 51,
    "BACKSPACE": 51,
}


def qkeysequence_to_pynput(sequence_text: str) -> str:
    tokens = [token.strip() for token in sequence_text.split("+") if token.strip()]
    converted: list[str] = []
    for token in tokens:
        if token in _KEY_NAME_MAP:
            converted.append(_KEY_NAME_MAP[token])
            continue

        upper = token.upper()
        if upper.startswith("F") and upper[1:].isdigit():
            converted.append(f"<{upper.lower()}>")
            continue

        if len(token) == 1:
            converted.append(token.lower())
            continue

        raise ValueError(f"Unsupported hotkey token: {token}")

    if not converted:
        raise ValueError("Hotkey cannot be empty.")
    return "+".join(converted)


if sys.platform == "darwin":
    def qkeysequence_to_macos(sequence_text: str) -> tuple[int, int]:
        tokens = [token.strip() for token in sequence_text.split("+") if token.strip()]
        if not tokens:
            raise ValueError("Hotkey cannot be empty.")

        modifiers = 0
        key_code: int | None = None
        modifier_tokens = {
            "Ctrl": int(NSEventModifierFlagControl),
            "Control": int(NSEventModifierFlagControl),
            "Alt": int(NSEventModifierFlagOption),
            "Option": int(NSEventModifierFlagOption),
            "Shift": int(NSEventModifierFlagShift),
            "Meta": int(NSEventModifierFlagCommand),
            "Cmd": int(NSEventModifierFlagCommand),
            "Command": int(NSEventModifierFlagCommand),
            "Win": int(NSEventModifierFlagCommand),
        }
        function_key_codes = {
            1: 122,
            2: 120,
            3: 99,
            4: 118,
            5: 96,
            6: 97,
            7: 98,
            8: 100,
            9: 101,
            10: 109,
            11: 103,
            12: 111,
        }

        for token in tokens:
            if token in modifier_tokens:
                modifiers |= modifier_tokens[token]
                continue

            upper = token.upper()
            if upper.startswith("F") and upper[1:].isdigit():
                number = int(upper[1:])
                if number in function_key_codes:
                    key_code = function_key_codes[number]
                    continue

            mapped = _MACOS_KEY_CODE_MAP.get(upper)
            if mapped is not None:
                key_code = mapped
                continue

            if len(token) == 1:
                mapped = _MACOS_KEY_CODE_MAP.get(token.upper())
                if mapped is not None:
                    key_code = mapped
                    continue

            raise ValueError(f"Unsupported hotkey token: {token}")

        if key_code is None:
            raise ValueError("Hotkey must include a non-modifier key.")
        return modifiers, key_code


if sys.platform == "win32":
    from ctypes import wintypes

    def qkeysequence_to_windows(sequence_text: str) -> tuple[int, int]:
        MOD_ALT = 0x0001
        MOD_CONTROL = 0x0002
        MOD_SHIFT = 0x0004
        MOD_WIN = 0x0008
        windows_modifiers = {
            "Ctrl": MOD_CONTROL,
            "Alt": MOD_ALT,
            "Shift": MOD_SHIFT,
            "Meta": MOD_WIN,
            "Win": MOD_WIN,
        }
        tokens = [token.strip() for token in sequence_text.split("+") if token.strip()]
        if not tokens:
            raise ValueError("Hotkey cannot be empty.")

        modifiers = 0
        virtual_key = 0
        for token in tokens:
            if token in windows_modifiers:
                modifiers |= windows_modifiers[token]
                continue

            upper = token.upper()
            if len(token) == 1 and token.isalnum():
                virtual_key = ord(upper)
                continue
            if upper.startswith("F") and upper[1:].isdigit():
                number = int(upper[1:])
                if 1 <= number <= 24:
                    virtual_key = 0x70 + number - 1
                    continue
            if token == "Space":
                virtual_key = 0x20
                continue

            raise ValueError(f"Unsupported hotkey token: {token}")

        if virtual_key == 0:
            raise ValueError("Hotkey must include a non-modifier key.")
        return modifiers, virtual_key


class GlobalHotkeyManager(QObject):
    activated = Signal()
    registration_failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.listener: keyboard.Listener | None = None if keyboard else None
        self.hotkey: keyboard.HotKey | None = None if keyboard else None
        self.is_windows_native = sys.platform == "win32"
        self.is_macos_native = sys.platform == "darwin"
        self.windows_hotkey_id = 0xA17
        self.windows_thread: threading.Thread | None = None
        self.windows_thread_id: int | None = None
        self.windows_stop_event = threading.Event()
        self.windows_ready_event = threading.Event()
        self.macos_global_monitor = None
        self.macos_local_monitor = None
        self.macos_global_handler = None
        self.macos_local_handler = None
        self.macos_modifier_mask = (
            int(NSEventModifierFlagCommand)
            | int(NSEventModifierFlagOption)
            | int(NSEventModifierFlagControl)
            | int(NSEventModifierFlagShift)
        ) if self.is_macos_native else 0

    def supports_global_hotkey(self) -> bool:
        return True

    def disabled_reason(self) -> str | None:
        return None

    def set_hotkey(self, sequence_text: str, hwnd: int | None = None) -> bool:
        self.stop()
        if not sequence_text:
            return True

        if self.is_windows_native:
            return self._set_windows_hotkey(sequence_text)
        if self.is_macos_native:
            return self._set_macos_hotkey(sequence_text)
        return self._set_fallback_hotkey(sequence_text)

    def _set_macos_hotkey(self, sequence_text: str) -> bool:
        if NSEvent is None:
            self.registration_failed.emit("Global hotkey support is unavailable on this macOS runtime.")
            return False

        try:
            modifiers, key_code = qkeysequence_to_macos(sequence_text)
        except Exception as exc:
            self.registration_failed.emit(str(exc))
            return False

        def matches(event: object) -> bool:
            if event is None:
                return False
            is_repeat = getattr(event, "isARepeat", None)
            if callable(is_repeat) and bool(is_repeat()):
                return False
            if int(event.keyCode()) != key_code:
                return False
            flags = int(event.modifierFlags()) & self.macos_modifier_mask
            return flags == modifiers

        def emit_if_match(event: object) -> bool:
            if not matches(event):
                return False
            self.activated.emit()
            return True

        def global_handler(event: object) -> None:
            emit_if_match(event)

        def local_handler(event: object) -> object | None:
            if emit_if_match(event):
                return None
            return event

        self.macos_global_handler = global_handler
        self.macos_local_handler = local_handler
        self.macos_global_monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSEventMaskKeyDown,
            global_handler,
        )
        self.macos_local_monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            NSEventMaskKeyDown,
            local_handler,
        )
        if self.macos_global_monitor is None and self.macos_local_monitor is None:
            self.registration_failed.emit("macOS rejected the selected hotkey.")
            return False
        return True

    def _set_windows_hotkey(self, sequence_text: str) -> bool:
        try:
            modifiers, virtual_key = qkeysequence_to_windows(sequence_text)
        except Exception as exc:
            self.registration_failed.emit(str(exc))
            return False

        self.windows_stop_event.clear()
        self.windows_ready_event.clear()

        def worker() -> None:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            msg = wintypes.MSG()
            PM_NOREMOVE = 0x0000

            user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_NOREMOVE)
            self.windows_thread_id = kernel32.GetCurrentThreadId()

            if not user32.RegisterHotKey(None, self.windows_hotkey_id, modifiers, virtual_key):
                self.registration_failed.emit("Windows rejected the selected hotkey. It may already be in use.")
                self.windows_ready_event.set()
                return

            self.windows_ready_event.set()
            while not self.windows_stop_event.is_set():
                result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result in (0, -1):
                    break
                if msg.message == 0x0312 and msg.wParam == self.windows_hotkey_id:
                    self.activated.emit()
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

            user32.UnregisterHotKey(None, self.windows_hotkey_id)

        self.windows_thread = threading.Thread(target=worker, name="HomeCopyHotkeyThread", daemon=True)
        self.windows_thread.start()
        self.windows_ready_event.wait(timeout=2)
        if self.windows_thread_id is None:
            self.registration_failed.emit("Hotkey thread failed to initialize.")
            return False
        return True

    def _set_fallback_hotkey(self, sequence_text: str) -> bool:
        if keyboard is None:
            self.registration_failed.emit("Global hotkey support requires the pynput package.")
            return False

        try:
            parsed = keyboard.HotKey.parse(qkeysequence_to_pynput(sequence_text))
        except Exception as exc:
            self.registration_failed.emit(str(exc))
            return False

        self.hotkey = keyboard.HotKey(parsed, self.activated.emit)

        def canonical(handler: Callable[[object], None]) -> Callable[[object], None]:
            def wrapper(key: object) -> None:
                if self.listener is None:
                    return
                handler(self.listener.canonical(key))

            return wrapper

        self.listener = keyboard.Listener(
            on_press=canonical(self.hotkey.press),
            on_release=canonical(self.hotkey.release),
        )
        self.listener.start()
        return True

    def stop(self) -> None:
        if self.is_windows_native:
            if self.windows_thread_id is not None:
                self.windows_stop_event.set()
                ctypes.windll.user32.PostThreadMessageW(self.windows_thread_id, 0x0012, 0, 0)
                if self.windows_thread is not None:
                    self.windows_thread.join(timeout=2)
            self.windows_thread = None
            self.windows_thread_id = None
            self.windows_ready_event.clear()

        if self.is_macos_native and NSEvent is not None:
            if self.macos_global_monitor is not None:
                NSEvent.removeMonitor_(self.macos_global_monitor)
            if self.macos_local_monitor is not None:
                NSEvent.removeMonitor_(self.macos_local_monitor)
            self.macos_global_monitor = None
            self.macos_local_monitor = None
            self.macos_global_handler = None
            self.macos_local_handler = None

        if self.listener is not None:
            self.listener.stop()
            self.listener = None
        self.hotkey = None
