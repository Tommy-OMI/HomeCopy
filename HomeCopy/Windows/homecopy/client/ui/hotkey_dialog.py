"""Dialog for editing the global hotkey."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QKeySequenceEdit,
)


class HotkeyDialog(QDialog):
    def __init__(self, current_hotkey: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Set Global Hotkey")
        self.setModal(True)
        self.resize(420, 180)

        self.edit = QKeySequenceEdit()
        self.edit.setKeySequence(current_hotkey)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(QLabel("Set the shortcut used to bring HomeCopy to the front from the system tray."))
        layout.addWidget(self.edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def hotkey_text(self) -> str:
        return self.edit.keySequence().toString()

    def _accept_if_valid(self) -> None:
        if not self.hotkey_text():
            QMessageBox.warning(self, "HomeCopy", "Please record a shortcut first.")
            return
        if "," in self.hotkey_text():
            QMessageBox.warning(self, "HomeCopy", "Please use a single shortcut, not a multi-step sequence.")
            return
        self.accept()
