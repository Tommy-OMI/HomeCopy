"""Qt worker thread that bridges the websocket client into the GUI."""

from __future__ import annotations

import asyncio
import contextlib
from concurrent.futures import Future
from datetime import datetime, timezone

from PySide6.QtCore import QThread, Signal

from homecopy.client.config import ClientConfig
from homecopy.client.network.client import HomeCopyClient
from homecopy.client.services.clipboard_service import ClipboardService
from homecopy.client.services.history_service import HistoryService
from homecopy.shared.models import ErrorMessage, HistoryRecord, IncomingTextMessage, SendAckMessage


class ClientRuntimeThread(QThread):
    """Owns the asyncio loop and forwards client events to the Qt thread."""

    status_changed = Signal(str)
    devices_changed = Signal(list)
    server_version_changed = Signal(str)
    incoming_text = Signal(dict)
    ack_received = Signal(str)
    error_received = Signal(str)
    history_changed = Signal(list)

    def __init__(self, config: ClientConfig) -> None:
        super().__init__()
        self.config = config
        self.client: HomeCopyClient | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.history_service = HistoryService(config.history_path, config.history_limit)
        self.clipboard_service = ClipboardService()
        self.current_devices: list[dict] = []
        self._connection_task: asyncio.Task[None] | None = None

    def run(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.client = HomeCopyClient(self.config)
        self.client.on_device_list = self._handle_device_list
        self.client.on_incoming_text = self._handle_incoming_text
        self.client.on_ack = self._handle_ack
        self.client.on_error = self._handle_error
        self.client.on_status = self._handle_status
        self.client.on_server_version = self._handle_server_version

        self._emit_history_snapshot()
        self._ensure_client_connection()

        try:
            self.loop.run_forever()
        finally:
            pending = [task for task in asyncio.all_tasks(self.loop) if not task.done()]
            for task in pending:
                task.cancel()
            if pending:
                with contextlib.suppress(Exception):
                    self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            with contextlib.suppress(Exception):
                self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()
            self.loop = None
            self.client = None
            self._connection_task = None

    def send_text(self, target_device_id: str, text: str) -> None:
        if self.loop is None or self.client is None:
            self.error_received.emit("Client is not connected yet.")
            return

        future = asyncio.run_coroutine_threadsafe(self.client.send_text(target_device_id, text), self.loop)
        future.add_done_callback(lambda completed: self._after_send(completed, target_device_id, text))

    def connect_client(self) -> None:
        if self.loop is None:
            self.error_received.emit("Client runtime is not ready yet.")
            return
        self.loop.call_soon_threadsafe(self._ensure_client_connection)

    def disconnect_client(self) -> None:
        if self.loop is None or self.client is None:
            return

        future = asyncio.run_coroutine_threadsafe(self.client.close(), self.loop)
        future.add_done_callback(self._after_disconnect)

    def delete_history_record(self, history_index: int) -> None:
        self.history_service.delete_at(history_index)
        self._emit_history_snapshot()

    def clear_history(self) -> None:
        self.history_service.clear()
        self._emit_history_snapshot()

    def stop(self) -> None:
        if self.loop is None:
            return
        if self.client is not None:
            future = asyncio.run_coroutine_threadsafe(self.client.close(), self.loop)
            with contextlib.suppress(Exception):
                future.result(timeout=2)
        self.loop.call_soon_threadsafe(self.loop.stop)

    def _ensure_client_connection(self) -> None:
        if self.loop is None or self.client is None:
            return
        if self._connection_task is not None and not self._connection_task.done():
            return
        self._connection_task = self.loop.create_task(self.client.connect_forever())

    def _after_disconnect(self, future: Future[None]) -> None:
        with contextlib.suppress(Exception):
            future.result()
        self.current_devices = []
        self.devices_changed.emit([])
        self.server_version_changed.emit("")
        self.status_changed.emit("disconnected")

    def _after_send(self, future: Future[None], target_device_id: str, text: str) -> None:
        try:
            future.result()
        except Exception as exc:  # pragma: no cover - UI runtime callback
            self.error_received.emit(str(exc))
            return

        peer_name = next(
            (item["device_name"] for item in self.current_devices if item["device_id"] == target_device_id),
            target_device_id,
        )
        self.history_service.append(
            HistoryRecord(
                direction="sent",
                peer_device_id=target_device_id,
                peer_device_name=peer_name,
                text=text,
                created_at=datetime.now(timezone.utc),
            )
        )
        self._emit_history_snapshot()

    async def _handle_device_list(self, devices: list[dict]) -> None:
        self.current_devices = list(devices)
        self.devices_changed.emit(list(devices))

    async def _handle_incoming_text(self, message: IncomingTextMessage) -> None:
        if self.config.auto_copy_on_receive:
            try:
                self.clipboard_service.copy_text(message.text)
            except Exception as exc:  # pragma: no cover - OS-specific clipboard behavior
                self.error_received.emit(f"Clipboard update failed: {exc}")

        self.incoming_text.emit(message.model_dump(by_alias=True, mode="json"))
        self.history_service.append(
            HistoryRecord(
                direction="received",
                peer_device_id=message.from_,
                peer_device_name=message.from_name,
                text=message.text,
                created_at=datetime.now(timezone.utc),
            )
        )
        self._emit_history_snapshot()

    async def _handle_ack(self, message: SendAckMessage) -> None:
        self.ack_received.emit(f"{message.request_id}")

    async def _handle_error(self, message: ErrorMessage) -> None:
        self.error_received.emit(f"{message.code}: {message.message}")

    async def _handle_status(self, status: str) -> None:
        self.status_changed.emit(status)

    async def _handle_server_version(self, version: str) -> None:
        self.server_version_changed.emit(version)

    def _emit_history_snapshot(self) -> None:
        records = [item.model_dump(mode="json") for item in self.history_service.load()]
        self.history_changed.emit(records)
