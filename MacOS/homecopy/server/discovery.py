"""LAN discovery broadcaster for the HomeCopy relay server."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import socket

from homecopy.server.config import ServerSettings
from homecopy.shared.discovery import (
    DiscoveryAnnouncement,
    DiscoveryProbe,
    discovery_broadcast_targets,
    decode_discovery_message,
    encode_discovery_message,
)

logger = logging.getLogger(__name__)


def resolve_advertise_host(settings: ServerSettings) -> str:
    if settings.discovery_advertise_host:
        return settings.discovery_advertise_host

    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
        try:
            sock.connect(("8.8.8.8", 80))
            host = sock.getsockname()[0]
            if host:
                return host
        except OSError:
            logger.debug("Falling back to hostname-based LAN address detection")

    try:
        host = socket.gethostbyname(socket.gethostname())
        if host and not host.startswith("127."):
            return host
    except OSError:
        logger.debug("Hostname lookup failed for LAN address detection")

    return "127.0.0.1"


class _DiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, broadcaster: "LanDiscoveryBroadcaster") -> None:
        self.broadcaster = broadcaster

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.broadcaster.transport = transport  # type: ignore[assignment]

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            payload = decode_discovery_message(data)
        except Exception:
            return

        if payload.get("type") != "discover_server":
            return

        try:
            DiscoveryProbe.model_validate(payload)
        except Exception:
            return

        logger.debug("Discovery probe received from %s:%s", addr[0], addr[1])
        self.broadcaster.send_announcement(addr)

    def error_received(self, exc: Exception) -> None:
        logger.warning("Discovery socket error: %s", exc)


class LanDiscoveryBroadcaster:
    def __init__(self, settings: ServerSettings) -> None:
        self.settings = settings
        self.transport: asyncio.DatagramTransport | None = None
        self._broadcast_task: asyncio.Task[None] | None = None
        self._announcement: DiscoveryAnnouncement | None = None

    async def start(self) -> None:
        if not self.settings.discovery_enabled:
            logger.info("LAN discovery is disabled")
            return

        loop = asyncio.get_running_loop()
        advertise_host = resolve_advertise_host(self.settings)
        self._announcement = DiscoveryAnnouncement(
            server_url=f"ws://{advertise_host}:{self.settings.port}/ws",
            server_name=socket.gethostname(),
            discovery_port=self.settings.discovery_port,
        )

        await loop.create_datagram_endpoint(
            lambda: _DiscoveryProtocol(self),
            local_addr=("0.0.0.0", self.settings.discovery_port),
            allow_broadcast=True,
            family=socket.AF_INET,
        )
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info(
            "LAN discovery started advertise_url=%s discovery_port=%s",
            self._announcement.server_url,
            self.settings.discovery_port,
        )

    async def stop(self) -> None:
        if self._broadcast_task is not None:
            self._broadcast_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._broadcast_task
            self._broadcast_task = None

        if self.transport is not None:
            self.transport.close()
            self.transport = None

    async def _broadcast_loop(self) -> None:
        while True:
            for target in discovery_broadcast_targets():
                self.send_announcement((target, self.settings.discovery_port))
            await asyncio.sleep(self.settings.discovery_interval)

    def send_announcement(self, target: tuple[str, int]) -> None:
        if self.transport is None or self._announcement is None:
            return
        self.transport.sendto(encode_discovery_message(self._announcement), target)
