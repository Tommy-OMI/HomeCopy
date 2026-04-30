"""Shared LAN discovery protocol helpers."""

from __future__ import annotations

import json
import ipaddress
import re
import socket
import subprocess
import sys
from typing import Any

from pydantic import BaseModel, Field

from homecopy.shared.constants import PROTOCOL_VERSION


DISCOVERY_MAGIC = "homecopy-discovery"


class DiscoveryProbe(BaseModel):
    magic: str = Field(default=DISCOVERY_MAGIC)
    type: str = Field(default="discover_server")
    protocol_version: int = Field(default=PROTOCOL_VERSION)


class DiscoveryAnnouncement(BaseModel):
    magic: str = Field(default=DISCOVERY_MAGIC)
    type: str = Field(default="server_announce")
    protocol_version: int = Field(default=PROTOCOL_VERSION)
    server_url: str
    server_name: str
    discovery_port: int


def encode_discovery_message(message: BaseModel) -> bytes:
    return json.dumps(message.model_dump(mode="json"), ensure_ascii=False).encode("utf-8")


def decode_discovery_message(payload: bytes) -> dict[str, Any]:
    return json.loads(payload.decode("utf-8"))


def _normalize_netmask(raw_netmask: str) -> str:
    if raw_netmask.startswith("0x"):
        value = int(raw_netmask, 16)
        return socket.inet_ntoa(value.to_bytes(4, byteorder="big"))
    return raw_netmask


def local_ipv4_interfaces() -> list[tuple[str, str | None]]:
    interfaces: list[tuple[str, str | None]] = []

    if sys.platform in {"darwin", "linux"}:
        try:
            output = subprocess.check_output(["ifconfig"], text=True, stderr=subprocess.DEVNULL)
        except Exception:
            output = ""

        pattern = re.compile(
            r"\sinet\s+(\d+\.\d+\.\d+\.\d+)\s+netmask\s+(0x[0-9a-fA-F]+|\d+\.\d+\.\d+\.\d+)(?:\s+broadcast\s+(\d+\.\d+\.\d+\.\d+))?"
        )
        for line in output.splitlines():
            match = pattern.search(line)
            if not match:
                continue

            address, raw_netmask, broadcast = match.groups()
            if address.startswith("127."):
                continue

            try:
                network = ipaddress.IPv4Network(f"{address}/{_normalize_netmask(raw_netmask)}", strict=False)
                derived_broadcast = str(network.broadcast_address)
            except Exception:
                derived_broadcast = None

            interfaces.append((address, broadcast or derived_broadcast))

    if not interfaces:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                address = sock.getsockname()[0]
                if address and not address.startswith("127."):
                    interfaces.append((address, None))
        except OSError:
            pass

    return interfaces


def local_ipv4_addresses() -> set[str]:
    return {address for address, _ in local_ipv4_interfaces()}


def discovery_broadcast_targets() -> list[str]:
    targets = ["255.255.255.255"]
    for _, broadcast in local_ipv4_interfaces():
        if broadcast and broadcast not in targets:
            targets.append(broadcast)
    return targets
