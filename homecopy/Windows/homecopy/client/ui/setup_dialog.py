"""First-run setup dialog for HomeCopy."""

from __future__ import annotations

from pathlib import Path

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
    def __init__(self, config: ClientConfig, config_path: str | Path, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.config_path = Path(config_path)

        self.setWindowTitle("HomeCopy Setup")
        self.setModal(True)
        self.resize(560, 320)

        self.server_url_input = QLineEdit(config.server_url)
        self.device_name_input = QLineEdit(config.device_name)
        self.auto_copy_checkbox = QCheckBox("Receive text directly into clipboard")
        self.auto_copy_checkbox.setChecked(config.auto_copy_on_receive)
        self.notify_checkbox = QCheckBox("Show desktop notifications")
        self.notify_checkbox.setChecked(config.show_notification)
        self.discovery_status = QLabel("You can fill the server manually or try LAN auto-discovery.")
        self.discovery_status.setWordWrap(True)
        self.discovery_thread: DiscoveryThread | None = None

        self._build_ui()
        QTimer.singleShot(0, self._discover_server)

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        intro = QLabel("首次启动先补全客户端配置。这里的 Device Name 指的是当前这台客户端电脑，Device ID 会自动生成。保存后，客户端会自动连接到 HomeCopy server。")
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

        buttons = QDialogButtonBox()
        save_button = buttons.addButton("Save and Continue", QDialogButtonBox.AcceptRole)
        cancel_button = buttons.addButton("Cancel", QDialogButtonBox.RejectRole)
        save_button.clicked.connect(self._save_and_accept)
        cancel_button.clicked.connect(self.reject)

        helper_row = QHBoxLayout()
        helper_row.setSpacing(8)
        discover_button = QPushButton("Auto Discover Server")
        discover_button.clicked.connect(self._discover_server)
        self.discover_button = discover_button
        helper_row.addWidget(discover_button)
        helper_row.addStretch(1)

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

    def _save_and_accept(self) -> None:
        server_url = self.server_url_input.text().strip()
        device_name = self.device_name_input.text().strip()

        if not all([server_url, device_name]):
            QMessageBox.warning(self, "HomeCopy", "请先完整填写 server 和 device name。")
            return

        try:
            updated = self.config.model_copy(
                update={
                    "server_url": server_url,
                    "auth_token": "",
                    "device_name": device_name,
                    "device_id": make_device_id(device_name),
                    "auto_copy_on_receive": self.auto_copy_checkbox.isChecked(),
                    "show_notification": self.notify_checkbox.isChecked(),
                    "setup_completed": True,
                }
            )
            updated.save(self.config_path)
        except Exception as exc:
            QMessageBox.warning(self, "HomeCopy", f"保存配置失败：{exc}")
            return

        self.config = updated
        self.accept()
