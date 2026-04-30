"""LAN discovery client helpers."""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from homecopy.shared.discovery import (
    DiscoveryAnnouncement,
    DiscoveryProbe,
    decode_discovery_message,
    discovery_broadcast_targets,
    encode_discovery_message,
    local_ipv4_addresses,
)


@dataclass
class DiscoveryResult:
    server_url: str
    server_name: str
    discovery_port: int
    responder_ip: str


def _normalize_server_url(server_url: str, responder_ip: str) -> str:
    try:
        parts = urlsplit(server_url)
    except Exception:
        return server_url

    host = parts.hostname or ""
    if not host:
        return server_url

    if host == "localhost" or host == "0.0.0.0" or host == "::1" or host.startswith("127."):
        port = parts.port
        netloc = responder_ip if port is None else f"{responder_ip}:{port}"
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))

    return server_url


class _DiscoveryClientProtocol(asyncio.DatagramProtocol):
    def __init__(self, discovery_port: int) -> None:
        self.discovery_port = discovery_port
        self.transport: asyncio.DatagramTransport | None = None
        self.results: dict[str, DiscoveryResult] = {}

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]
        probe = encode_discovery_message(DiscoveryProbe())
        for target in discovery_broadcast_targets():
            self.transport.sendto(probe, (target, self.discovery_port))

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            payload = decode_discovery_message(data)
            announcement = DiscoveryAnnouncement.model_validate(payload)
        except Exception:
            return

        normalized_url = _normalize_server_url(announcement.server_url, addr[0])
        self.results[addr[0]] = DiscoveryResult(
            server_url=normalized_url,
            server_name=announcement.server_name,
            discovery_port=announcement.discovery_port,
            responder_ip=addr[0],
        )


async def discover_server(
    timeout: float = 3.0,
    discovery_port: int = 8766,
) -> DiscoveryResult | None:
    loop = asyncio.get_running_loop()
    protocol = _DiscoveryClientProtocol(discovery_port)
    try:
        transport, _ = await loop.create_datagram_endpoint(
            lambda: protocol,
            local_addr=("0.0.0.0", 0),
            allow_broadcast=True,
            family=socket.AF_INET,
        )
    except OSError:
        return None

    try:
        await asyncio.sleep(timeout)
        results = list(protocol.results.values())
        if not results:
            return None

        local_ips = local_ipv4_addresses()
        remote_results = [
            item for item in results
            if item.responder_ip not in local_ips and not item.responder_ip.startswith("127.")
        ]
        if remote_results:
            return remote_results[0]
        return results[0]
    finally:
        transport.close()
