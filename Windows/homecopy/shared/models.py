"""Pydantic models for websocket protocol messages."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .constants import PROTOCOL_VERSION


def normalize_device_id(value: str) -> str:
    return value.strip().lower()


class DeviceSummary(BaseModel):
    device_id: str = Field(pattern=r"^[A-Za-z0-9-]+$")
    device_name: str
    version: str | None = None

    @field_validator("device_id")
    @classmethod
    def normalize_device_id_field(cls, value: str) -> str:
        return normalize_device_id(value)


class RegisterMessage(BaseModel):
    type: Literal["register"]
    protocol_version: int = Field(default=PROTOCOL_VERSION)
    device_id: str = Field(pattern=r"^[A-Za-z0-9-]+$")
    device_name: str = Field(min_length=1, max_length=100)
    version: str | None = None
    token: str = ""

    @field_validator("device_id")
    @classmethod
    def normalize_device_id_field(cls, value: str) -> str:
        return normalize_device_id(value)


class RegisterOkMessage(BaseModel):
    type: Literal["register_ok"] = "register_ok"
    self: str
    server_version: str | None = None
    online_devices: list[DeviceSummary]


class SendTextMessage(BaseModel):
    type: Literal["send_text"]
    request_id: UUID
    to: str = Field(pattern=r"^[A-Za-z0-9-]+$")
    text: str = Field(min_length=1)

    @field_validator("to")
    @classmethod
    def normalize_target_device_id(cls, value: str) -> str:
        return normalize_device_id(value)


class SendFileStartMessage(BaseModel):
    type: Literal["send_file_start"]
    request_id: UUID
    file_id: UUID
    to: str = Field(pattern=r"^[A-Za-z0-9-]+$")
    file_name: str = Field(min_length=1, max_length=255)
    file_size: int = Field(ge=0)
    mime_type: str | None = None

    @field_validator("to")
    @classmethod
    def normalize_target_device_id(cls, value: str) -> str:
        return normalize_device_id(value)


class SendFileChunkMessage(BaseModel):
    type: Literal["send_file_chunk"]
    request_id: UUID
    file_id: UUID
    to: str = Field(pattern=r"^[A-Za-z0-9-]+$")
    chunk_index: int = Field(ge=0)
    content_b64: str = Field(min_length=1)

    @field_validator("to")
    @classmethod
    def normalize_target_device_id(cls, value: str) -> str:
        return normalize_device_id(value)


class SendFileCompleteMessage(BaseModel):
    type: Literal["send_file_complete"]
    request_id: UUID
    file_id: UUID
    to: str = Field(pattern=r"^[A-Za-z0-9-]+$")
    total_chunks: int = Field(ge=0)

    @field_validator("to")
    @classmethod
    def normalize_target_device_id(cls, value: str) -> str:
        return normalize_device_id(value)


class HeartbeatMessage(BaseModel):
    type: Literal["heartbeat"] = "heartbeat"
    sent_at: datetime


class IncomingTextMessage(BaseModel):
    type: Literal["incoming_text"] = "incoming_text"
    message_id: UUID
    from_: str = Field(alias="from")
    from_name: str
    text: str
    sent_at: datetime

    model_config = ConfigDict(populate_by_name=True)


class IncomingFileStartMessage(BaseModel):
    type: Literal["incoming_file_start"] = "incoming_file_start"
    message_id: UUID
    file_id: UUID
    from_: str = Field(alias="from")
    from_name: str
    file_name: str
    file_size: int = Field(ge=0)
    mime_type: str | None = None
    sent_at: datetime

    model_config = ConfigDict(populate_by_name=True)


class IncomingFileChunkMessage(BaseModel):
    type: Literal["incoming_file_chunk"] = "incoming_file_chunk"
    file_id: UUID
    chunk_index: int = Field(ge=0)
    content_b64: str = Field(min_length=1)


class IncomingFileCompleteMessage(BaseModel):
    type: Literal["incoming_file_complete"] = "incoming_file_complete"
    message_id: UUID
    file_id: UUID
    total_chunks: int = Field(ge=0)


class SendAckMessage(BaseModel):
    type: Literal["send_ack"] = "send_ack"
    request_id: UUID
    status: Literal["ok"]


class HeartbeatAckMessage(BaseModel):
    type: Literal["heartbeat_ack"] = "heartbeat_ack"
    sent_at: datetime


class DeviceListMessage(BaseModel):
    type: Literal["device_list"] = "device_list"
    devices: list[DeviceSummary]


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str


class HistoryRecord(BaseModel):
    direction: Literal["sent", "received"]
    peer_device_id: str
    peer_device_name: str
    kind: Literal["text", "file"] = "text"
    text: str = ""
    file_name: str | None = None
    file_size: int | None = Field(default=None, ge=0)
    file_path: str | None = None
    created_at: datetime

    @field_validator("peer_device_id")
    @classmethod
    def normalize_peer_device_id(cls, value: str) -> str:
        return normalize_device_id(value)

    @model_validator(mode="after")
    def validate_content(self) -> "HistoryRecord":
        if self.kind == "text":
            if not self.text.strip():
                raise ValueError("Text cannot be empty.")
            return self

        if not (self.file_name or "").strip():
            raise ValueError("File name is required for file history entries.")
        return self


ClientInboundMessage = Union[
    RegisterMessage,
    SendTextMessage,
    SendFileStartMessage,
    SendFileChunkMessage,
    SendFileCompleteMessage,
    HeartbeatMessage,
]
ServerOutboundMessage = Union[
    RegisterOkMessage,
    IncomingTextMessage,
    IncomingFileStartMessage,
    IncomingFileChunkMessage,
    IncomingFileCompleteMessage,
    SendAckMessage,
    HeartbeatAckMessage,
    DeviceListMessage,
    ErrorMessage,
]
