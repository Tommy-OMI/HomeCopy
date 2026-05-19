"""Protocol parsing helpers for the relay server."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError, TypeAdapter

from homecopy.shared.models import (
    HeartbeatMessage,
    RegisterMessage,
    SendFileChunkMessage,
    SendFileCompleteMessage,
    SendFileStartMessage,
    SendTextMessage,
)

register_adapter = TypeAdapter(RegisterMessage)
send_text_adapter = TypeAdapter(SendTextMessage)
send_file_start_adapter = TypeAdapter(SendFileStartMessage)
send_file_chunk_adapter = TypeAdapter(SendFileChunkMessage)
send_file_complete_adapter = TypeAdapter(SendFileCompleteMessage)
heartbeat_adapter = TypeAdapter(HeartbeatMessage)


def parse_register_message(payload: Any) -> RegisterMessage:
    try:
        return register_adapter.validate_python(payload)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


def parse_send_text_message(payload: Any) -> SendTextMessage:
    try:
        return send_text_adapter.validate_python(payload)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


def parse_send_file_start_message(payload: Any) -> SendFileStartMessage:
    try:
        return send_file_start_adapter.validate_python(payload)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


def parse_send_file_chunk_message(payload: Any) -> SendFileChunkMessage:
    try:
        return send_file_chunk_adapter.validate_python(payload)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


def parse_send_file_complete_message(payload: Any) -> SendFileCompleteMessage:
    try:
        return send_file_complete_adapter.validate_python(payload)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


def parse_heartbeat_message(payload: Any) -> HeartbeatMessage:
    try:
        return heartbeat_adapter.validate_python(payload)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
