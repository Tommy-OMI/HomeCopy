from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path

from .config import ProcessingConfig
from .fits_header import read_fits_metadata
from .models import ChannelStats, TargetStats


FITS_EXTENSIONS = {".fit", ".fits", ".fts"}
COMPLETION_MARKER = "omi_complete.json"
KNOWN_CHANNELS = {
    "L",
    "R",
    "G",
    "B",
    "HA",
    "HALPHA",
    "H-ALPHA",
    "OIII",
    "O3",
    "SII",
    "S2",
    "CLEAR",
}


def scan_dropbox_root(config: ProcessingConfig, limit: int | None = None) -> list[TargetStats]:
    root = config.dropbox_root
    if not root.exists():
        raise FileNotFoundError(f"Dropbox root not found: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Dropbox root is not a directory: {root}")

    targets: list[TargetStats] = []
    for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        targets.append(scan_target_folder(child, config, limit=limit))

    return targets


def scan_target_folder(path: Path, config: ProcessingConfig, limit: int | None = None) -> TargetStats:
    now = time.time()
    stable_after_seconds = config.stable_after_minutes * 60
    auto_ready_after_seconds = config.auto_ready_after_hours * 3600
    max_files = limit or config.max_scan_files

    channel_map: dict[str, ChannelStats] = defaultdict(lambda: ChannelStats(name="Unknown"))
    fits_count = 0
    total_size = 0
    newest_mtime: float | None = None
    oldest_unstable_file: str | None = None
    all_stable = True

    for file_path in _iter_fits(path, max_files=max_files):
        fits_count += 1
        stat = file_path.stat()
        total_size += stat.st_size
        newest_mtime = stat.st_mtime if newest_mtime is None else max(newest_mtime, stat.st_mtime)

        file_age = now - stat.st_mtime
        if file_age < stable_after_seconds:
            all_stable = False
            if oldest_unstable_file is None:
                oldest_unstable_file = str(file_path)

        metadata = read_fits_metadata(file_path)
        channel_name = normalize_channel(str(metadata.get("filter") or _infer_channel_from_path(file_path, path)))
        exposure_seconds = float(metadata.get("exposure_seconds") or 0)

        if channel_name not in channel_map:
            channel_map[channel_name] = ChannelStats(name=channel_name)
        channel_map[channel_name].fits_count += 1
        channel_map[channel_name].exposure_seconds += exposure_seconds

    has_marker = (path / COMPLETION_MARKER).exists()
    status = _derive_status(
        fits_count=fits_count,
        all_stable=all_stable,
        has_marker=has_marker,
        newest_mtime=newest_mtime,
        now=now,
        auto_ready_after_seconds=auto_ready_after_seconds,
    )

    channels = sorted(channel_map.values(), key=lambda item: item.name)
    return TargetStats(
        name=path.name,
        path=str(path),
        status=status,
        fits_count=fits_count,
        total_size_bytes=total_size,
        channels=channels,
        has_completion_marker=has_marker,
        newest_mtime=newest_mtime,
        oldest_unstable_file=oldest_unstable_file,
    )


def normalize_channel(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return "Unknown"

    upper = cleaned.upper().replace("_", "-").replace(" ", "")
    aliases = {
        "LUMINANCE": "L",
        "LUM": "L",
        "RED": "R",
        "GREEN": "G",
        "BLUE": "B",
        "HALPHA": "Ha",
        "H-ALPHA": "Ha",
        "HA": "Ha",
        "O3": "OIII",
        "O-III": "OIII",
        "S2": "SII",
        "S-II": "SII",
    }
    if upper in aliases:
        return aliases[upper]
    if upper in KNOWN_CHANNELS:
        return cleaned if len(cleaned) <= 4 else upper
    return cleaned


def _iter_fits(path: Path, max_files: int):
    yielded = 0
    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in FITS_EXTENSIONS:
            continue
        yielded += 1
        if yielded > max_files:
            break
        yield file_path


def _infer_channel_from_path(file_path: Path, target_root: Path) -> str:
    try:
        relative_parts = file_path.relative_to(target_root).parts
    except ValueError:
        return "Unknown"

    for part in reversed(relative_parts[:-1]):
        normalized = normalize_channel(part)
        if normalized != "Unknown":
            return normalized
    return "Unknown"


def _derive_status(
    *,
    fits_count: int,
    all_stable: bool,
    has_marker: bool,
    newest_mtime: float | None,
    now: float,
    auto_ready_after_seconds: int,
) -> str:
    if fits_count == 0:
        return "empty"
    if not all_stable:
        return "capturing"
    if has_marker:
        return "ready"
    if auto_ready_after_seconds > 0 and newest_mtime is not None:
        if now - newest_mtime >= auto_ready_after_seconds:
            return "ready"
    return "stable"

