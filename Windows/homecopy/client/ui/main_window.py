"""Main PySide6 window for the HomeCopy client."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QDialog,
    QSizePolicy,
    QStatusBar,
    QStyle,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from homecopy.client.config import ClientConfig
from homecopy.client.services.hotkey_service import GlobalHotkeyManager
from homecopy.client.ui.hotkey_dialog import HotkeyDialog
from homecopy.client.ui.runtime import ClientRuntimeThread
from homecopy.client.ui.setup_dialog import SetupDialog
from homecopy.shared.models import normalize_device_id
from homecopy_shared.startup_policy import EmbeddedServerController


WINDOW_STYLESHEET = """
QMainWindow {
  background: #f4efe7;
}
QFrame#TopBar {
  background: #183153;
  border-radius: 18px;
}
QFrame#Panel {
  background: #fffaf2;
  border: 1px solid #e7dcc9;
  border-radius: 18px;
}
QLabel#StatusBadge {
  background: #f5c451;
  color: #183153;
  border-radius: 12px;
  font-weight: 700;
  padding: 6px 12px;
}
QLabel#TitleLabel {
  color: #fffaf2;
  font-size: 22px;
  font-weight: 700;
}
QLabel#MetaLabel {
  color: #d9e3f0;
}
QListWidget, QTextEdit {
  background: #fffdf8;
  border: 1px solid #dccfb9;
  border-radius: 12px;
  padding: 8px;
  selection-background-color: #183153;
  selection-color: #fffdf8;
}
QPushButton {
  background: #d96d3a;
  color: white;
  border: none;
  border-radius: 12px;
  font-weight: 700;
  padding: 10px 16px;
}
QPushButton:hover {
  background: #c45b2b;
}
QPushButton:disabled {
  background: #cdb9ab;
  color: #f6ede4;
}
QStatusBar {
  background: #fffaf2;
}
"""


class MainWindow(QMainWindow):
    def __init__(
        self,
        config_path: str | Path,
        config: ClientConfig | None = None,
        server_controller: EmbeddedServerController | None = None,
    ) -> None:
        super().__init__()
        self.config_path = Path(config_path)
        self.config = config or ClientConfig.load(self.config_path)
        self.runtime: ClientRuntimeThread | None = None
        self.current_devices: list[dict] = []
        self.tray_icon: QSystemTrayIcon | None = None
        self.hotkey_manager = GlobalHotkeyManager(self)
        self.server_controller = server_controller
        self.minimize_to_tray_notice_shown = False
        self.latest_received_text = ""

        self.setWindowTitle(f"HomeCopy - {self.config.device_name}")
        self.resize(1120, 760)
        self.setMinimumSize(900, 640)
        self.setStyleSheet(WINDOW_STYLESHEET)

        self._build_ui()
        self._connect_signals()

        if not self._run_first_launch_setup():
            raise SystemExit(0)

        self.runtime = ClientRuntimeThread(self.config)
        self._connect_runtime_signals()
        self._setup_tray_icon()
        self._setup_global_hotkey()
        self.runtime.start()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(22, 22, 22, 18)
        root_layout.setSpacing(18)
        root_layout.addWidget(self._build_top_bar())

        content_layout = QHBoxLayout()
        content_layout.setSpacing(18)
        content_layout.addWidget(self._build_device_panel(), 2)
        content_layout.addWidget(self._build_editor_panel(), 6)
        root_layout.addLayout(content_layout)

        self.setCentralWidget(root)

        status_bar = QStatusBar()
        status_bar.showMessage("Ready")
        self.setStatusBar(status_bar)

    def _build_top_bar(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("TopBar")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        title_column = QVBoxLayout()
        title = QLabel("HomeCopy")
        title.setObjectName("TitleLabel")
        subtitle = QLabel(f"{self.config.device_name}  |  {self.config.server_url}")
        subtitle.setObjectName("MetaLabel")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)

        self.status_badge = QLabel("connecting")
        self.status_badge.setObjectName("StatusBadge")
        self.status_badge.setAlignment(Qt.AlignCenter)
        self.status_badge.setMinimumWidth(160)

        layout.addLayout(title_column)
        layout.addStretch(1)
        layout.addWidget(self.status_badge)
        return panel

    def _build_device_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Online Devices")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #183153;")
        description = QLabel("Double-click a device to target it quickly.")
        description.setStyleSheet("color: #6f655d;")

        self.device_list = QListWidget()
        self.device_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.device_list.setMinimumWidth(220)
        self.device_list.setMaximumWidth(300)

        self.selected_device_label = QLabel("Target: none")
        self.selected_device_label.setStyleSheet("font-weight: 700; color: #183153;")

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.device_list, 1)
        layout.addWidget(self.selected_device_label)
        return panel

    def _build_editor_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Send Text")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #183153;")
        description = QLabel("Paste a code snippet, link, or short note and send it to another machine.")
        description.setWordWrap(True)
        description.setStyleSheet("color: #6f655d;")

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Type or paste text here...")
        self.editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.editor.setMinimumHeight(150)
        self.editor.setMaximumHeight(220)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        self.send_button = QPushButton("Send")
        self.clear_button = QPushButton("Clear")
        self.refresh_button = QPushButton("Refresh")
        self.hotkey_button = QPushButton("Hotkey")
        button_row.addWidget(self.send_button)
        button_row.addWidget(self.clear_button)
        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.hotkey_button)
        button_row.addStretch(1)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.editor, 2)
        layout.addLayout(button_row)
        layout.addWidget(self._build_activity_panel(), 5)
        return panel

    def _build_activity_panel(self) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        history_panel = QFrame()
        history_panel.setObjectName("Panel")
        history_layout = QVBoxLayout(history_panel)
        history_layout.setContentsMargins(16, 16, 16, 16)
        history_layout.setSpacing(10)
        history_title = QLabel("Recent History")
        history_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #183153;")
        self.history_list = QListWidget()
        history_layout.addWidget(history_title)
        history_layout.addWidget(self.history_list, 1)

        incoming_panel = QFrame()
        incoming_panel.setObjectName("Panel")
        incoming_layout = QVBoxLayout(incoming_panel)
        incoming_layout.setContentsMargins(16, 16, 16, 16)
        incoming_layout.setSpacing(10)
        incoming_title = QLabel("Latest Clipboard Sync")
        incoming_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #183153;")
        self.latest_received_meta = QLabel("Waiting for incoming text...")
        self.latest_received_meta.setStyleSheet("color: #6f655d;")
        self.latest_received_preview = QTextEdit()
        self.latest_received_preview.setReadOnly(True)
        self.latest_received_preview.setPlaceholderText("New incoming text will appear here.")
        incoming_layout.addWidget(incoming_title)
        incoming_layout.addWidget(self.latest_received_meta)
        incoming_layout.addWidget(self.latest_received_preview, 1)

        layout.addWidget(history_panel, 1)
        layout.addWidget(incoming_panel, 1)
        return panel

    def _connect_signals(self) -> None:
        self.send_button.clicked.connect(self._send_current_text)
        self.clear_button.clicked.connect(self.editor.clear)
        self.refresh_button.clicked.connect(self._refresh_devices)
        self.hotkey_button.clicked.connect(self._open_hotkey_dialog)
        self.device_list.itemSelectionChanged.connect(self._update_selected_device_label)
        self.device_list.itemDoubleClicked.connect(lambda _: self._send_current_text())
        self.hotkey_manager.activated.connect(self._toggle_visibility_from_hotkey)
        self.hotkey_manager.registration_failed.connect(self._handle_hotkey_registration_failed)
    
    def _connect_runtime_signals(self) -> None:
        assert self.runtime is not None
        self.runtime.status_changed.connect(self._handle_status_changed)
        self.runtime.devices_changed.connect(self._populate_devices)
        self.runtime.incoming_text.connect(self._handle_incoming_text)
        self.runtime.ack_received.connect(self._handle_ack)
        self.runtime.error_received.connect(self._handle_error)
        self.runtime.history_changed.connect(self._populate_history)

    def _run_first_launch_setup(self) -> bool:
        if not self.config.needs_first_run_setup():
            return True

        dialog = SetupDialog(self.config, self.config_path, self)
        if dialog.exec() != QDialog.Accepted:
            return False

        self.config = ClientConfig.load(self.config_path)
        subtitle = self.findChild(QLabel, "MetaLabel")
        if subtitle is not None:
            subtitle.setText(f"{self.config.device_name}  |  {self.config.server_url}")
        self.setWindowTitle(f"HomeCopy - {self.config.device_name}")
        return True

    def _refresh_devices(self) -> None:
        if self.runtime is not None:
            self.runtime.refresh_devices()

    def _setup_tray_icon(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        tray_icon = QSystemTrayIcon(self.style().standardIcon(QStyle.SP_ComputerIcon), self)
        tray_icon.setToolTip("HomeCopy")
        tray_icon.activated.connect(self._handle_tray_activated)

        tray_menu = QMenu(self)
        show_action = QAction("Show HomeCopy", self)
        show_action.triggered.connect(self._restore_from_tray)
        hotkey_action = QAction("Set Hotkey", self)
        hotkey_action.triggered.connect(self._open_hotkey_dialog)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_application)
        tray_menu.addAction(show_action)
        tray_menu.addAction(hotkey_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        tray_icon.setContextMenu(tray_menu)
        tray_icon.show()
        self.tray_icon = tray_icon

    def _setup_global_hotkey(self) -> None:
        self.hotkey_manager.set_hotkey(self.config.global_hotkey)

    def _open_hotkey_dialog(self) -> None:
        dialog = HotkeyDialog(self.config.global_hotkey, self)
        if dialog.exec() != QDialog.Accepted:
            return

        hotkey_text = dialog.hotkey_text()
        previous_hotkey = self.config.global_hotkey
        self.config = self.config.model_copy(update={"global_hotkey": hotkey_text})
        try:
            if not self.hotkey_manager.set_hotkey(hotkey_text):
                raise ValueError("Failed to register the selected hotkey.")
            self.config.save(self.config_path)
        except Exception as exc:
            self.config = self.config.model_copy(update={"global_hotkey": previous_hotkey})
            QMessageBox.warning(self, "HomeCopy", f"Failed to save hotkey: {exc}")
            self.hotkey_manager.set_hotkey(previous_hotkey)
            return

        self.statusBar().showMessage(f"Global hotkey updated to {hotkey_text}", 6000)

    def _handle_hotkey_registration_failed(self, message: str) -> None:
        self.statusBar().showMessage(message, 8000)

    def _handle_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {
            QSystemTrayIcon.Trigger,
            QSystemTrayIcon.DoubleClick,
            QSystemTrayIcon.MiddleClick,
        }:
            self._restore_from_tray()

    def _hide_to_tray(self) -> None:
        if not self.config.minimize_to_tray or self.tray_icon is None:
            return
        self.hide()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        if not self.minimize_to_tray_notice_shown:
            self.tray_icon.showMessage(
                "HomeCopy",
                f"HomeCopy is still running in the system tray. Hotkey: {self.config.global_hotkey}",
                QSystemTrayIcon.Information,
                4000,
            )
            self.minimize_to_tray_notice_shown = True

    def _restore_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _toggle_visibility_from_hotkey(self) -> None:
        # Global hotkey callbacks can arrive with stale window-state flags.
        # Use visibility as the source of truth and defer UI work to the event loop.
        if self.isVisible():
            QTimer.singleShot(0, self._hide_to_tray)
            return
        QTimer.singleShot(0, self._restore_from_tray)

    def _quit_application(self) -> None:
        self.close()

    def _shutdown_owned_server(self) -> None:
        if self.server_controller is not None:
            self.server_controller.shutdown()

    def _populate_devices(self, devices: list[dict]) -> None:
        visible_devices: list[dict] = []
        seen_device_ids: set[str] = set()
        local_device_id = self.config.device_id.casefold()
        for device in devices:
            device_id = str(device["device_id"]).casefold()
            if device_id == local_device_id or device_id in seen_device_ids:
                continue
            seen_device_ids.add(device_id)
            visible_devices.append(device)

        self.current_devices = visible_devices
        selected_device_id = self._selected_device_id()

        self.device_list.clear()
        for device in self.current_devices:
            device_name = str(device["device_name"])
            device_id = str(device["device_id"])
            if normalize_device_id(device_name) == normalize_device_id(device_id):
                item_text = device_name
            else:
                item_text = f"{device_name}\n{device_id}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, device["device_id"])
            self.device_list.addItem(item)
            if device["device_id"] == selected_device_id:
                item.setSelected(True)

        self._update_selected_device_label()
        self.statusBar().showMessage(f"Online devices updated: {len(self.current_devices)}")

    def _populate_history(self, history: list[dict]) -> None:
        self.history_list.clear()
        for record in reversed(history):
            direction = "Sent" if record["direction"] == "sent" else "Received"
            line = f"{direction} | {record['peer_device_name']} | {record['created_at']}"
            preview = record["text"].replace("\n", " ")
            item = QListWidgetItem(f"{line}\n{preview[:140]}")
            self.history_list.addItem(item)

    def _handle_status_changed(self, status: str) -> None:
        self.status_badge.setText(status)
        self.statusBar().showMessage(status)

    def _handle_incoming_text(self, message: dict) -> None:
        sender = message.get("from_name") or message.get("from")
        text = message.get("text", "")
        self.latest_received_text = text
        self.statusBar().showMessage(f"Received text from {sender}", 8000)
        self.editor.setPlainText(text)
        self.editor.selectAll()
        self.latest_received_meta.setText(f"Latest incoming text from {sender}")
        self.latest_received_preview.setPlainText(text)

    def _handle_ack(self, request_id: str) -> None:
        self.editor.clear()
        self.statusBar().showMessage(f"Sent successfully ({request_id})", 6000)

    def _handle_error(self, error_text: str) -> None:
        self.statusBar().showMessage(error_text, 8000)
        QMessageBox.warning(self, "HomeCopy", error_text)

    def _selected_device_id(self) -> str | None:
        selected_items = self.device_list.selectedItems()
        if not selected_items:
            return None
        return selected_items[0].data(Qt.UserRole)

    def _update_selected_device_label(self) -> None:
        selected_items = self.device_list.selectedItems()
        if not selected_items:
            self.selected_device_label.setText("Target: none")
            return
        device_id = selected_items[0].data(Qt.UserRole)
        device_name = selected_items[0].text().splitlines()[0]
        self.selected_device_label.setText(f"Target: {device_name} ({device_id})")

    def _send_current_text(self) -> None:
        target_device_id = self._selected_device_id()
        text = self.editor.toPlainText().strip()

        if not target_device_id:
            QMessageBox.information(self, "HomeCopy", "Please select a target device first.")
            return
        if not text:
            QMessageBox.information(self, "HomeCopy", "Please enter some text before sending.")
            return

        self.runtime.send_text(target_device_id, text)
        self.statusBar().showMessage(f"Sending to {target_device_id}...", 4000)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.hotkey_manager.stop()
        if self.tray_icon is not None:
            self.tray_icon.hide()
        if self.runtime is not None:
            self.runtime.stop()
            self.runtime.wait(3000)
        self._shutdown_owned_server()
        super().closeEvent(event)

    def changeEvent(self, event: QEvent) -> None:
        if (
            event.type() == QEvent.WindowStateChange
            and self.isMinimized()
            and self.config.minimize_to_tray
            and self.tray_icon is not None
        ):
            QTimer.singleShot(0, self._hide_to_tray)
        super().changeEvent(event)



def create_application(
    config_path: str | Path,
    config: ClientConfig | None = None,
    server_controller: EmbeddedServerController | None = None,
) -> tuple[QApplication, MainWindow]:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(config_path, config, server_controller)
    return app, window
