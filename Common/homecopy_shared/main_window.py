"""Main PySide6 window shared by the HomeCopy desktop clients."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QRectF, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QColor, QDesktopServices, QIcon, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
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
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from homecopy.client.config import ClientConfig
from homecopy.client.services.hotkey_service import GlobalHotkeyManager
from homecopy.client.services.notification_service import NotificationService
from homecopy.client.ui.hotkey_dialog import HotkeyDialog
from homecopy.client.ui.runtime import ClientRuntimeThread
from homecopy.client.ui.setup_dialog import SetupDialog
from homecopy.paths import runtime_data_root
from homecopy_shared import APP_VERSION
from homecopy_shared.startup_policy import (
    EmbeddedServerController,
    get_server_stats,
    is_local_server_url,
    local_server_display_address,
    resolve_preferred_local_host,
    wait_for_server_health,
)
from homecopy_shared.ui_formatting import (
    format_device_label,
    format_history_content,
    format_history_direction,
    format_history_timestamp,
    format_file_size,
    format_notification_message,
    format_server_display,
)


HISTORY_MESSAGE_COLUMN = 3
HISTORY_ACTION_COLUMN = 4
HISTORY_HIGHLIGHT_COLOR = QColor("#f8e8a6")

WINDOW_STYLESHEET = """
QMainWindow {
  background: #f4efe7;
}
QFrame#TopBar {
  background: transparent;
}
QFrame#TopSectionLeft,
QFrame#TopSectionRight {
  background: #183153;
  border: 1px solid rgba(255, 250, 242, 0.12);
  border-radius: 18px;
}
QLabel#SectionTitle {
  color: #fffaf2;
  font-size: 18px;
  font-weight: 700;
}
QLabel#SectionStatus {
  color: #f5c451;
  font-weight: 700;
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
QLabel#ServerBadge {
  background: #d7e7f6;
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
QLabel#VersionLabel {
  color: #f5c451;
  font-size: 16px;
  font-weight: 700;
}
QLabel#MetaLabel {
  color: #d9e3f0;
}
QListWidget, QTableWidget, QTextEdit {
  background: #fffdf8;
  color: #183153;
  border: 1px solid #dccfb9;
  border-radius: 12px;
  padding: 8px;
  selection-background-color: #183153;
  selection-color: #fffdf8;
}
QListWidget::item,
QTableWidget::item {
  color: #183153;
}
QHeaderView::section {
  background: #efe4d2;
  color: #183153;
  border: none;
  border-bottom: 1px solid #dccfb9;
  padding: 8px 10px;
  font-weight: 700;
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
QPushButton[smallAction="true"] {
  background: #d96d3a;
  border-radius: 11px;
  font-size: 18px;
  font-weight: 700;
  max-width: 22px;
  min-width: 22px;
  max-height: 22px;
  min-height: 22px;
  padding: 0;
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
        self.current_history: list[dict] = []
        self.tray_icon: QSystemTrayIcon | None = None
        self.notification_service = NotificationService()
        self.hotkey_manager = GlobalHotkeyManager(self)
        self.server_controller = server_controller or EmbeddedServerController()
        self.minimize_to_tray_notice_shown = False
        self.highlighted_history_marker: tuple[str, str, str, str] | None = None
        self._syncing_history_selection = False
        self.local_server_client_count = 0
        self._quit_requested = False
        self._hidden_to_tray = False
        self._restoring_from_tray = False
        self._tray_hide_pending = False
        self._tray_has_unread_message = False
        self._default_tray_icon: QIcon | None = None
        self._unread_tray_icon: QIcon | None = None
        self.server_stats_timer = QTimer(self)
        self.server_stats_timer.setInterval(1500)
        self.remote_server_version = ""

        self.setWindowTitle(f"HomeCopy - {self.config.device_name}")
        self.resize(1180, 760)
        self.setMinimumSize(960, 660)
        self.setStyleSheet(WINDOW_STYLESHEET)

        self._build_ui()
        self._connect_signals()

        if not self._run_first_launch_setup():
            raise SystemExit(0)

        self.runtime = ClientRuntimeThread(self.config)
        self._connect_runtime_signals()
        self._setup_tray_icon()
        self._refresh_header_details()
        self.server_stats_timer.timeout.connect(self._refresh_local_server_stats)
        self.server_stats_timer.start()
        QTimer.singleShot(250, self._refresh_local_server_stats)
        QTimer.singleShot(500, self._setup_global_hotkey)
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
        content_layout.addWidget(self._build_editor_panel(), 7)
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

        self.client_section = QFrame()
        self.client_section.setObjectName("TopSectionLeft")
        client_layout = QVBoxLayout(self.client_section)
        client_layout.setContentsMargins(18, 16, 18, 16)
        client_layout.setSpacing(10)

        client_header_row = QHBoxLayout()
        client_header_row.setSpacing(10)
        title = QLabel("HomeCopy")
        title.setObjectName("TitleLabel")
        version = QLabel(APP_VERSION)
        version.setObjectName("VersionLabel")
        self.connection_button = QPushButton("Disconnect")
        self.connection_button.setMinimumWidth(132)
        client_header_row.addWidget(title)
        client_header_row.addWidget(version)
        client_header_row.addStretch(1)
        client_header_row.addWidget(self.connection_button)

        client_meta_row = QHBoxLayout()
        client_meta_row.setSpacing(18)
        self.client_device_label = QLabel()
        self.client_device_label.setObjectName("MetaLabel")
        self.client_ip_label = QLabel()
        self.client_ip_label.setObjectName("MetaLabel")
        self.client_server_label = QLabel()
        self.client_server_label.setObjectName("MetaLabel")
        self.client_status_label = QLabel()
        self.client_status_label.setObjectName("SectionStatus")
        self.client_status_label.hide()

        client_layout.addLayout(client_header_row)
        client_meta_row.addWidget(self.client_device_label)
        client_meta_row.addWidget(self.client_ip_label)
        client_meta_row.addWidget(self.client_server_label)
        client_meta_row.addStretch(1)
        client_layout.addLayout(client_meta_row)

        self.server_section = QFrame()
        self.server_section.setObjectName("TopSectionRight")
        server_layout = QVBoxLayout(self.server_section)
        server_layout.setContentsMargins(18, 16, 18, 16)
        server_layout.setSpacing(10)

        server_header_row = QHBoxLayout()
        server_header_row.setSpacing(10)
        server_title = QLabel("Local Relay")
        server_title.setObjectName("SectionTitle")
        self.server_toggle_button = QPushButton("Stop Server")
        self.server_toggle_button.setMinimumWidth(136)
        server_header_row.addWidget(server_title)
        server_header_row.addStretch(1)
        server_header_row.addWidget(self.server_toggle_button)

        server_meta_row = QHBoxLayout()
        server_meta_row.setSpacing(18)
        self.server_meta_label = QLabel(local_server_display_address())
        self.server_meta_label.setObjectName("MetaLabel")
        self.server_clients_label = QLabel("Clients: 0")
        self.server_clients_label.setObjectName("MetaLabel")
        self.server_status_label = QLabel()
        self.server_status_label.setObjectName("SectionStatus")
        self.server_status_label.hide()

        server_layout.addLayout(server_header_row)
        server_meta_row.addWidget(self.server_meta_label)
        server_meta_row.addWidget(self.server_clients_label)
        server_meta_row.addStretch(1)
        server_layout.addLayout(server_meta_row)

        layout.addWidget(self.client_section, 1)
        layout.addWidget(self.server_section, 1)
        return panel

    def _build_device_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        panel.setMinimumWidth(220)
        panel.setMaximumWidth(290)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Online Devices")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #183153;")

        self.device_list = QListWidget()
        self.device_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.device_list.setMinimumWidth(196)
        self.device_list.setMaximumWidth(248)

        self.selected_device_label = QLabel("Target: none")
        self.selected_device_label.setStyleSheet("font-weight: 700; color: #183153;")

        layout.addWidget(title)
        layout.addWidget(self.device_list, 1)
        layout.addWidget(self.selected_device_label)
        return panel

    def _build_editor_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Send Content")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #183153;")
        description = QLabel("Paste text or choose a file and send it to another machine.")
        description.setWordWrap(True)
        description.setStyleSheet("color: #6f655d;")

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Type or paste text here...")
        self.editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.editor.setMinimumHeight(150)
        self.editor.setMaximumHeight(220)
        self.editor.installEventFilter(self)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        self.send_button = QPushButton("Send")
        self.send_file_button = QPushButton("Send File")
        self.clear_button = QPushButton("Clear")
        self.hotkey_button = QPushButton("Hotkey")
        button_row.addWidget(self.send_button)
        button_row.addWidget(self.send_file_button)
        button_row.addWidget(self.clear_button)
        button_row.addWidget(self.hotkey_button)
        button_row.addStretch(1)

        history_header_row = QHBoxLayout()
        history_header_row.setSpacing(10)
        history_title = QLabel("Recent History")
        history_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #183153;")
        self.clear_history_button = QPushButton("Clear")
        self.clear_history_button.setMinimumWidth(96)
        self.clear_history_button.setEnabled(False)
        history_header_row.addWidget(history_title)
        history_header_row.addStretch(1)
        history_header_row.addWidget(self.clear_history_button)

        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["Date Time", "Device", "Direction", "Content", ""])
        self.history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.setWordWrap(False)
        self.history_table.setShowGrid(False)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.verticalHeader().setDefaultSectionSize(38)

        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.editor, 2)
        layout.addLayout(button_row)
        layout.addLayout(history_header_row)
        layout.addWidget(self.history_table, 5)
        return panel

    def _connect_signals(self) -> None:
        self.send_button.clicked.connect(self._send_current_text)
        self.send_file_button.clicked.connect(self._send_selected_file)
        self.clear_button.clicked.connect(self.editor.clear)
        self.hotkey_button.clicked.connect(self._open_hotkey_dialog)
        self.connection_button.clicked.connect(self._toggle_client_connection)
        self.server_toggle_button.clicked.connect(self._toggle_local_server)
        self.clear_history_button.clicked.connect(self._clear_history)
        self.device_list.itemSelectionChanged.connect(self._update_selected_device_label)
        self.device_list.itemDoubleClicked.connect(lambda _: self._send_current_text())
        self.history_table.cellPressed.connect(self._handle_history_cell_pressed)
        self.history_table.cellDoubleClicked.connect(self._handle_history_cell_double_clicked)
        self.history_table.itemSelectionChanged.connect(self._normalize_history_selection)
        self.hotkey_manager.activated.connect(self._toggle_visibility_from_hotkey)
        self.hotkey_manager.registration_failed.connect(self._handle_hotkey_registration_failed)

    def _connect_runtime_signals(self) -> None:
        assert self.runtime is not None
        self.runtime.status_changed.connect(self._handle_status_changed)
        self.runtime.devices_changed.connect(self._populate_devices)
        self.runtime.server_version_changed.connect(self._handle_server_version_changed)
        self.runtime.incoming_text.connect(self._handle_incoming_text)
        self.runtime.incoming_file.connect(self._handle_incoming_file)
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
        self.setWindowTitle(f"HomeCopy - {self.config.device_name}")
        self._refresh_header_details()
        return True

    def _setup_tray_icon(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self._default_tray_icon = self._build_tray_icon(False)
        self._unread_tray_icon = self._build_tray_icon(True)
        tray_icon = QSystemTrayIcon(self)
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
        self.tray_icon = tray_icon
        self._update_tray_icon()
        tray_icon.show()

    def _build_tray_icon(self, has_unread: bool) -> QIcon:
        base_icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        if not has_unread:
            return base_icon

        icon = QIcon()
        for size in (16, 18, 20, 22, 24, 32):
            pixmap = base_icon.pixmap(size, size)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            diameter = max(6, int(size * 0.42))
            margin = max(1, int(size * 0.06))
            dot_rect = QRectF(size - diameter - margin, margin, diameter, diameter)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#d96d3a"))
            painter.drawEllipse(dot_rect)
            painter.setBrush(QColor("#fffaf2"))
            inner_rect = dot_rect.adjusted(
                diameter * 0.3,
                diameter * 0.3,
                -diameter * 0.3,
                -diameter * 0.3,
            )
            painter.drawEllipse(inner_rect)
            painter.end()
            icon.addPixmap(pixmap)
        return icon

    def _update_tray_icon(self) -> None:
        if self.tray_icon is None:
            return
        icon = self._unread_tray_icon if self._tray_has_unread_message else self._default_tray_icon
        if icon is not None:
            self.tray_icon.setIcon(icon)
        tooltip = "HomeCopy"
        if self._tray_has_unread_message:
            tooltip = "HomeCopy (new item)"
        self.tray_icon.setToolTip(tooltip)

    def _set_tray_unread_message(self, has_unread: bool) -> None:
        if self._tray_has_unread_message == has_unread:
            return
        self._tray_has_unread_message = has_unread
        self._update_tray_icon()

    def _should_mark_tray_unread(self) -> bool:
        return (
            self.tray_icon is not None
            and (
                self._hidden_to_tray
                or not self.isVisible()
                or not self.isActiveWindow()
            )
        )

    def _setup_global_hotkey(self) -> None:
        if not self.hotkey_manager.set_hotkey(self.config.global_hotkey):
            reason = self.hotkey_manager.disabled_reason()
            if reason:
                self.statusBar().showMessage(reason, 8000)

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
        self._tray_hide_pending = False
        if not self.config.minimize_to_tray or self.tray_icon is None:
            return
        self._hidden_to_tray = True
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.hide()
        if not self.minimize_to_tray_notice_shown:
            tray_message = "HomeCopy is still running in the system tray."
            if self.config.global_hotkey:
                tray_message = f"{tray_message} Hotkey: {self.config.global_hotkey}"
            self.tray_icon.showMessage(
                "HomeCopy",
                tray_message,
                QSystemTrayIcon.Information,
                4000,
            )
            self.minimize_to_tray_notice_shown = True

    def _restore_from_tray(self) -> None:
        self._tray_hide_pending = False
        self._hidden_to_tray = False
        self._restoring_from_tray = True
        self._set_tray_unread_message(False)
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.repaint()
        QTimer.singleShot(0, self._finish_restore_from_tray)

    def _finish_restore_from_tray(self) -> None:
        self._restoring_from_tray = False
        self.update()

    def _toggle_visibility_from_hotkey(self) -> None:
        if self.isVisible():
            QTimer.singleShot(0, self._hide_to_tray)
            return
        QTimer.singleShot(0, self._restore_from_tray)

    def _quit_application(self) -> None:
        self._quit_requested = True
        self.close()

    def _shutdown_owned_server(self) -> None:
        if self.server_controller is not None:
            self.server_controller.shutdown()

    def _toggle_client_connection(self) -> None:
        if self.runtime is None:
            return
        if self.connection_button.text() == "Connect":
            self.runtime.connect_client()
            self.statusBar().showMessage("Connecting to HomeCopy server...", 4000)
            return
        self.runtime.disconnect_client()
        self.statusBar().showMessage("Disconnected from HomeCopy server.", 4000)

    def _toggle_local_server(self) -> None:
        if self.server_controller is None:
            return

        if self.server_controller.is_running():
            if self.runtime is not None and self._is_local_client_target():
                self.runtime.disconnect_client()
            self.server_controller.shutdown()
            self.local_server_client_count = 0
            self._refresh_server_section()
            self.statusBar().showMessage("Local relay server stopped.", 5000)
            return

        if not self.server_controller.started_by_app:
            return

        self.server_controller.start(runtime_data_root())
        if not wait_for_server_health(root=runtime_data_root()):
            self.server_controller.shutdown()
            self.local_server_client_count = 0
            self._refresh_server_section()
            QMessageBox.warning(self, "HomeCopy", "Unable to restart the local HomeCopy server.")
            return

        if self.runtime is not None and self._is_local_client_target():
            self.runtime.connect_client()
        self._refresh_local_server_stats()
        self._refresh_server_section()
        self.statusBar().showMessage("Local relay server started.", 5000)

    def _clear_history(self) -> None:
        if self.runtime is None or not self.current_history:
            return
        self.highlighted_history_marker = None
        self.runtime.clear_history()
        self.statusBar().showMessage("History cleared.", 4000)

    def _delete_history_record(self, history_index: int) -> None:
        if self.runtime is None:
            return
        self.highlighted_history_marker = None
        self.runtime.delete_history_record(history_index)
        self.statusBar().showMessage("History entry deleted.", 4000)

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
            device_version = str(device.get("version") or "")
            item = QListWidgetItem(format_device_label(device_name, device_id, device_version or None))
            item.setData(Qt.UserRole, device["device_id"])
            item.setData(Qt.UserRole + 1, device_name)
            self.device_list.addItem(item)
            if device["device_id"] == selected_device_id:
                item.setSelected(True)

        self._update_selected_device_label()
        self.statusBar().showMessage(f"Online devices updated: {len(self.current_devices)}")

    def _populate_history(self, history: list[dict]) -> None:
        self.current_history = list(history)
        self.history_table.setRowCount(0)
        highlighted_row: int | None = None

        for row_index, record in enumerate(reversed(history)):
            self.history_table.insertRow(row_index)
            history_index = len(history) - 1 - row_index

            device_name = str(record["peer_device_name"])
            direction = str(record["direction"])
            history_kind = str(record.get("kind") or "text")
            message_text = format_history_content(record)
            history_marker_value = str(record.get("file_path") or record.get("text") or record.get("file_name") or "")

            items = [
                self._build_history_item(format_history_timestamp(str(record["created_at"]))),
                self._build_history_item(device_name),
                self._build_history_item(format_history_direction(direction)),
                self._build_history_item(message_text, selectable=True),
            ]

            for column, item in enumerate(items):
                self.history_table.setItem(row_index, column, item)

            delete_button = QPushButton("-")
            delete_button.setProperty("smallAction", True)
            delete_button.setToolTip("Delete")
            delete_button.clicked.connect(
                lambda _checked=False, index=history_index: self._delete_history_record(index)
            )
            self.history_table.setCellWidget(row_index, HISTORY_ACTION_COLUMN, delete_button)

            if (
                highlighted_row is None
                and self.highlighted_history_marker is not None
                and direction == "received"
                and (
                    history_kind,
                    str(record["peer_device_id"]),
                    device_name,
                    history_marker_value,
                )
                == self.highlighted_history_marker
            ):
                highlighted_row = row_index
                for item in items:
                    item.setBackground(HISTORY_HIGHLIGHT_COLOR)

        self.clear_history_button.setEnabled(bool(history))

        if highlighted_row is not None:
            self._select_history_message_cell(highlighted_row, scroll=True)

    def _build_history_item(self, text: str, *, selectable: bool = False) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        flags = Qt.ItemIsEnabled
        if selectable:
            flags |= Qt.ItemIsSelectable
        item.setFlags(flags)
        item.setToolTip(text)
        return item

    def _handle_status_changed(self, status: str) -> None:
        self.connection_button.setText("Connect" if status == "disconnected" else "Disconnect")
        if status in {"connecting", "disconnected"}:
            self.remote_server_version = ""
            self._refresh_header_details()
        self.statusBar().showMessage(status)

    def _handle_server_version_changed(self, version: str) -> None:
        self.remote_server_version = version.strip()
        self._refresh_header_details()

    def _handle_incoming_text(self, message: dict) -> None:
        sender_name = str(message.get("from_name") or message.get("from") or "Unknown device")
        sender_id = str(message.get("from") or "")
        text = str(message.get("text") or "")
        self.highlighted_history_marker = ("text", sender_id, sender_name, text)
        self._show_incoming_notification(sender_name, text=text)
        self.statusBar().showMessage(f"Received text from {sender_name}", 8000)

    def _handle_incoming_file(self, message: dict) -> None:
        sender_name = str(message.get("from_name") or message.get("from") or "Unknown device")
        sender_id = str(message.get("from") or "")
        file_name = str(message.get("file_name") or "Unnamed file")
        saved_path = str(message.get("saved_path") or "")
        file_size = int(message.get("file_size") or 0)
        self.highlighted_history_marker = ("file", sender_id, sender_name, saved_path or file_name)
        self._show_incoming_notification(sender_name, file_name=file_name)
        self.statusBar().showMessage(
            f"Received file from {sender_name}: {file_name} ({format_file_size(file_size)})",
            8000,
        )

    def _handle_ack(self, payload: dict) -> None:
        request_id = str(payload.get("request_id") or "")
        kind = str(payload.get("kind") or "text")
        if kind == "text":
            self.editor.clear()
            self.statusBar().showMessage(f"Text sent successfully ({request_id})", 6000)
            return
        self.statusBar().showMessage(f"File sent successfully ({request_id})", 6000)

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
        device_name = selected_items[0].data(Qt.UserRole + 1) or selected_items[0].text().splitlines()[0]
        self.selected_device_label.setText(f"Target: {device_name}")

    def _send_current_text(self) -> None:
        target_device_id = self._selected_device_id()
        text = self.editor.toPlainText().strip()

        if not target_device_id:
            QMessageBox.information(self, "HomeCopy", "Please select a target device first.")
            return
        if not text:
            QMessageBox.information(self, "HomeCopy", "Please enter some text before sending.")
            return

        assert self.runtime is not None
        self.runtime.send_text(target_device_id, text)
        self.statusBar().showMessage(f"Sending to {target_device_id}...", 4000)

    def _send_selected_file(self) -> None:
        target_device_id = self._selected_device_id()
        if not target_device_id:
            QMessageBox.information(self, "HomeCopy", "Please select a target device first.")
            return

        file_path, _selected_filter = QFileDialog.getOpenFileName(self, "Select File to Send")
        if not file_path:
            return

        assert self.runtime is not None
        self.runtime.send_file(target_device_id, file_path)
        self.statusBar().showMessage(f"Sending file to {target_device_id}...", 4000)

    def _handle_history_cell_pressed(self, row: int, column: int) -> None:
        if column == HISTORY_ACTION_COLUMN:
            return
        self._select_history_message_cell(row)

    def _handle_history_cell_double_clicked(self, row: int, column: int) -> None:
        if column == HISTORY_ACTION_COLUMN:
            return
        history_index = len(self.current_history) - 1 - row
        if history_index < 0 or history_index >= len(self.current_history):
            return
        record = self.current_history[history_index]
        if str(record.get("kind") or "text") == "file":
            file_path = str(record.get("file_path") or "")
            if not file_path:
                self.statusBar().showMessage("This file history entry does not have a local path.", 4000)
                return
            if not Path(file_path).exists():
                self.statusBar().showMessage("The file no longer exists at the stored path.", 4000)
                return
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            self.statusBar().showMessage("Opened the file from history.", 4000)
            return

        item = self.history_table.item(row, HISTORY_MESSAGE_COLUMN)
        if item is None:
            return
        self.editor.setPlainText(str(record.get("text") or item.text()))
        self.editor.setFocus()
        self.statusBar().showMessage("Loaded message into the editor.", 4000)

    def _normalize_history_selection(self) -> None:
        if self._syncing_history_selection:
            return
        selected_indexes = self.history_table.selectedIndexes()
        if not selected_indexes:
            return
        first_index = selected_indexes[0]
        if first_index.column() == HISTORY_MESSAGE_COLUMN and len(selected_indexes) == 1:
            return
        self._select_history_message_cell(first_index.row())

    def _select_history_message_cell(self, row: int, *, scroll: bool = False) -> None:
        item = self.history_table.item(row, HISTORY_MESSAGE_COLUMN)
        if item is None:
            return

        self._syncing_history_selection = True
        try:
            self.history_table.clearSelection()
            item.setSelected(True)
            self.history_table.setCurrentItem(item)
            if scroll:
                self.history_table.scrollToItem(item, QAbstractItemView.PositionAtTop)
        finally:
            self._syncing_history_selection = False

    def _refresh_header_details(self) -> None:
        self.client_device_label.setText(f"Device: {self.config.device_name}")
        self.client_ip_label.setText(f"IP: {resolve_preferred_local_host()}")
        server_text = format_server_display(self.config.server_url)
        if self.remote_server_version:
            server_text = f"{server_text} (v{self.remote_server_version})"
        self.client_server_label.setText(f"Server: {server_text}")
        self._refresh_server_section()

    def _refresh_local_server_stats(self) -> None:
        if not self._should_show_server_section():
            self.local_server_client_count = 0
            return

        if self.server_controller.started_by_app and not self.server_controller.is_running():
            self.local_server_client_count = 0
            self._refresh_server_section()
            return

        target_server_url = self.config.server_url if self._is_local_client_target() else local_server_display_address()
        if "://" not in target_server_url:
            target_server_url = f"ws://{target_server_url}/ws"

        stats = get_server_stats(target_server_url)
        if stats is None:
            if self.server_controller.started_by_app and self.server_controller.is_running():
                self.local_server_client_count = max(self.local_server_client_count, 0)
            else:
                self.local_server_client_count = 0
            self._refresh_server_section()
            return

        connected_clients = stats.get("connected_clients", 0)
        try:
            self.local_server_client_count = max(0, int(connected_clients))
        except (TypeError, ValueError):
            self.local_server_client_count = 0
        self._refresh_server_section()

    def _refresh_server_section(self) -> None:
        show_local_server = self._should_show_server_section()
        self.server_section.setVisible(show_local_server)
        if not show_local_server:
            return

        self.server_meta_label.setText(f"Listen: {local_server_display_address()}")
        self.server_clients_label.setText(f"Clients: {self.local_server_client_count}")
        if self.server_controller.started_by_app:
            if self.server_controller.is_running():
                self.server_toggle_button.setText("Stop Server")
            else:
                self.server_toggle_button.setText("Start Server")
            self.server_toggle_button.setEnabled(True)
            return

        self.server_toggle_button.setText("Start Server")
        self.server_toggle_button.setEnabled(False)

    def _should_show_server_section(self) -> bool:
        return self.server_controller.started_by_app or self._is_local_client_target()

    def _is_local_client_target(self) -> bool:
        return is_local_server_url(self.config.server_url)

    def _show_incoming_notification(
        self,
        sender_name: str,
        *,
        text: str | None = None,
        file_name: str | None = None,
    ) -> None:
        if self._should_mark_tray_unread():
            self._set_tray_unread_message(True)
        if not self.config.show_notification:
            return

        notification_text = format_notification_message(sender_name, text=text, file_name=file_name)
        if self.tray_icon is not None:
            self.tray_icon.showMessage(
                "HomeCopy",
                notification_text,
                QSystemTrayIcon.Information,
                5000,
            )
        self.notification_service.notify("HomeCopy", notification_text)

    def event(self, event: QEvent) -> bool:
        if (
            event.type() == QEvent.Show
            and self._hidden_to_tray
            and not self._restoring_from_tray
        ):
            QTimer.singleShot(0, self._restore_from_tray)
        if event.type() == QEvent.WindowActivate:
            self._set_tray_unread_message(False)
        return super().event(event)

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self.editor and event.type() == QEvent.KeyPress:
            modifiers = event.modifiers()
            if modifiers & Qt.ControlModifier and event.key() in {Qt.Key_Return, Qt.Key_Enter}:
                self._send_current_text()
                return True
            if modifiers & Qt.ControlModifier and event.key() == Qt.Key_K:
                self.editor.clear()
                return True
        return super().eventFilter(watched, event)

    def closeEvent(self, event: QCloseEvent) -> None:
        if (
            not self._quit_requested
            and self.config.minimize_to_tray
            and self.tray_icon is not None
        ):
            event.ignore()
            QTimer.singleShot(0, self._hide_to_tray)
            return
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
            and not self._tray_hide_pending
            and not self._restoring_from_tray
        ):
            self._tray_hide_pending = True
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
