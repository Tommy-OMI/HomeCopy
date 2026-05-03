"""Async websocket client for HomeCopy."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable
from uuid import uuid4

import websockets
from pydantic import TypeAdapter
from websockets.asyncio.client import ClientConnection

from homecopy.client.config import ClientConfig
from homecopy.shared.constants import (
    DEFAULT_HEARTBEAT_INTERVAL,
    DEFAULT_HEARTBEAT_TIMEOUT,
    DEFAULT_RECONNECT_DELAYS,
    PROTOCOL_VERSION,
)
from homecopy.shared.models import (
    DeviceListMessage,
    ErrorMessage,
    HeartbeatAckMessage,
    IncomingTextMessage,
    RegisterOkMessage,
    SendAckMessage,
)

logger = logging.getLogger(__name__)

DeviceListHandler = Callable[[list[dict]], Awaitable[None]]
IncomingHandler = Callable[[IncomingTextMessage], Awaitable[None]]
AckHandler = Callable[[SendAckMessage], Awaitable[None]]
ErrorHandler = Callable[[ErrorMessage], Awaitable[None]]
StatusHandler = Callable[[str], Awaitable[None]]


class HomeCopyClient:
    def __init__(self, config: ClientConfig) -> None:
        self.config = config
        self.websocket: ClientConnection | None = None
        self.running = False
        self.registered_devices: list[dict] = []
        self.on_device_list: DeviceListHandler | None = None
        self.on_incoming_text: IncomingHandler | None = None
        self.on_ack: AckHandler | None = None
        self.on_error: ErrorHandler | None = None
        self.on_status: StatusHandler | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._last_heartbeat_ack_at = 0.0

    async def emit_status(self, status: str) -> None:
        logger.info("Client status: %s", status)
        if self.on_status is not None:
            await self.on_status(status)

    async def connect_forever(self) -> None:
        self.running = True
        attempt = 0

        while self.running:
            try:
                await self.emit_status("connecting")
                async with websockets.connect(self.config.server_url, ping_interval=20, ping_timeout=20) as websocket:
                    self.websocket = websocket
                    attempt = 0
                    await self._register()
                    self._last_heartbeat_ack_at = asyncio.get_running_loop().time()
                    self._start_heartbeat_task()
                    await self.emit_status("connected")
                    await self._receive_loop()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await self.emit_status(f"disconnected: {exc}")
                delay = DEFAULT_RECONNECT_DELAYS[min(attempt, len(DEFAULT_RECONNECT_DELAYS) - 1)]
                attempt += 1
                await asyncio.sleep(delay)
            finally:
                await self._stop_heartbeat_task()
                self.websocket = None

    async def _register(self) -> None:
        assert self.websocket is not None
        register_payload = {
            "type": "register",
            "protocol_version": PROTOCOL_VERSION,
            "device_id": self.config.device_id,
            "device_name": self.config.device_name,
            "token": self.config.auth_token,
        }
        await self.websocket.send(json.dumps(register_payload, ensure_ascii=False))

    async def _receive_loop(self) -> None:
        assert self.websocket is not None
        register_ok_adapter = TypeAdapter(RegisterOkMessage)
        device_list_adapter = TypeAdapter(DeviceListMessage)
        incoming_adapter = TypeAdapter(IncomingTextMessage)
        ack_adapter = TypeAdapter(SendAckMessage)
        heartbeat_ack_adapter = TypeAdapter(HeartbeatAckMessage)
        error_adapter = TypeAdapter(ErrorMessage)

        async for raw_message in self.websocket:
            payload = json.loads(raw_message)
            message_type = payload.get("type")

            if message_type == "register_ok":
                register_ok = register_ok_adapter.validate_python(payload)
                self.registered_devices = [item.model_dump(mode="json") for item in register_ok.online_devices]
                if self.on_device_list is not None:
                    await self.on_device_list(self.registered_devices)
                continue

            if message_type == "device_list":
                device_list = device_list_adapter.validate_python(payload)
                self.registered_devices = [item.model_dump(mode="json") for item in device_list.devices]
                if self.on_device_list is not None:
                    await self.on_device_list(self.registered_devices)
                continue

            if message_type == "incoming_text":
                incoming = incoming_adapter.validate_python(payload)
                if self.on_incoming_text is not None:
                    await self.on_incoming_text(incoming)
                continue

            if message_type == "send_ack":
                ack = ack_adapter.validate_python(payload)
                if self.on_ack is not None:
                    await self.on_ack(ack)
                continue

            if message_type == "heartbeat_ack":
                heartbeat_ack_adapter.validate_python(payload)
                self._last_heartbeat_ack_at = asyncio.get_running_loop().time()
                continue

            if message_type == "error":
                error = error_adapter.validate_python(payload)
                if self.on_error is not None:
                    await self.on_error(error)
                continue

            logger.warning("Ignored unknown message type=%s payload=%s", message_type, payload)

    async def send_text(self, target_device_id: str, text: str) -> None:
        if self.websocket is None:
            raise RuntimeError("Client is not connected.")

        payload = {
            "type": "send_text",
            "request_id": str(uuid4()),
            "to": target_device_id,
            "text": text,
        }
        await self.websocket.send(json.dumps(payload, ensure_ascii=False))

    def _start_heartbeat_task(self) -> None:
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _stop_heartbeat_task(self) -> None:
        if self._heartbeat_task is None:
            return

        task = self._heartbeat_task
        self._heartbeat_task = None
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def _heartbeat_loop(self) -> None:
        while self.running and self.websocket is not None:
            await asyncio.sleep(DEFAULT_HEARTBEAT_INTERVAL)
            if self.websocket is None or not self.running:
                return

            loop = asyncio.get_running_loop()
            if loop.time() - self._last_heartbeat_ack_at > DEFAULT_HEARTBEAT_TIMEOUT:
                logger.warning("Heartbeat timed out; closing stale websocket")
                await self.websocket.close(code=4001, reason="Heartbeat timed out")
                return

            payload = {
                "type": "heartbeat",
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
            await self.websocket.send(json.dumps(payload, ensure_ascii=False))

    def build_history_record(self, direction: str, peer_device_id: str, peer_device_name: str, text: str) -> dict:
        return {
            "direction": direction,
            "peer_device_id": peer_device_id,
            "peer_device_name": peer_device_name,
            "text": text,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def close(self) -> None:
        self.running = False
        if self.websocket is not None:
            await self.websocket.close()
