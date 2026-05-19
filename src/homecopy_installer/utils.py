"""Shared installer utility helpers."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Mapping
from uuid import uuid4


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path)


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_command(
    command: list[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
) -> None:
    print(f"[run] {' '.join(command)}")
    subprocess.run(command, check=True, cwd=cwd, env=dict(env) if env else None)


def replace_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(f"Source directory does not exist: {source}")

    ensure_directory(destination.parent)
    staging = destination.parent / f".{destination.name}.staging-{uuid4().hex}"
    backup = destination.parent / f".{destination.name}.backup-{uuid4().hex}"

    remove_path(staging)
    remove_path(backup)
    shutil.copytree(source, staging, symlinks=True)

    if destination.exists():
        destination.rename(backup)

    staging.rename(destination)
    remove_path(backup)


def promote_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(f"Source directory does not exist: {source}")

    ensure_directory(destination.parent)
    backup = destination.parent / f".{destination.name}.backup-{uuid4().hex}"
    remove_path(backup)

    if destination.exists():
        destination.rename(backup)

    source.rename(destination)
    remove_path(backup)
