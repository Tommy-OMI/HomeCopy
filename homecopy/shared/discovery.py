"""Shared LAN discovery protocol helpers."""

from __future__ import annotations

import json
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
