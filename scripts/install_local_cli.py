#!/usr/bin/env python3
"""Install the local HomeCopy CLI from the current source checkout."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def install_with_pipx(root: Path) -> bool:
    pipx = shutil.which("pipx")
    if pipx is None:
        return False
    run([pipx, "install", "--force", "--editable", str(root)])
    return True


def install_with_pip(root: Path) -> None:
    run([sys.executable, "-m", "pip", "install", "--user", "--editable", str(root)])


def main() -> int:
    root = repo_root()
    try:
        if install_with_pipx(root):
            print("[install] Installed local HomeCopy CLI with pipx.")
        else:
            install_with_pip(root)
            print("[install] Installed local HomeCopy CLI with pip --user.")
    except subprocess.CalledProcessError as exc:
        print(f"[install] Failed: {exc}", file=sys.stderr)
        return exc.returncode or 1

    print("[install] You can now run: homecopy version")
    print("[install] And update the desktop app with: homecopy update")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
