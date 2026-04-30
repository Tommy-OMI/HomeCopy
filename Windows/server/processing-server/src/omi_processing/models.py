from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChannelStats:
    name: str
    fits_count: int = 0
    exposure_seconds: float = 0.0


@dataclass
class TargetStats:
    name: str
    path: str
    status: str
    fits_count: int
    total_size_bytes: int
    channels: list[ChannelStats] = field(default_factory=list)
    has_completion_marker: bool = False
    newest_mtime: float | None = None
    oldest_unstable_file: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "path": self.path,
            "status": self.status,
            "fitsCount": self.fits_count,
            "totalSizeBytes": self.total_size_bytes,
            "channels": [
                {
                    "name": channel.name,
                    "fitsCount": channel.fits_count,
                    "exposureSeconds": channel.exposure_seconds,
                }
                for channel in self.channels
            ],
            "hasCompletionMarker": self.has_completion_marker,
            "newestMtime": self.newest_mtime,
            "oldestUnstableFile": self.oldest_unstable_file,
        }

