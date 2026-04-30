"""JSON-backed local history storage."""

from __future__ import annotations

import json
from pathlib import Path

from homecopy.shared.models import HistoryRecord


class HistoryService:
    def __init__(self, path: Path, limit: int) -> None:
        self.path = path
        self.limit = limit

    def load(self) -> list[HistoryRecord]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return [HistoryRecord.model_validate(item) for item in raw]

    def append(self, record: HistoryRecord) -> list[HistoryRecord]:
        history = self.load()
        history.append(record)
        history = history[-self.limit :]
        self.path.write_text(
            json.dumps([item.model_dump(mode="json") for item in history], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return history
