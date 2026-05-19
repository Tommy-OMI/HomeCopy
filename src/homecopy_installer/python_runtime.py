"""Python runtime selection for local builds."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass


MIN_VERSION = (3, 11)
PREFERRED_MINOR_VERSIONS = ("3.12", "3.11")


@dataclass(frozen=True)
class PythonCommand:
    command: list[str]
    display: str
    version: str


def _candidate_commands() -> list[list[str]]:
    candidates: list[list[str]] = []
    override = os.environ.get("HOMECOPY_PYTHON_BIN", "").strip()
    if override:
        candidates.append([override])

    if sys.platform == "win32":
        for version in PREFERRED_MINOR_VERSIONS:
            candidates.append(["py", f"-{version}"])
        for executable in ("python3.12", "python3.11", "python"):
            candidates.append([executable])
    else:
        for executable in (
            "/opt/homebrew/bin/python3.12",
            "/opt/homebrew/bin/python3.11",
            "python3.12",
            "python3.11",
            "python3",
        ):
            candidates.append([executable])

    candidates.append([sys.executable])
    return candidates


def _resolve_command(command: list[str]) -> list[str] | None:
    executable = command[0]
    if os.path.isabs(executable) and os.path.exists(executable):
        return command
    if shutil.which(executable):
        return command
    return None


def _python_version(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            command + ["-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.SubprocessError:
        return None
    return completed.stdout.strip()


def _version_tuple(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    return int(parts[0]), int(parts[1]), int(parts[2])


def select_build_python() -> PythonCommand:
    seen: set[tuple[str, ...]] = set()
    for candidate in _candidate_commands():
        resolved = _resolve_command(candidate)
        if not resolved:
            continue

        key = tuple(resolved)
        if key in seen:
            continue
        seen.add(key)

        version = _python_version(resolved)
        if not version:
            continue

        if _version_tuple(version) >= (*MIN_VERSION, 0):
            return PythonCommand(command=resolved, display=" ".join(resolved), version=version)

    raise RuntimeError(
        "No supported Python runtime found for building HomeCopy. "
        "Install Python 3.11 or newer, or set HOMECOPY_PYTHON_BIN."
    )
