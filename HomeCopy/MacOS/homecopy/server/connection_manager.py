"""In-memory connection registry for online devices."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import WebSocket

from homecopy.shared.models import DeviceListMessage, DeviceSummary

logger = logging.getLogger(__name__)


@dataclass
class DeviceConnection:
    websocket: WebSocket
    device_id: str
    device_name: str
    connected_at: datetime
    remote_addr: str


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, DeviceConnection] = {}

    def is_online(self, device_id: str) -> bool:
        return device_id in self._connections

    def get(self, device_id: str) -> DeviceConnection | None:
        return self._connections.get(device_id)

    def get_device_list(self, exclude_device_id: str | None = None) -> list[DeviceSummary]:
        return [
            DeviceSummary(device_id=conn.device_id, device_name=conn.device_name)
            for conn in sorted(self._connections.values(), key=lambda item: item.device_name.lower())
            if conn.device_id != exclude_device_id
        ]

    async def register(self, websocket: WebSocket, device_id: str, device_name: str, remote_addr: str) -> None:
        existing = self._connections.get(device_id)
        if existing is not None:
            logger.info("Replacing previous connection for device_id=%s", device_id)
            await existing.websocket.close(code=4002, reason="Replaced by a new connection")

        self._connections[device_id] = DeviceConnection(
            websocket=websocket,
            device_id=device_id,
            device_name=device_name,
            connected_at=datetime.now(timezone.utc),
            remote_addr=remote_addr,
        )

    async def unregister(self, websocket: WebSocket) -> DeviceConnection | None:
        for device_id, conn in list(self._connections.items()):
            if conn.websocket is websocket:
                self._connections.pop(device_id, None)
                return conn
        return None

    async def send_json(self, device_id: str, payload: dict) -> None:
        connection = self._connections[device_id]
        await connection.websocket.send_json(payload)

    async def broadcast_device_list(self) -> None:
        if not self._connections:
            return

        payload = DeviceListMessage(devices=self.get_device_list()).model_dump(by_alias=True, mode="json")
        stale_device_ids: list[str] = []
        for device_id, connection in self._connections.items():
            try:
                await connection.websocket.send_json(payload)
            except Exception:
                logger.exception("Failed to broadcast device list to device_id=%s", device_id)
                stale_device_ids.append(device_id)

        for device_id in stale_device_ids:
            self._connections.pop(device_id, None)
