"""Shared Qt setup dialog used by Windows and macOS clients."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QThread, Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from homecopy.client.config import ClientConfig, make_device_id
from homecopy.client.discovery import discover_server


SetupAction = Literal["connect", "start_local", "cancel"]


@dataclass(slots=True)
class SetupResult:
    action: SetupAction
    server_url: str


class DiscoveryThread(QThread):
    found = Signal(dict)
    failed = Signal(str)

    def __init__(self, discovery_port: int = 8766) -> None:
        super().__init__()
        self.discovery_port = discovery_port

    def run(self) -> None:
        import asyncio

        result = asyncio.run(discover_server(discovery_port=self.discovery_port))
        if result is None:
            self.failed.emit("No HomeCopy server found on the local network.")
            return
        self.found.emit(
            {
                "server_url": result.server_url,
                "server_name": result.server_name,
                "discovery_port": result.discovery_port,
                "responder_ip": result.responder_ip,
            }
        )


class SetupDialog(QDialog):
    def __init__(
        self,
        config: ClientConfig,
        config_path: str | Path,
        parent=None,
        *,
        server_missing: bool = False,
        local_server_url: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.config_path = Path(config_path)
        self.server_missing = server_missing
        self.local_server_url = local_server_url or "ws://127.0.0.1:8765/ws"
        self.discovery_thread: DiscoveryThread | None = None
        self.result_payload = SetupResult(action="cancel", server_url=config.server_url)

        self.setWindowTitle("HomeCopy Setup")
        self.setModal(True)
        self.resize(560, 360 if server_missing else 320)

        self.server_url_input = QLineEdit(config.server_url)
        self.device_name_input = QLineEdit(config.device_name)
        self.auto_copy_checkbox = QCheckBox("Receive text directly into clipboard")
        self.auto_copy_checkbox.setChecked(config.auto_copy_on_receive)
        self.notify_checkbox = QCheckBox("Show desktop notifications")
        self.notify_checkbox.setChecked(config.show_notification)
        self.discovery_status = QLabel(self._initial_status_text())
        self.discovery_status.setWordWrap(True)

        self._build_ui()
        QTimer.singleShot(0, self._discover_server)

    def _initial_intro_text(self) -> str:
        if self.server_missing:
            return (
                "未发现可用的 HomeCopy server。你可以重新自动发现、手动填写 Server URL，"
                "或者直接在当前电脑上启动本地 relay server。"
            )
        return (
            "首次启动先补全客户端配置。这里的 Device Name 指的是当前这台客户端电脑，"
            "Device ID 会自动生成。保存后，客户端会自动连接到 HomeCopy server。"
        )

    def _initial_status_text(self) -> str:
        if self.server_missing:
            return "No HomeCopy server found on the local network yet."
        return "You can fill the server manually or try LAN auto-discovery."

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        intro = QLabel(self._initial_intro_text())
        intro.setWordWrap(True)
        intro.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow("Server URL", self.server_url_input)
        form.addRow("Device Name", self.device_name_input)

        toggles = QVBoxLayout()
        toggles.setSpacing(10)
        toggles.addWidget(self.auto_copy_checkbox)
        toggles.addWidget(self.notify_checkbox)

        helper_row = QHBoxLayout()
        helper_row.setSpacing(8)
        discover_button = QPushButton("Auto Discover Server")
        discover_button.clicked.connect(self._discover_server)
        self.discover_button = discover_button
        helper_row.addWidget(discover_button)
        helper_row.addStretch(1)

        buttons = QDialogButtonBox()
        save_label = "Connect and Continue" if self.server_missing else "Save and Continue"
        save_button = buttons.addButton(save_label, QDialogButtonBox.AcceptRole)
        cancel_button = buttons.addButton("Cancel", QDialogButtonBox.RejectRole)
        save_button.clicked.connect(self._save_and_accept)
        cancel_button.clicked.connect(self._cancel)

        if self.server_missing:
            start_local_button = buttons.addButton("Start Local Relay", QDialogButtonBox.ActionRole)
            start_local_button.clicked.connect(self._start_local_and_accept)

        root_layout.addWidget(intro)
        root_layout.addLayout(form)
        root_layout.addLayout(toggles)
        root_layout.addLayout(helper_row)
        root_layout.addWidget(self.discovery_status)
        root_layout.addWidget(buttons)

    def _discover_server(self) -> None:
        if self.discovery_thread is not None and self.discovery_thread.isRunning():
            return
        self.discover_button.setEnabled(False)
        self.discovery_status.setText("Searching for HomeCopy server on the local network...")
        self.discovery_thread = DiscoveryThread()
        self.discovery_thread.found.connect(self._apply_discovery_result)
        self.discovery_thread.failed.connect(self._handle_discovery_failed)
        self.discovery_thread.finished.connect(lambda: self.discover_button.setEnabled(True))
        self.discovery_thread.start()

    def _apply_discovery_result(self, result: dict) -> None:
        self.server_url_input.setText(result["server_url"])
        self.discovery_status.setText(
            f"Discovered {result['server_name']} at {result['server_url']}."
        )

    def _handle_discovery_failed(self, message: str) -> None:
        self.discovery_status.setText(message)

    def _build_updated_config(self, server_url: str) -> ClientConfig:
        device_name = self.device_name_input.text().strip()
        if not device_name:
            raise ValueError("请先填写 device name。")

        if not server_url.strip():
            raise ValueError("请先填写 server url。")

        return self.config.model_copy(
            update={
                "server_url": server_url.strip(),
                "auth_token": "",
                "device_name": device_name,
                "device_id": make_device_id(device_name),
                "auto_copy_on_receive": self.auto_copy_checkbox.isChecked(),
                "show_notification": self.notify_checkbox.isChecked(),
                "setup_completed": True,
            }
        )

    def _save_config(self, updated: ClientConfig) -> None:
        updated.save(self.config_path)
        self.config = updated

    def _save_and_accept(self) -> None:
        try:
            updated = self._build_updated_config(self.server_url_input.text())
            self._save_config(updated)
        except Exception as exc:
            QMessageBox.warning(self, "HomeCopy", f"保存配置失败：{exc}")
            return

        self.result_payload = SetupResult(action="connect", server_url=updated.server_url)
        self.accept()

    def _start_local_and_accept(self) -> None:
        try:
            updated = self._build_updated_config(self.local_server_url)
            self._save_config(updated)
        except Exception as exc:
            QMessageBox.warning(self, "HomeCopy", f"保存配置失败：{exc}")
            return

        self.result_payload = SetupResult(action="start_local", server_url=updated.server_url)
        self.accept()

    def _cancel(self) -> None:
        self.result_payload = SetupResult(action="cancel", server_url=self.config.server_url)
        self.reject()


__all__ = ["DiscoveryThread", "SetupDialog", "SetupResult"]
