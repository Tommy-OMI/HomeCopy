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
        return self._save(history[-self.limit :])

    def delete_at(self, index: int) -> list[HistoryRecord]:
        history = self.load()
        if 0 <= index < len(history):
            del history[index]
        return self._save(history)

    def clear(self) -> list[HistoryRecord]:
        return self._save([])

    def _save(self, history: list[HistoryRecord]) -> list[HistoryRecord]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps([item.model_dump(mode="json") for item in history], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return history
