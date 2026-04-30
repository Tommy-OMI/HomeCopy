"""Shared desktop UI formatting helpers."""

from __future__ import annotations

from datetime import datetime


def normalize_device_id(value: str) -> str:
    return value.strip().lower()


def format_device_label(device_name: str, device_id: str) -> str:
    if normalize_device_id(device_name) == normalize_device_id(device_id):
        return device_name
    return f"{device_name}\n{device_id}"


def format_history_direction(direction: str) -> str:
    return "Received" if direction == "received" else "Sent"


def format_history_timestamp(value: str) -> str:
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return value.replace("T", " ").removesuffix("Z")
    return parsed.strftime("%Y-%m-%d %H:%M:%S")
