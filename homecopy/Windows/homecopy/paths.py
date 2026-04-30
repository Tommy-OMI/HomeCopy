"""Runtime path helpers shared by source runs and packaged apps."""

from __future__ import annotations

import sys
from pathlib import Path


APP_NAME = "HomeCopy"


def application_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def runtime_data_root() -> Path:
    if getattr(sys, "frozen", False) and sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support" / APP_NAME
        root.mkdir(parents=True, exist_ok=True)
        return root
    return application_root()


def runtime_env_path() -> Path:
    return runtime_data_root() / ".env"
