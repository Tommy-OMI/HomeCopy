"""Filesystem path helpers for the installer runtime."""

from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "HomeCopy"


def data_root() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / APP_NAME
        return Path.home() / "AppData" / "Local" / APP_NAME
    raise RuntimeError(f"Unsupported platform: {sys.platform}")


def installer_root() -> Path:
    return data_root() / "installer"


def metadata_path() -> Path:
    return installer_root() / "installation.json"


def source_path() -> Path:
    return installer_root() / "source"


def staged_source_path() -> Path:
    return installer_root() / "source.staged"


def installed_app_path() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Applications" / "HomeCopy.app"
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return base / "Programs" / APP_NAME
    raise RuntimeError(f"Unsupported platform: {sys.platform}")
