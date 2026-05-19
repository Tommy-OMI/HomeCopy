"""Shared desktop UI formatting helpers."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlsplit


def normalize_device_label_key(value: str) -> str:
    return "".join(char.lower() for char in value if char.isalnum())


def normalize_device_id(value: str) -> str:
    return value.strip().lower()


def format_device_label(device_name: str, device_id: str, version: str | None = None) -> str:
    version_suffix = f" (v{version})" if version else ""
    if normalize_device_label_key(device_name) == normalize_device_label_key(device_id):
        return f"{device_name}{version_suffix}"
    return f"{device_name}{version_suffix}\n{device_id}"


def format_history_direction(direction: str) -> str:
    return "Received" if direction == "received" else "Sent"


def format_file_size(byte_count: int | None) -> str:
    if byte_count is None:
        return "unknown size"
    size = float(byte_count)
    units = ["B", "KB", "MB", "GB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{int(byte_count)} B"


def format_history_content(record: dict) -> str:
    if str(record.get("kind") or "text") == "file":
        file_name = str(record.get("file_name") or "Unnamed file")
        return f"File: {file_name} ({format_file_size(record.get('file_size'))})"
    return str(record.get("text") or "")


def format_history_timestamp(value: str) -> str:
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return value.replace("T", " ").removesuffix("Z")
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def format_server_display(server_url: str) -> str:
    parts = urlsplit(server_url)
    if not parts.scheme or not parts.netloc:
        return server_url
    return parts.netloc


def format_notification_message(
    sender_name: str,
    *,
    text: str | None = None,
    file_name: str | None = None,
    limit: int = 160,
) -> str:
    if file_name:
        return f"{sender_name} sent {file_name}"

    collapsed = " ".join((text or "").split())
    if not collapsed:
        return f"New text from {sender_name}"
    if len(collapsed) > limit:
        collapsed = f"{collapsed[: max(0, limit - 1)].rstrip()}…"
    return f"{sender_name}: {collapsed}"
