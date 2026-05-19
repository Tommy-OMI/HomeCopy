"""Helpers for receiving and storing relayed files."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path


def sanitize_file_name(file_name: str) -> str:
    sanitized = Path(file_name).name.strip()
    return sanitized or "received-file"


def unique_destination_path(root: Path, file_name: str) -> Path:
    candidate = root / sanitize_file_name(file_name)
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2
    while True:
        candidate = root / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


@dataclass
class PendingIncomingFile:
    file_id: str
    sender_id: str
    sender_name: str
    file_name: str
    file_size: int
    mime_type: str | None
    sent_at: str
    temp_path: Path
    received_chunks: int = 0
    written_bytes: int = 0


class IncomingFileStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.temp_root = root / ".incoming"
        self._pending: dict[str, PendingIncomingFile] = {}

    def start_transfer(
        self,
        *,
        file_id: str,
        sender_id: str,
        sender_name: str,
        file_name: str,
        file_size: int,
        mime_type: str | None,
        sent_at: str,
    ) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.temp_root.mkdir(parents=True, exist_ok=True)

        temp_path = self.temp_root / f"{file_id}.part"
        if temp_path.exists():
            temp_path.unlink()
        temp_path.touch()

        self._pending[file_id] = PendingIncomingFile(
            file_id=file_id,
            sender_id=sender_id,
            sender_name=sender_name,
            file_name=sanitize_file_name(file_name),
            file_size=file_size,
            mime_type=mime_type,
            sent_at=sent_at,
            temp_path=temp_path,
        )

    def append_chunk(self, *, file_id: str, chunk_index: int, content_b64: str) -> None:
        pending = self._pending.get(file_id)
        if pending is None:
            raise ValueError("Received file chunk without an active file transfer.")
        if chunk_index != pending.received_chunks:
            raise ValueError("Received file chunk out of sequence.")

        chunk = base64.b64decode(content_b64.encode("ascii"), validate=True)
        pending.temp_path.parent.mkdir(parents=True, exist_ok=True)
        with pending.temp_path.open("ab") as handle:
            handle.write(chunk)

        pending.received_chunks += 1
        pending.written_bytes += len(chunk)

    def complete_transfer(self, *, file_id: str, total_chunks: int) -> dict[str, str | int | None]:
        pending = self._pending.pop(file_id, None)
        if pending is None:
            raise ValueError("Received file completion without an active file transfer.")
        if total_chunks != pending.received_chunks:
            raise ValueError("Received file completion with a mismatched chunk count.")
        if pending.written_bytes != pending.file_size:
            raise ValueError("Received file size does not match the announced file size.")

        destination = unique_destination_path(self.root, pending.file_name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        pending.temp_path.replace(destination)

        return {
            "file_id": pending.file_id,
            "from": pending.sender_id,
            "from_name": pending.sender_name,
            "file_name": pending.file_name,
            "file_size": pending.file_size,
            "mime_type": pending.mime_type,
            "saved_path": str(destination),
            "sent_at": pending.sent_at,
        }

    def discard_transfer(self, file_id: str) -> None:
        pending = self._pending.pop(file_id, None)
        if pending is None:
            return
        if pending.temp_path.exists():
            pending.temp_path.unlink()
