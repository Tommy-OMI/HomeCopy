"""Installer metadata persistence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .paths import metadata_path
from .utils import ensure_directory


@dataclass
class InstallationMetadata:
    app_version: str
    commit: str
    installed_at: str
    installed_path: str
    platform: str
    ref: str
    repo: str
    source_path: str


def load_metadata() -> InstallationMetadata | None:
    path = metadata_path()
    if not path.exists():
        return None

    payload = json.loads(path.read_text(encoding="utf-8"))
    return InstallationMetadata(**payload)


def save_metadata(metadata: InstallationMetadata) -> Path:
    path = metadata_path()
    ensure_directory(path.parent)
    path.write_text(json.dumps(asdict(metadata), indent=2, sort_keys=True), encoding="utf-8")
    return path


def build_metadata(
    *,
    app_version: str,
    commit: str,
    installed_path: Path,
    platform: str,
    ref: str,
    repo: str,
    source_path: Path,
) -> InstallationMetadata:
    return InstallationMetadata(
        app_version=app_version,
        commit=commit,
        installed_at=datetime.now(timezone.utc).isoformat(),
        installed_path=str(installed_path),
        platform=platform,
        ref=ref,
        repo=repo,
        source_path=str(source_path),
    )
