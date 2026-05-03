"""Protocol parsing helpers for the relay server."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError, TypeAdapter

from homecopy.shared.models import HeartbeatMessage, RegisterMessage, SendTextMessage

register_adapter = TypeAdapter(RegisterMessage)
send_text_adapter = TypeAdapter(SendTextMessage)
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


def parse_heartbeat_message(payload: Any) -> HeartbeatMessage:
    try:
        return heartbeat_adapter.validate_python(payload)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
