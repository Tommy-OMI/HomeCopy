"""macOS build and install helpers."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from ..paths import data_root, installed_app_path
from ..python_runtime import PythonCommand
from ..utils import ensure_directory, replace_tree, run_command


def build_and_install(source_root: Path, python_command: PythonCommand) -> Path:
    mac_root = source_root / "MacOS"
    env = os.environ.copy()
    env["PYTHON_BIN"] = python_command.command[0]

    run_command(["bash", "package_macos.command"], cwd=mac_root, env=env)

    built_app = mac_root / "dist" / "HomeCopyClient-macOS" / "HomeCopyClient.app"
    target_app = installed_app_path()
    replace_tree(built_app, target_app)

    shared_app = Path.home() / "Shared" / "HomeCopy.app"
    replace_tree(built_app, shared_app)

    ensure_directory(data_root())
    env_example = mac_root / ".env.example"
    if env_example.exists():
        shutil.copy2(env_example, data_root() / ".env.example")

    return target_app
