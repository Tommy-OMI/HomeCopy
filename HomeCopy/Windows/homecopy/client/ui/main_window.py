"""Main PySide6 window for the HomeCopy client."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
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
from homecopy.client.ui.hotkey_dialog import HotkeyDialog
from homecopy.client.ui.runtime import ClientRuntimeThread
from homecopy.client.ui.setup_dialog import SetupDialog
from homecopy_shared.startup_policy import EmbeddedServerController
from homecopy_shared.ui_formatting import (
    format_device_label,
    format_history_direction,
    format_history_timestamp,
)


HISTORY_MESSAGE_COLUMN = 3
HISTORY_HIGHLIGHT_COLOR = QColor("#f8e8a6")

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
        self.highlighted_history_marker: tuple[str, str, str] | None = None
        self._syncing_history_selection = False

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
        content_layout.addWidget(self._build_device_panel(), 1)
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
        panel.setMinimumWidth(180)
        panel.setMaximumWidth(240)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Online Devices")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #183153;")
        description = QLabel("Double-click a device to target it quickly.")
        description.setStyleSheet("color: #6f655d;")

        self.device_list = QListWidget()
        self.device_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.device_list.setMinimumWidth(150)
        self.device_list.setMaximumWidth(210)

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
        self.editor.installEventFilter(self)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        self.send_button = QPushButton("Send")
        self.clear_button = QPushButton("Clear")
        self.hotkey_button = QPushButton("Hotkey")
        button_row.addWidget(self.send_button)
        button_row.addWidget(self.clear_button)
        button_row.addWidget(self.hotkey_button)
        button_row.addStretch(1)

        history_title = QLabel("Recent History")
        history_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #183153;")

        self.history_table = QTableWidget(0, 4)
        self.history_table.setHorizontalHeaderLabels(["Date Time", "Device", "Direction", "Message"])
        self.history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.setWordWrap(False)
        self.history_table.setShowGrid(False)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.verticalHeader().setDefaultSectionSize(34)

        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.editor, 2)
        layout.addLayout(button_row)
        layout.addWidget(history_title)
        layout.addWidget(self.history_table, 5)
        return panel

    def _connect_signals(self) -> None:
        self.send_button.clicked.connect(self._send_current_text)
        self.clear_button.clicked.connect(self.editor.clear)
        self.hotkey_button.clicked.connect(self._open_hotkey_dialog)
        self.device_list.itemSelectionChanged.connect(self._update_selected_device_label)
        self.device_list.itemDoubleClicked.connect(lambda _: self._send_current_text())
        self.history_table.cellPressed.connect(self._handle_history_cell_pressed)
        self.history_table.itemSelectionChanged.connect(self._normalize_history_selection)
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
        if not self.config.minimize_to_tray or self.tray_icon is None:
            return
        self.hide()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
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
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _toggle_visibility_from_hotkey(self) -> None:
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
            item = QListWidgetItem(format_device_label(device_name, device_id))
            item.setData(Qt.UserRole, device["device_id"])
            self.device_list.addItem(item)
            if device["device_id"] == selected_device_id:
                item.setSelected(True)

        self._update_selected_device_label()
        self.statusBar().showMessage(f"Online devices updated: {len(self.current_devices)}")

    def _populate_history(self, history: list[dict]) -> None:
        self.history_table.setRowCount(0)
        highlighted_row: int | None = None

        for row_index, record in enumerate(reversed(history)):
            self.history_table.insertRow(row_index)

            device_name = str(record["peer_device_name"])
            message_text = str(record["text"])
            direction = str(record["direction"])

            items = [
                self._build_history_item(format_history_timestamp(str(record["created_at"]))),
                self._build_history_item(device_name),
                self._build_history_item(format_history_direction(direction)),
                self._build_history_item(message_text, selectable=True),
            ]

            for column, item in enumerate(items):
                self.history_table.setItem(row_index, column, item)

            if (
                highlighted_row is None
                and self.highlighted_history_marker is not None
                and direction == "received"
                and (
                    str(record["peer_device_id"]),
                    device_name,
                    message_text,
                )
                == self.highlighted_history_marker
            ):
                highlighted_row = row_index
                for item in items:
                    item.setBackground(HISTORY_HIGHLIGHT_COLOR)

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
        self.status_badge.setText(status)
        self.statusBar().showMessage(status)

    def _handle_incoming_text(self, message: dict) -> None:
        sender_name = str(message.get("from_name") or message.get("from") or "Unknown device")
        sender_id = str(message.get("from") or "")
        text = str(message.get("text") or "")
        self.highlighted_history_marker = (sender_id, sender_name, text)
        self.statusBar().showMessage(f"Received text from {sender_name}", 8000)

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

        assert self.runtime is not None
        self.runtime.send_text(target_device_id, text)
        self.statusBar().showMessage(f"Sending to {target_device_id}...", 4000)

    def _handle_history_cell_pressed(self, row: int, _column: int) -> None:
        self._select_history_message_cell(row)

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
