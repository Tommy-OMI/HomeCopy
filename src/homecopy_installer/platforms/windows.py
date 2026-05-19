"""Windows build and install helpers."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from ..paths import data_root, installed_app_path
from ..python_runtime import PythonCommand
from ..utils import ensure_directory, replace_tree, run_command


def build_and_install(source_root: Path, python_command: PythonCommand) -> Path:
    windows_root = source_root / "Windows"
    run_command(
        python_command.command + ["scripts/build_client.py"],
        cwd=windows_root,
        env=os.environ.copy(),
    )

    built_dir = windows_root / "dist" / "HomeCopyClient"
    target_dir = installed_app_path()
    replace_tree(built_dir, target_dir)

    ensure_directory(data_root())
    env_example = windows_root / ".env.example"
    if env_example.exists():
        shutil.copy2(env_example, data_root() / ".env.example")

    return target_dir / "HomeCopyClient.exe"
